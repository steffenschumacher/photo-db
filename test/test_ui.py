"""Smoke tests for the PySide6 desktop UI. Uses Qt's "offscreen" platform
plugin (see the ``qapp`` fixture in conftest.py) so no real display is
needed; excluded from the default test run via the ``gui`` marker (these
still spin up real Qt widgets and are slower / more environment-sensitive
than the rest of the suite).
"""

import tempfile

import pytest

from photo_db.config import Config

from .conftest import STATIC_DIR

pytestmark = pytest.mark.gui


def _sample_bytes(filename: str = "08-190641-4631.jpeg") -> bytes:
    with open(STATIC_DIR / filename, "rb") as f:
        return f.read()


def _ui_config(store_url: str) -> Config:
    return Config(store_url=store_url, lean_cache_path=tempfile.mktemp(suffix=".db"))


def test_main_window_builds_and_shows(qapp, local_store_client, clean_store, test_config):
    from photo_db.ui.main_window import MainWindow

    cfg = _ui_config(test_config.STORE_URL)
    window = MainWindow(cfg)
    try:
        assert window.windowTitle() == "Photo DB"
        assert window.grid.model.rowCount() == 0
        assert window.menuBar().actions(), "expected a Library menu"
    finally:
        window.close()
        window.lean_cache.close()


def test_settings_dialog_saves_config(qapp, tmp_path):
    from photo_db.ui.settings_dialog import SettingsDialog

    cfg = Config(store_url="/tmp/somewhere", lean_cache_path=str(tmp_path / "lean.db"))
    env_path = tmp_path / ".env"
    dlg = SettingsDialog(cfg)
    dlg.store_url.setText("/tmp/elsewhere")
    dlg.hash_size.setValue(42)

    import os

    cwd = os.getcwd()
    os.chdir(tmp_path)
    try:
        dlg._on_save()
    finally:
        os.chdir(cwd)

    assert cfg.STORE_URL == "/tmp/elsewhere"
    assert cfg.HASH_SIZE == 42
    assert env_path.exists()


def test_thumbnail_grid_lists_synced_photos(qapp, local_store_client, clean_store, test_config):
    from photo_db.db.lean_cache import LeanCache
    from photo_db.ui.thumbnail_grid import ThumbnailGridWidget

    local_store_client.upload(_sample_bytes())

    lean_cache = LeanCache(_ui_config(test_config.STORE_URL))
    lean_cache.sync(local_store_client)

    cache_dir = tempfile.mkdtemp()
    grid = ThumbnailGridWidget(lean_cache, local_store_client, cache_dir)
    try:
        assert grid.model.rowCount() == 1
        assert grid.current_period() is not None
    finally:
        lean_cache.close()


def test_scan_dialog_builds(qapp, test_config):
    from photo_db.ui.scan_dialog import ScanDialog

    dlg = ScanDialog(test_config)
    assert dlg.windowTitle() == "Scan for photos"
    assert dlg.table.columnCount() == 7
