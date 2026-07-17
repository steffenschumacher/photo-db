"""Thumbnail browsing grid.

Combines a year/month picker with infinite-scroll: picking a month jumps
the grid there, and scrolling near the bottom lazily appends the next
month's rows (and their thumbnails) - both are meant to coexist per the
requirement to support either navigation style.
"""

from PySide6.QtCore import QSize
from PySide6.QtWidgets import (
    QComboBox,
    QHBoxLayout,
    QLabel,
    QListView,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from photo_db.client import AbstractPDBClient
from photo_db.db.lean_cache import LeanCache
from photo_db.ui.filters import month_label
from photo_db.ui.thumbnail_model import LeanPhotoListModel

_ICON_SIZE = QSize(160, 160)


class ThumbnailGridWidget(QWidget):
    """Browses the local :class:`LeanCache` as a scrollable thumbnail grid."""

    def __init__(
        self, lean_cache: LeanCache, client: AbstractPDBClient, cache_dir: str, parent=None
    ):
        super().__init__(parent)
        self.lean_cache = lean_cache
        self._months: list[tuple[int, int]] = []
        self._month_index = -1

        self.model = LeanPhotoListModel(client, cache_dir)
        self.view = QListView()
        self.view.setModel(self.model)
        self.view.setViewMode(QListView.ViewMode.IconMode)
        self.view.setIconSize(_ICON_SIZE)
        self.view.setResizeMode(QListView.ResizeMode.Adjust)
        self.view.setUniformItemSizes(True)
        self.view.setSpacing(6)
        self.view.setMovement(QListView.Movement.Static)
        self.view.verticalScrollBar().valueChanged.connect(self._on_scroll)

        self.month_picker = QComboBox()
        self.month_picker.currentIndexChanged.connect(self._on_month_picked)
        prev_btn = QPushButton("<")
        prev_btn.clicked.connect(self._prev_month)
        next_btn = QPushButton(">")
        next_btn.clicked.connect(self._next_month)
        self.count_label = QLabel("")

        top_bar = QHBoxLayout()
        top_bar.addWidget(QLabel("Period"))
        top_bar.addWidget(prev_btn)
        top_bar.addWidget(self.month_picker, 1)
        top_bar.addWidget(next_btn)
        top_bar.addWidget(self.count_label)

        layout = QVBoxLayout()
        layout.addLayout(top_bar)
        layout.addWidget(self.view, 1)
        self.setLayout(layout)

        self.refresh_months()

    def refresh_months(self) -> None:
        """Reload the set of (year, month) periods available in the lean
        cache (call after a sync) and re-populate the picker."""
        self._months = self.lean_cache.available_months()
        self.month_picker.blockSignals(True)
        self.month_picker.clear()
        for year, month in self._months:
            self.month_picker.addItem(month_label(year, month))
        self.month_picker.blockSignals(False)
        if self._months:
            self._month_index = len(self._months) - 1
            self.month_picker.setCurrentIndex(self._month_index)
            self._load_month(self._month_index, reset=True)
        else:
            self.model.clear()
            self.count_label.setText("0 photos")

    def _on_month_picked(self, index: int) -> None:
        if index < 0 or index == self._month_index:
            return
        self._load_month(index, reset=True)

    def _prev_month(self) -> None:
        if self._month_index > 0:
            self.month_picker.setCurrentIndex(self._month_index - 1)

    def _next_month(self) -> None:
        if self._month_index < len(self._months) - 1:
            self.month_picker.setCurrentIndex(self._month_index + 1)

    def _load_month(self, index: int, reset: bool) -> None:
        self._month_index = index
        year, month = self._months[index]
        rows = self.lean_cache.query_by_month(year, month)
        if reset:
            self.model.set_rows(rows)
        else:
            self.model.append_rows(rows)
        self.count_label.setText(f"{self.model.rowCount()} photos")

    def _on_scroll(self, value: int) -> None:
        bar = self.view.verticalScrollBar()
        if bar.maximum() == 0 or value < bar.maximum() - 4:
            return
        # Near the bottom of the currently loaded rows: lazily pull in the
        # next month, if any, appending rather than resetting the grid.
        if self._month_index < len(self._months) - 1:
            self._load_month(self._month_index + 1, reset=False)

    def current_period(self) -> tuple[int, int] | None:
        if 0 <= self._month_index < len(self._months):
            return self._months[self._month_index]
        return None
