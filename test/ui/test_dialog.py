import pytest

wx = pytest.importorskip("wx")

from photo_db.ui.dialogs.scan_init import ScanInitDialog  # noqa: E402


@pytest.mark.gui
def test_scan_init():
    """Opens a real, modal desktop window (ScanInitDialog.__init__ calls
    ShowModal()/Destroy() itself) - this requires manual interaction (or a
    virtual display) and is excluded from the default test run (see the
    `gui` marker in pyproject.toml). Run explicitly with `pytest -m gui` in
    an interactive desktop session if you want to exercise the UI.
    """
    wx.App(0)
    ScanInitDialog(None, -1, "Start new Scan")
