"""Full-image preview popup.

Double-clicking a thumbnail in the grid opens this dialog, showing the
original image auto-rotated per EXIF orientation plus any previously
saved manual correction (the store's ``/image/<uuid>`` - or, for a local
store, ``LocalStore.get_display_bytes`` - already bakes both of those in,
so this dialog just displays whatever bytes it gets back).

The rotate buttons let the user nudge the image another 90 degrees and
persist that back to whichever store is configured (local or remote) via
``AbstractPDBClient.rotate()`` - both client implementations go through
the same call here, so this dialog doesn't need to know which kind of
store it's talking to.
"""

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QSizePolicy,
    QVBoxLayout,
)

from photo_db.client import AbstractPDBClient


class ImageViewerDialog(QDialog):
    """Shows the full (auto-oriented) image for ``uuid`` and lets the user
    apply an additional 90-degree rotation, persisted back to the store."""

    #: emitted with the uuid after a rotation was successfully saved, so
    #: the caller can invalidate/refresh the corresponding thumbnail.
    rotated = Signal(str)

    def __init__(self, client: AbstractPDBClient, uuid: str, parent=None):
        super().__init__(parent)
        self.client = client
        self.uuid = uuid
        self._pixmap: QPixmap | None = None
        self.setWindowTitle("Photo preview")
        self.resize(900, 700)

        self.image_label = QLabel("Loading..")
        self.image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.image_label.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

        rotate_left_btn = QPushButton("Rotate left")
        rotate_left_btn.clicked.connect(lambda: self._rotate(-90))
        rotate_right_btn = QPushButton("Rotate right")
        rotate_right_btn.clicked.connect(lambda: self._rotate(90))
        close_btn = QPushButton("Close")
        close_btn.clicked.connect(self.accept)

        btn_row = QHBoxLayout()
        btn_row.addWidget(rotate_left_btn)
        btn_row.addWidget(rotate_right_btn)
        btn_row.addStretch(1)
        btn_row.addWidget(close_btn)

        layout = QVBoxLayout()
        layout.addWidget(self.image_label, 1)
        layout.addLayout(btn_row)
        self.setLayout(layout)

        self._load_image()

    def _load_image(self) -> None:
        try:
            data = self.client.get(self.uuid)
        except Exception as e:  # noqa: BLE001 - surface to the user, don't crash
            QMessageBox.critical(self, "Error loading image", str(e))
            self.image_label.setText("Failed to load image")
            return
        pixmap = QPixmap()
        if pixmap.loadFromData(data):
            self._pixmap = pixmap
            self._render_pixmap()
        else:
            self.image_label.setText("Image data could not be decoded")

    def _render_pixmap(self) -> None:
        if not self._pixmap:
            return
        scaled = self._pixmap.scaled(
            self.image_label.size(),
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )
        self.image_label.setPixmap(scaled)

    def resizeEvent(self, event):  # noqa: N802 - Qt override signature
        super().resizeEvent(event)
        self._render_pixmap()

    def _rotate(self, delta: int) -> None:
        try:
            self.client.rotate(self.uuid, delta)
        except Exception as e:  # noqa: BLE001 - surface to the user, don't crash
            QMessageBox.critical(self, "Error rotating image", str(e))
            return
        # The store is authoritative on the resulting orientation - reload
        # rather than rotate the in-memory pixmap ourselves, to stay in
        # sync with what was actually persisted.
        self._load_image()
        self.rotated.emit(self.uuid)


__all__ = ["ImageViewerDialog"]
