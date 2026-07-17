"""Background thumbnail fetching for the thumbnail grid.

Runs on a Qt thread pool so scrolling/browsing never blocks the UI while a
thumbnail is being fetched (local disk read, or a network round trip to a
web backend) and decoded. Keeps a small on-disk cache of raw thumbnail
bytes (separate from the server's own ``.thumbs/`` tree) plus an in-memory
``QIcon`` cache for whatever's currently visible.

Thumbnail bytes are decoded into a ``QPixmap``/``QIcon`` only on the main
thread (in the ``ready`` slot) - constructing pixmaps off the GUI thread is
not safe on all platforms, so worker tasks only ever emit raw bytes.
"""

from os import makedirs, remove
from os.path import dirname, exists, join

from PySide6.QtCore import QObject, QRunnable, QThreadPool, Signal
from PySide6.QtGui import QIcon, QPixmap

from photo_db.client import AbstractPDBClient


class _WorkerSignals(QObject):
    ready = Signal(str, bytes)
    failed = Signal(str, str)


class _FetchTask(QRunnable):
    def __init__(self, client: AbstractPDBClient, uuid: str, cache_path: str, signals):
        super().__init__()
        self.client = client
        self.uuid = uuid
        self.cache_path = cache_path
        self.signals = signals

    def run(self):
        try:
            if exists(self.cache_path):
                with open(self.cache_path, "rb") as f:
                    data = f.read()
            else:
                data = self.client.get_thumbnail(self.uuid)
                cache_dir = dirname(self.cache_path)
                if cache_dir and not exists(cache_dir):
                    makedirs(cache_dir, exist_ok=True)
                with open(self.cache_path, "wb") as f:
                    f.write(data)
            self.signals.ready.emit(self.uuid, data)
        except Exception as e:  # noqa: BLE001 - report to UI, don't crash worker
            self.signals.failed.emit(self.uuid, str(e))


class ThumbnailLoader(QObject):
    """Fetches and caches thumbnails for the grid model."""

    thumbnail_ready = Signal(str, QIcon)

    def __init__(self, client: AbstractPDBClient, cache_dir: str, parent=None):
        super().__init__(parent)
        self.client = client
        self.cache_dir = cache_dir
        self.pool = QThreadPool.globalInstance()
        self._memory: dict[str, QIcon] = {}
        self._pending: set[str] = set()
        self._signals = _WorkerSignals()
        self._signals.ready.connect(self._on_ready)
        self._signals.failed.connect(self._on_failed)

    def get(self, uuid: str) -> QIcon | None:
        """Return the cached icon for ``uuid``, or ``None`` if not loaded
        yet (caller should also call :meth:`request`)."""
        return self._memory.get(uuid)

    def request(self, uuid: str) -> None:
        """Kick off a background fetch for ``uuid`` unless already cached
        or already in flight."""
        if uuid in self._memory or uuid in self._pending:
            return
        self._pending.add(uuid)
        cache_path = join(self.cache_dir, f"{uuid}.jpg")
        self.pool.start(_FetchTask(self.client, uuid, cache_path, self._signals))

    def _on_ready(self, uuid: str, data: bytes) -> None:
        self._pending.discard(uuid)
        pixmap = QPixmap()
        if pixmap.loadFromData(data):
            icon = QIcon(pixmap)
            self._memory[uuid] = icon
            self.thumbnail_ready.emit(uuid, icon)
        else:
            print(f"Thumbnail data for {uuid} could not be decoded")

    def _on_failed(self, uuid: str, message: str) -> None:
        self._pending.discard(uuid)
        print(f"Thumbnail fetch failed for {uuid}: {message}")

    def invalidate(self, uuid: str) -> None:
        """Drop any cached copy of ``uuid``'s thumbnail (in-memory icon and
        on-disk cache file), forcing the next :meth:`request` to re-fetch.
        Needed after a rotation change, since the uuid-keyed cache file
        would otherwise keep serving the stale orientation."""
        self._memory.pop(uuid, None)
        self._pending.discard(uuid)
        cache_path = join(self.cache_dir, f"{uuid}.jpg")
        if exists(cache_path):
            remove(cache_path)
