from datetime import datetime
from io import BytesIO
from os import chown, makedirs
from os.path import dirname, exists, join, sep

from ..config import Config, default_config
from ..db.store import StoreDB
from ..exceptions import DuplicateException, SimilarException
from ..photo import Photo
from ..photo.orientation import render_oriented
from ..photo.parsers import hashes_similar
from ..photo.thumbnail import generate_thumbnail


class LocalStore:
    """Filesystem + SQLite backed photo library.

    Instantiated with an explicit ``Config`` (dependency injection) so tests
    and callers can point multiple, isolated stores at different locations
    in the same process instead of relying on shared global state.
    """

    def __init__(self, config: Config = default_config):
        self.config = config
        makedirs(config.STORE_URL, exist_ok=True)
        self.db = StoreDB(config)

    def check_hash(self, ph: Photo) -> bool:
        """Reject ``ph`` if it's a duplicate (exact or near) of anything
        already in the store.

        Checked against each of ``ph``'s four 90-degree rotation hash
        variants (not just its "as-is" orientation), so a photo that's the
        same content but physically re-saved/rotated by some other tool is
        still caught as a duplicate rather than silently adopted as a new,
        unrelated photo - regardless of what (if anything) its EXIF
        ``Orientation`` tag claims. When a match is only found at a
        rotation other than 0, the *existing* stored photo's ``rotation``
        is corrected to match (assuming it hasn't already been manually
        corrected), since we now know which way up it should display.
        """
        tpl = "Uploaded photo is {} existing photo"
        variants = ph.hash_variants()
        for degrees, variant_hash in variants.items():
            if uuid := self.db.lookup_hash(variant_hash):
                self._maybe_correct_rotation(uuid, degrees)
                raise DuplicateException(uuid, tpl.format("duplicate of"))

        for ext_hash, uuid in self.db.get_hashes().items():
            matched_degrees = next(
                (d for d, v in variants.items() if hashes_similar(v, ext_hash, self.config)),
                None,
            )
            if matched_degrees is None:
                continue
            existing = self.db.get_photo(uuid)
            # A match found only via a *rotated* variant (matched_degrees
            # != 0) means "the same photo, just physically reoriented" -
            # not a genuinely different/better version, so it's always a
            # duplicate, regardless of preferable_to()'s date/resolution
            # comparison (which would otherwise never fire here: a rotated
            # re-save typically has the same date and the same pixel
            # *area*, just swapped width/height). preferable_to() still
            # decides for same-orientation (degrees == 0) near-duplicates,
            # where resolution/date can legitimately differ.
            if matched_degrees != 0 or existing.preferable_to(ph):
                self._maybe_correct_rotation(uuid, matched_degrees)
                raise SimilarException(uuid, tpl.format("too similar to preferable"))
        self.db.insert_photo(ph)

    def _maybe_correct_rotation(self, uuid: str, candidate_degrees: int) -> None:
        """A rotated duplicate was just found: the stored ``uuid`` photo's
        canonical (0 degrees) hash matched the candidate's hash rotated
        ``candidate_degrees`` clockwise - so ``uuid`` needs the inverse
        rotation applied to display the way the (assumed correctly
        oriented) candidate does. Only applied if ``uuid`` hasn't already
        been manually corrected (rotation != 0), so we never clobber a
        deliberate user choice with an automatic guess."""
        if candidate_degrees == 0:
            return
        existing = self.db.get_photo(uuid)
        if existing is not None and existing.rotation == 0:
            self.rotate(uuid, (360 - candidate_degrees) % 360)

    def upload(self, photo: bytes) -> str:
        try:
            ph = Photo.from_file(BytesIO(photo), "uploaded.jpg", config=self.config)
            self.check_hash(ph)
            photo_path = self.abs_folder(ph.db_path())
        except SimilarException as sim:
            raise sim
        except DuplicateException as dup:
            # if photo exists in db, but not in fs, we also store it.
            # Cases: deleted locally or pre_check
            ph.uuid = dup.uuid
            photo_path = self.abs_folder(ph.db_path())
            if exists(photo_path):
                raise dup
        with open(photo_path, "wb") as new_pic:
            new_pic.write(photo)
        if self.config.FILE_GID or self.config.FILE_UID:
            # -1 means dont change
            uid = self.config.FILE_UID or -1
            gid = self.config.FILE_GID or -1
            chown(photo_path, uid, gid)
        self._write_thumbnail(ph, photo)
        return ph.uuid

    def get_photo(self, uuid: str) -> Photo:
        if ph := self.db.get_photo(uuid):
            return ph

    def read_photo(self, ph: Photo) -> bytes:
        with open(self.abs_folder(ph.db_path()), "rb") as pic:
            return pic.read()

    def get_display_bytes(self, ph: Photo) -> tuple[bytes, str]:
        """Return this photo's bytes re-oriented for display (EXIF
        auto-orientation plus any stored manual ``rotation``), without
        altering the stored original file. Returns ``(bytes, extension)``
        - extension is ``ph.extension`` unchanged if nothing needed
        correcting, or ``"jpg"`` if the bytes were re-encoded."""
        data, fmt = render_oriented(self.read_photo(ph), ph.rotation)
        return data, (fmt or ph.extension)

    def rotate(self, uuid: str, delta: int) -> Photo | None:
        """Apply an additional clockwise ``delta`` degrees rotation on top
        of whatever correction is already stored (wrapping to
        0/90/180/270), persist it, and regenerate the cached thumbnail to
        match. Returns the updated Photo, or ``None`` if ``uuid`` is
        unknown."""
        ph = self.get_photo(uuid)
        if ph is None:
            return None
        ph.rotation = (ph.rotation + delta) % 360
        self.db.update_rotation(uuid, ph.rotation)
        self._write_thumbnail(ph, self.read_photo(ph))
        return ph

    def get_hashes(self) -> dict[str, str]:
        return self.db.get_hashes()

    def since(
        self,
        scanned_after: datetime | None = None,
        limit: int = 5000,
        after_uuid: str | None = None,
    ) -> list[Photo]:
        return self.db.since(scanned_after, limit, after_uuid)

    def thumb_path(self, ph: Photo) -> str:
        """Thumbnails live in a folder tree parallel to the originals, keyed
        by uuid (rather than the original's date-derived filename) so they
        keep working even if the naming scheme or capture date is amended
        later."""
        return join(
            self.config.STORE_URL,
            ".thumbs",
            f"{ph.date.year:04d}",
            f"{ph.date.month:02d}",
            f"{ph.uuid}.jpg",
        )

    def _write_thumbnail(self, ph: Photo, photo: bytes) -> None:
        path = self.thumb_path(ph)
        thumb_dir = dirname(path)
        # exist_ok=True (rather than an exists()-then-makedirs() check)
        # avoids a TOCTOU race: the scanner runs many process_image() calls
        # concurrently on a thread pool, so two threads uploading photos
        # from the same year/month can both observe the directory as
        # missing and race to create it - the loser would otherwise hit a
        # FileExistsError even though the directory now exists exactly as
        # intended.
        makedirs(thumb_dir, exist_ok=True)
        with open(path, "wb") as thumb_file:
            thumb_file.write(generate_thumbnail(photo, rotation=ph.rotation))

    def get_thumbnail(self, ph: Photo) -> bytes:
        """Return the cached thumbnail for ``ph``, regenerating it on the
        fly (and caching the result) if it's missing - e.g. for photos
        stored before thumbnail generation existed."""
        path = self.thumb_path(ph)
        if not exists(path):
            self._write_thumbnail(ph, self.read_photo(ph))
        with open(path, "rb") as thumb_file:
            return thumb_file.read()

    def abs_folder(self, db_path: str) -> str:
        db_path_parts = db_path.split(sep)
        filename = db_path_parts.pop()
        db_dir = join(self.config.STORE_URL, *db_path_parts)
        # Same TOCTOU race as _write_thumbnail() above - use exist_ok=True
        # rather than an exists() check, since multiple scanner threads can
        # be uploading into the same year/month folder concurrently.
        makedirs(db_dir, exist_ok=True)
        return join(db_dir, filename)


__all__ = ["LocalStore"]
