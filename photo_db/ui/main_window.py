"""Main application window: toolbar + menu (Scan folder.., Sync library..,
Settings..) plus the thumbnail browsing grid as the central widget.

Actions are exposed both in the menu bar *and* a toolbar, since on macOS the
menu bar lives in the global system menu (easy to miss), whereas a toolbar
is always visible inside the window itself.
"""

from os import makedirs
from os.path import expanduser, join

from PySide6.QtCore import QThread, Signal
from PySide6.QtGui import QAction
from PySide6.QtWidgets import (
    QLabel,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QStatusBar,
    QToolBar,
    QVBoxLayout,
    QWidget,
)

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


class _NoStoreWidget(QWidget):
    """Placeholder central widget shown when no valid store is configured
    yet (e.g. first run), with a direct path to Settings rather than a
    dead end."""

    def __init__(self, message: str, open_settings_cb, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout()
        layout.addStretch(1)
        label = QLabel(message)
        label.setWordWrap(True)
        layout.addWidget(label)
        btn = QPushButton("Open Settings..")
        btn.clicked.connect(open_settings_cb)
        layout.addWidget(btn)
        layout.addStretch(1)
        self.setLayout(layout)


class MainWindow(QMainWindow):
    def __init__(self, config: Config = default_config):
        super().__init__()
        self.config = config
        self.setWindowTitle("Photo DB")
        self.resize(1100, 750)

        makedirs(_THUMB_CACHE_DIR, exist_ok=True)
        self.lean_cache: LeanCache | None = None
        self.client = None
        self.grid: ThumbnailGridWidget | None = None
        self.sync_worker: SyncWorker | None = None

        self.store_label = QLabel()
        self.setStatusBar(QStatusBar())
        self.statusBar().addPermanentWidget(self.store_label)

        self._build_actions()
        self.reload_store()

    def _build_actions(self):
        self.scan_action = QAction("Scan folder..", self)
        self.scan_action.setStatusTip("Recursively scan a folder and adopt new photos")
        self.scan_action.triggered.connect(self._open_scan_dialog)

        self.sync_action = QAction("Sync library..", self)
        self.sync_action.setStatusTip("Pull the latest metadata from the configured store")
        self.sync_action.triggered.connect(self._sync_library)

        self.settings_action = QAction("Settings..", self)
        self.settings_action.setStatusTip("Configure the local/remote store and options")
        self.settings_action.triggered.connect(self._open_settings)

        exit_action = QAction("Exit", self)
        exit_action.triggered.connect(self.close)

        menu = self.menuBar().addMenu("&Library")
        menu.addAction(self.scan_action)
        menu.addAction(self.sync_action)
        menu.addSeparator()
        menu.addAction(self.settings_action)
        menu.addSeparator()
        menu.addAction(exit_action)

        toolbar = QToolBar("Main", self)
        toolbar.setMovable(False)
        toolbar.addAction(self.scan_action)
        toolbar.addAction(self.sync_action)
        toolbar.addSeparator()
        toolbar.addAction(self.settings_action)
        self.addToolBar(toolbar)
        self.toolbar = toolbar

    def reload_store(self):
        """(Re)create the client/lean cache/grid from the current config.

        Called on startup and whenever Settings are saved, so switching
        between a local folder and a remote webservice (or changing which
        one) takes effect immediately rather than requiring a restart.
        """
        try:
            new_client = init_client(config=self.config)
            new_lean_cache = LeanCache(config=self.config)
        except Exception as e:
            self._show_no_store(f"Could not open store '{self.config.STORE_URL}': {e}")
            return

        if self.lean_cache is not None:
            self.lean_cache.close()
        self.client = new_client
        self.lean_cache = new_lean_cache
        self.grid = ThumbnailGridWidget(self.lean_cache, self.client, _THUMB_CACHE_DIR)
        self.setCentralWidget(self.grid)
        self._update_store_label()

    def _show_no_store(self, message: str):
        self.setCentralWidget(_NoStoreWidget(message, self._open_settings, self))
        self.store_label.setText("No store configured")

    def _update_store_label(self):
        kind = "remote" if self.config.STORE_URL.lower().startswith("http") else "local"
        self.store_label.setText(f"Store ({kind}): {self.config.STORE_URL}")

    def _open_scan_dialog(self):
        if self.grid is None:
            QMessageBox.warning(self, "No store", "Configure a store in Settings first.")
            return
        dlg = ScanDialog(self.config, self)
        dlg.exec()
        # Whatever was adopted during the scan is already upserted into the
        # lean cache by the Scanner itself - just refresh the grid to show it.
        self.grid.refresh_months()

    def _sync_library(self):
        if self.grid is None:
            QMessageBox.warning(self, "No store", "Configure a store in Settings first.")
            return
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
        if dlg.exec():
            self.reload_store()

    def closeEvent(self, event):
        if self.sync_worker and self.sync_worker.isRunning():
            self.sync_worker.wait(2000)
        if self.lean_cache is not None:
            self.lean_cache.close()
        super().closeEvent(event)
