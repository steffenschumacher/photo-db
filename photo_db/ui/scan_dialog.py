"""Scan dialog - pick a folder to recursively scan, run the existing
:class:`photo_db.scanner.scanner.Scanner` in a background thread, and show
live progress of what's detected/adopted/rejected.
"""

from PySide6.QtCore import QThread, Signal
from PySide6.QtWidgets import (
    QDialog,
    QFileDialog,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
)

from photo_db.client import init_client
from photo_db.config import Config
from photo_db.photo import LocalPhoto
from photo_db.scanner.scanner import Scanner
from photo_db.ui.filters import mpixel, taken_date, trim_path

_COLUMNS = [
    ("Path", "local_path", trim_path),
    ("Resolution", "pixels", mpixel),
    ("Camera", "camera", None),
    ("Taken", "date", taken_date),
    ("GPS", "gps", None),
    ("Status", "status", None),
    ("Details", "reject_reason", None),
]


class ScanWorker(QThread):
    """Runs a folder scan + upload/adoption loop off the UI thread."""

    photo_processed = Signal(object)
    finished_scan = Signal(int, int)
    failed = Signal(str)

    def __init__(self, scanner: Scanner, import_path: str, parent=None):
        super().__init__(parent)
        self.scanner = scanner
        self.import_path = import_path
        self._stop = False

    def stop(self):
        self._stop = True

    def run(self):
        try:
            self.scanner.scan_dir(self.import_path)
            finished = False
            while not finished and not self._stop:
                finished, photos = self.scanner.uploading_complete(blocking=False, verbose=False)
                for ph in photos:
                    self.photo_processed.emit(ph)
                if not finished:
                    self.msleep(300)
            self.finished_scan.emit(self.scanner.processed, self.scanner.detected)
        except Exception as e:  # noqa: BLE001 - surface any failure to the UI
            self.failed.emit(str(e))


class ScanDialog(QDialog):
    """Lets the user pick an import folder and watch the scan run against
    the configured store (local path or remote web backend)."""

    def __init__(self, config: Config, parent=None):
        super().__init__(parent)
        self.config = config
        self.worker: ScanWorker | None = None
        self.setWindowTitle("Scan for photos")
        self.resize(900, 500)

        self.import_path = QLineEdit()
        self.pick_btn = QPushButton("Select..")
        self.pick_btn.clicked.connect(self._pick_folder)
        path_row = QHBoxLayout()
        path_row.addWidget(QLabel("Import path"))
        path_row.addWidget(self.import_path, 1)
        path_row.addWidget(self.pick_btn)

        self.status_label = QLabel(f"Store: {config.STORE_URL}")

        self.progress = QProgressBar()
        self.progress.setRange(0, 1)
        self.progress.setValue(0)
        self.progress.setTextVisible(False)
        self.progress.setVisible(False)

        self.table = QTableWidget(0, len(_COLUMNS))
        self.table.setHorizontalHeaderLabels([c[0] for c in _COLUMNS])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.table.verticalHeader().setVisible(False)

        self.start_btn = QPushButton("Start scan")
        self.start_btn.clicked.connect(self._start_scan)
        close_btn = QPushButton("Close")
        close_btn.clicked.connect(self.reject)
        btn_row = QHBoxLayout()
        btn_row.addStretch(1)
        btn_row.addWidget(self.start_btn)
        btn_row.addWidget(close_btn)

        layout = QVBoxLayout()
        layout.addLayout(path_row)
        layout.addWidget(self.status_label)
        layout.addWidget(self.progress)
        layout.addWidget(self.table, 1)
        layout.addLayout(btn_row)
        self.setLayout(layout)

    def _pick_folder(self):
        if path := QFileDialog.getExistingDirectory(self, "Select import path"):
            self.import_path.setText(path)

    def _start_scan(self):
        path = self.import_path.text()
        if not path:
            QMessageBox.warning(self, "Missing path", "Please select an import path first.")
            return
        if not self.config.STORE_URL:
            QMessageBox.warning(self, "Missing store", "Please configure a store in Settings.")
            return
        try:
            client = init_client(config=self.config)
            scanner = Scanner(client, config=self.config)
        except Exception as e:
            QMessageBox.critical(self, "Error starting scan", str(e))
            return
        self.start_btn.setEnabled(False)
        self.pick_btn.setEnabled(False)
        self.import_path.setEnabled(False)
        self.progress.setRange(0, 0)  # indeterminate "busy" spinner while scanning
        self.progress.setVisible(True)
        self.table.setRowCount(0)
        self.worker = ScanWorker(scanner, path, self)
        self.worker.photo_processed.connect(self._add_row)
        self.worker.finished_scan.connect(self._on_finished)
        self.worker.failed.connect(self._on_failed)
        self.worker.start()

    def _add_row(self, ph: LocalPhoto):
        row = self.table.rowCount()
        self.table.insertRow(row)
        for col, (_title, attr, fmt) in enumerate(_COLUMNS):
            val = getattr(ph, attr, None)
            if val is not None and fmt:
                val = fmt(val)
            self.table.setItem(row, col, QTableWidgetItem(str(val) if val is not None else ""))

    def _on_finished(self, processed: int, detected: int):
        self.status_label.setText(
            f"Store: {self.config.STORE_URL} - done, processed {processed}/{detected} photos"
        )
        self.progress.setRange(0, 1)
        self.progress.setValue(1)
        # Scan is complete: leave the start/pick/path controls disabled so
        # the user can't re-trigger a scan from this dialog instance (per
        # requirement, only Close should remain available at completion) -
        # they can reopen the dialog for a new scan instead.

    def _on_failed(self, message: str):
        QMessageBox.critical(self, "Scan failed", message)
        self.progress.setVisible(False)
        # Unlike a normal completion, a failure is recoverable - re-enable
        # the controls so the user can fix the issue (e.g. pick a
        # different path) and retry without reopening the dialog.
        self.start_btn.setEnabled(True)
        self.pick_btn.setEnabled(True)
        self.import_path.setEnabled(True)

    def closeEvent(self, event):
        if self.worker and self.worker.isRunning():
            self.worker.stop()
            self.worker.wait(2000)
        super().closeEvent(event)
