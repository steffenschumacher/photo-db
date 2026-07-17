from collections import deque
from concurrent.futures import Future, ThreadPoolExecutor
from datetime import datetime
from os import listdir
from os.path import isdir, isfile, join, sep
from re import IGNORECASE, compile
from threading import Lock
from time import time
from traceback import print_exc
from uuid import uuid4

from photo_db.client import AbstractPDBClient, init_client
from photo_db.config import Config, default_config
from photo_db.constants import IGNORABLE_EXTS
from photo_db.db.lean_cache import LeanCache
from photo_db.db.scanner import ScanDB
from photo_db.exceptions import DuplicateException, SimilarException
from photo_db.photo import LocalPhoto, Photo

_ignore_pat = compile(r".*(\.AppleDouble).*", IGNORECASE)
_consider_pat = compile(r"\S+\.(jpg|jpeg|heic|heif|arw)", IGNORECASE)
_raw_pat = compile(r"\S+\.arw", IGNORECASE)


class Scanner:
    client: AbstractPDBClient = None
    pool: ThreadPoolExecutor

    def __init__(
        self,
        client: AbstractPDBClient = None,
        config: Config = default_config,
        lean_cache: LeanCache = None,
    ):
        self.config = config
        self.client: AbstractPDBClient = client or init_client(config=config)
        self.pool = ThreadPoolExecutor(4)
        self.futures = deque()
        self.processed = 0
        self.detected = 0
        self.start = None
        # The lean cache is synced incrementally (only what changed since
        # our last sync) rather than fully re-fetching hash->uuid on every
        # scan, and is persisted locally so subsequent scans start warm.
        self.lean_cache = lean_cache or LeanCache(config=config)
        self._chs = self.pool.submit(self._load_central_hashes)
        self._chs_lock = Lock()
        self.scan_hashes: dict[str, LocalPhoto] = {}
        self.sh_lock = Lock()
        self.ch_lock = Lock()
        self.db = ScanDB(config=config)

    def _load_central_hashes(self) -> dict[str, str]:
        self.lean_cache.sync(self.client)
        return self.lean_cache.hashes()

    @property
    def central_hashes(self) -> dict[str, str]:
        if isinstance(self._chs, Future):
            with self._chs_lock:
                if isinstance(self._chs, Future):
                    self._chs = self._chs.result()
        if isinstance(self._chs, dict):
            return self._chs
        else:
            raise ValueError(f"Loading of central hashes failed: {self._chs}")

    def scan_dir(self, path: str):
        if self.start is None:
            self.start = time()
        for file in listdir(path):
            full = join(path, file)
            if isdir(full):
                self.scan_dir(full)
            elif self.is_possible_image(full):
                self.detected += 1
                fut = self.pool.submit(self.process_image, path, file)
                self.futures.appendleft(fut)

    def processed_photos(self) -> list[LocalPhoto]:
        return self.db.search()

    def uploading_complete(
        self, blocking=False, verbose=True, hz=100
    ) -> tuple[bool, list[LocalPhoto]]:
        tick = None
        photos = []
        while True:
            if not self.futures:
                return True, photos
            fut: Future = self.futures.pop()
            try:
                ph: LocalPhoto = fut.result(timeout=None if blocking else 0.1)
                print(f"Finished processing {ph}")
                self.db.upsert_photo(ph)
                photos.append(ph)
                self.processed += 1
                if not tick:
                    tick = hz
                    if verbose:
                        msg = (
                            f"Processed {self.processed}/{self.detected} photos - "
                            f"remaining: {len(self.futures)}"
                        )
                        print(msg)
                tick -= 1
            except TimeoutError:
                self.futures.insert(0, fut)
                return False, photos
            except Exception as e:
                print(f"Received unhandled exception: {e}")
                print_exc()
                return False, photos

    def process_image(self, path: str, file: str, pre_check_hash=True):
        full = join(path, file)
        try:
            if _raw_pat.search(full.lower()):
                from photo_db.photo.arw_converter import convert_raw

                ph = convert_raw(full, self.config)
            else:
                ph = LocalPhoto.from_file(full, config=self.config)
            if not ph.camera or not ph.latitude or not ph.longitude or not ph.date:
                ph.latitude = ph.latitude or 0
                ph.longitude = ph.longitude or 0
                ph.altitude = ph.altitude or 0
                ph.camera = ph.camera or "N/A"
                ph.date = ph.date or datetime.fromtimestamp(0.0)
                reasons = []
                if not ph.camera:
                    reasons.append("camera")
                if not ph.latitude:
                    reasons.append("GPS")
                if not ph.date:
                    reasons.append("date")
                ph.reject_reason = f"Incomplete EXIF data ({'+'.join(reasons)})"
                ph.status = "exif"
                return ph
        except (ValueError, ImportError, ModuleNotFoundError) as ve:
            print(f"{file} is not a valid photo - skipping: {ve}")
            reason = ve.args[0].split(": ")[-1] if ve.args else str(ve)
            if isinstance(ve, ImportError | ModuleNotFoundError):
                reason = f"RAW conversion unavailable ({reason}) - install the 'raw' extra"
            dummy_args = {
                "path": full,
                "camera": "Unknown",
                "date": datetime.now(),
                "width": 0,
                "height": 0,
                "hash": str(uuid4()),
                "extension": full.split(sep)[-1],
                "reject_reason": reason,
                "status": "ignored",
            }
            return LocalPhoto(**dummy_args)
        if self.check_with_processed_photos(ph):
            # attempts upload if likely import worthy
            self.check_with_central_photos(ph)
        return ph

    def check_with_processed_photos(self, ph: LocalPhoto) -> bool:
        with self.sh_lock:
            if processed := self.scan_hashes.get(ph.hash, None):
                ph.duplicate_src = "local"
                ph.duplicate_uuid = processed.uuid
                ph.reject_reason = "identical to already processed photo"
                ph.status = "duplicate"
                return False
            for scan_hash, other in self.scan_hashes.items():
                if ph.similar_to_hash(scan_hash):
                    if other.preferable_to(ph):
                        ph.duplicate_src = "local"
                        ph.duplicate_uuid = other.uuid
                        ph.reject_reason = "too similar to processed photo"
                        ph.status = "similar"
                        return False
                    else:
                        ph.duplicate_src = "local"
                        ph.duplicate_uuid = other.uuid
                        ph.reject_reason = "similar to processed photo, but preferable"
            # we passed all the tests - we will try to upload this now...
            self.scan_hashes[ph.hash] = ph
            return True

    def check_with_central_photos(self, ph: LocalPhoto) -> bool:
        with self.ch_lock:
            if existing := self.central_hashes.get(ph.hash, None):
                ph.duplicate_src = "central"
                ph.duplicate_uuid = existing
                ph.reject_reason = "identical to imported photo"
                ph.status = "duplicate"
                return False
            for central_hash, uuid in self.central_hashes.items():
                if ph.similar_to_hash(central_hash):
                    other: Photo | None = self.client.get_meta(uuid)
                    if other is None:
                        # Stale central_hashes entry (e.g. the referenced
                        # photo no longer exists in the store) - nothing
                        # sound to compare against, so just skip it rather
                        # than crash.
                        continue
                    if other.preferable_to(ph):
                        ph.duplicate_src = "central"
                        ph.duplicate_uuid = uuid
                        ph.reject_reason = "too similar to imported photo"
                        ph.status = "similar"
                        return False
                    else:
                        ph.duplicate_src = "central"
                        ph.duplicate_uuid = uuid
                        ph.reject_reason = "similar to imported photo, but preferable"

        # we passed all the tests - we will try to upload this now...
        try:
            with open(ph.local_path, "rb") as pic:
                ph.uuid = self.client.upload(pic.read())
                ph.status = "uploaded"
                with self.ch_lock:
                    self.central_hashes[ph.hash] = ph.uuid
                    # Keep the lean cache warm with this scan session's own
                    # uploads so later files in the same scan (and future
                    # scans, before their next full sync) see it as a known
                    # duplicate without waiting on a server round trip. The
                    # `scanned` value here is the client's clock rather
                    # than the server's; it gets corrected transparently
                    # the next time LeanCache.sync() pulls the authoritative
                    # row (upserts are keyed by uuid).
                    self.lean_cache.upsert_many([ph.lean_dict()])
            return True
        except (DuplicateException, SimilarException) as de:
            ph.duplicate_src = "central"
            ph.duplicate_uuid = de.uuid
            ph.reject_reason = de.description
            ph.status = "rejected"
            return False

    def is_possible_image(self, abs_file: str) -> bool:
        if not isfile(abs_file):
            return False
        lower = abs_file.lower()
        if _ignore_pat.search(lower):
            return False
        for ext in IGNORABLE_EXTS:
            if lower.endswith(f".{ext}"):
                return False

        return bool(_consider_pat.search(lower))
