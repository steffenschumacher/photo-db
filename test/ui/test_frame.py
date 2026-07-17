import pytest

wx = pytest.importorskip("wx")

from photo_db.ui.frames import ImportFrame  # noqa: E402


@pytest.mark.gui
def test_import_frame():
    """Opens a real desktop window and blocks on app.MainLoop() - excluded
    from the default test run (see the `gui` marker in pyproject.toml). Run
    explicitly with `pytest -m gui` in an interactive desktop session if you
    want to exercise the UI.
    """
    app = wx.App(0)
    ImportFrame(None, "Photo DB Importer")
    app.MainLoop()


if __name__ == "__main__":
    test_import_frame()
