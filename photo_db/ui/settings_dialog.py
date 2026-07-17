"""Settings dialog - a thin form over :class:`photo_db.config.Config`,
persisted to a dotenv file so changes survive across app restarts.
"""

from PySide6.QtWidgets import (
    QCheckBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QLineEdit,
    QMessageBox,
    QSpinBox,
)

from photo_db.config import Config


class SettingsDialog(QDialog):
    """Edits a :class:`Config` in place and persists it to ``.env`` on save."""

    def __init__(self, config: Config, parent=None):
        super().__init__(parent)
        self.config = config
        self.setWindowTitle("Settings")
        self.setMinimumWidth(420)

        self.store_url = QLineEdit(config.STORE_URL or "")
        self.store_user = QLineEdit(config.STORE_USER or "")
        self.store_pass = QLineEdit(config.STORE_PASS or "")
        self.store_pass.setEchoMode(QLineEdit.EchoMode.Password)
        self.ssl_verify = QCheckBox()
        self.ssl_verify.setChecked(bool(config.SSL_VERIFY))
        self.hash_size = QSpinBox()
        self.hash_size.setRange(8, 256)
        self.hash_size.setValue(config.HASH_SIZE)
        self.similarity = QSpinBox()
        self.similarity.setRange(1, 99)
        self.similarity.setValue(config.SIMILARITY)
        self.lean_cache_path = QLineEdit(config.LEAN_CACHE_PATH or "")

        form = QFormLayout()
        form.addRow("Store path/URL", self.store_url)
        form.addRow("Verify SSL", self.ssl_verify)
        form.addRow("Username (webservice)", self.store_user)
        form.addRow("Password (webservice)", self.store_pass)
        form.addRow("Hash size", self.hash_size)
        form.addRow("Similarity %", self.similarity)
        form.addRow("Lean cache path", self.lean_cache_path)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self._on_save)
        buttons.rejected.connect(self.reject)
        form.addRow(buttons)
        self.setLayout(form)

    def _on_save(self):
        try:
            self.config.STORE_URL = self.store_url.text().rstrip("/")
            self.config.SSL_VERIFY = self.ssl_verify.isChecked()
            self.config.STORE_USER = self.store_user.text() or None
            self.config.STORE_PASS = self.store_pass.text() or None
            self.config.HASH_SIZE = self.hash_size.value()
            self.config.SIMILARITY = self.similarity.value()
            self.config.LEAN_CACHE_PATH = self.lean_cache_path.text()
            self.config.save_env_file()
        except Exception as e:
            QMessageBox.critical(self, "Error saving settings", str(e))
            return
        self.accept()
