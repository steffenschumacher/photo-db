"""Main application window: menu (Scan folder.., Sync library.., Settings..)
plus the thumbnail browsing grid as the central widget.
"""

from os import makedirs
from os.path import expanduser, join

from PySide6.QtCore import QThread, Signal
from PySide6.QtGui import QAction
from PySide6.QtWidgets import QMainWindow, QMessageBox, QStatusBar

from photo_db.client import init_client
from photo_db.config import Config, default_config
from photo_db.db.lean_cache import LeanCache
from photo_db.ui.scan_dialog import ScanDialog
from photo_db.ui.settings_dialog import SettingsDialog
from photo_db.ui.thumbnail_grid import ThumbnailGridWidget

_THUMB_CACHE_DIR = join(expanduser("~"), ".photodb", "thumb_cache")


class SyncWorker(QThread):
    """Runs a lean cache sync (metadata only, no image bytes) off the UI
    thread - can involve many small requests to a remote backend."""

    finished_sync = Signal(int)
    failed = Signal(str)

    def __init__(self, lean_cache: LeanCache, client, parent=None):
        super().__init__(parent)
        self.lean_cache = lean_cache
        self.client = client

    def run(self):
        try:
            self.lean_cache.sync(self.client)
            self.finished_sync.emit(self.lean_cache.count())
        except Exception as e:  # noqa: BLE001 - surface to UI
            self.failed.emit(str(e))


class MainWindow(QMainWindow):
    def __init__(self, config: Config = default_config):
        super().__init__()
        self.config = config
        self.setWindowTitle("Photo DB")
        self.resize(1100, 750)

        makedirs(_THUMB_CACHE_DIR, exist_ok=True)
        self.lean_cache = LeanCache(config=config)
        self.client = init_client(config=config)
        self.grid = ThumbnailGridWidget(self.lean_cache, self.client, _THUMB_CACHE_DIR)
        self.setCentralWidget(self.grid)

        self.setStatusBar(QStatusBar())
        self._build_menu()
        self.sync_worker: SyncWorker | None = None

    def _build_menu(self):
        menu = self.menuBar().addMenu("&Library")

        scan_action = QAction("Scan folder..", self)
        scan_action.triggered.connect(self._open_scan_dialog)
        menu.addAction(scan_action)

        sync_action = QAction("Sync library..", self)
        sync_action.triggered.connect(self._sync_library)
        menu.addAction(sync_action)

        menu.addSeparator()

        settings_action = QAction("Settings..", self)
        settings_action.triggered.connect(self._open_settings)
        menu.addAction(settings_action)

        menu.addSeparator()

        exit_action = QAction("Exit", self)
        exit_action.triggered.connect(self.close)
        menu.addAction(exit_action)

    def _open_scan_dialog(self):
        dlg = ScanDialog(self.config, self)
        dlg.exec()
        # Whatever was adopted during the scan is already upserted into the
        # lean cache by the Scanner itself - just refresh the grid to show it.
        self.grid.refresh_months()

    def _sync_library(self):
        self.statusBar().showMessage("Syncing library..")
        self.sync_worker = SyncWorker(self.lean_cache, self.client, self)
        self.sync_worker.finished_sync.connect(self._on_sync_finished)
        self.sync_worker.failed.connect(self._on_sync_failed)
        self.sync_worker.start()

    def _on_sync_finished(self, count: int):
        self.statusBar().showMessage(f"Synced - {count} photos known locally", 5000)
        self.grid.refresh_months()

    def _on_sync_failed(self, message: str):
        self.statusBar().clearMessage()
        QMessageBox.critical(self, "Sync failed", message)

    def _open_settings(self):
        dlg = SettingsDialog(self.config, self)
        dlg.exec()

    def closeEvent(self, event):
        if self.sync_worker and self.sync_worker.isRunning():
            self.sync_worker.wait(2000)
        self.lean_cache.close()
        super().closeEvent(event)
