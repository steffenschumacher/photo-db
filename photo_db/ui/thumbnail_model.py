"""Qt model wrapping lean cache rows for the thumbnail grid.

Deliberately holds only whatever page of rows is currently loaded (one or
more months' worth) rather than the whole library, so browsing stays cheap
even for large collections - the grid widget drives what's loaded based on
the visible year/month and scroll position.
"""

from datetime import UTC, datetime

from PySide6.QtCore import QAbstractListModel, QModelIndex, Qt
from PySide6.QtGui import QIcon

from photo_db.client import AbstractPDBClient
from photo_db.ui.thumbnail_loader import ThumbnailLoader

UuidRole = Qt.ItemDataRole.UserRole + 1
DateRole = Qt.ItemDataRole.UserRole + 2


class LeanPhotoListModel(QAbstractListModel):
    """List model over lean-dict rows (see ``Photo.lean_dict``), with
    thumbnails fetched lazily via a :class:`ThumbnailLoader` as each row is
    actually asked to render (i.e. as it scrolls into view)."""

    def __init__(self, client: AbstractPDBClient, cache_dir: str, parent=None):
        super().__init__(parent)
        self.loader = ThumbnailLoader(client, cache_dir)
        self.loader.thumbnail_ready.connect(self._on_thumbnail_ready)
        self._rows: list[dict] = []
        self._blank = QIcon()

    def set_rows(self, rows: list[dict]) -> None:
        self.beginResetModel()
        self._rows = rows
        self.endResetModel()

    def append_rows(self, rows: list[dict]) -> None:
        if not rows:
            return
        start = len(self._rows)
        self.beginInsertRows(QModelIndex(), start, start + len(rows) - 1)
        self._rows.extend(rows)
        self.endInsertRows()

    def clear(self) -> None:
        self.set_rows([])

    def rowCount(self, parent: QModelIndex = QModelIndex()) -> int:  # noqa: B008
        return len(self._rows)

    def data(self, index: QModelIndex, role: int = Qt.ItemDataRole.DisplayRole):
        if not index.isValid() or not (0 <= index.row() < len(self._rows)):
            return None
        row = self._rows[index.row()]
        if role == Qt.ItemDataRole.DecorationRole:
            icon = self.loader.get(row["uuid"])
            if icon is None:
                self.loader.request(row["uuid"])
                return self._blank
            return icon
        if role == Qt.ItemDataRole.ToolTipRole:
            dt = datetime.fromtimestamp(row["date"], tz=UTC)
            camera = row.get("camera") or "unknown camera"
            return f"{dt:%Y-%m-%d %H:%M:%S} - {camera}"
        if role == UuidRole:
            return row["uuid"]
        if role == DateRole:
            return row["date"]
        return None

    def _on_thumbnail_ready(self, uuid: str, _icon: QIcon) -> None:
        for i, row in enumerate(self._rows):
            if row["uuid"] == uuid:
                idx = self.index(i)
                self.dataChanged.emit(idx, idx, [Qt.ItemDataRole.DecorationRole])
                break

    def invalidate_thumbnail(self, uuid: str) -> None:
        """Drop the cached thumbnail for ``uuid`` (e.g. after a rotation
        change) and trigger a fresh fetch/render for whatever row(s)
        currently show it."""
        self.loader.invalidate(uuid)
        for i, row in enumerate(self._rows):
            if row["uuid"] == uuid:
                idx = self.index(i)
                self.dataChanged.emit(idx, idx, [Qt.ItemDataRole.DecorationRole])
                break
