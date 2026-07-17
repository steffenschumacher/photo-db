import wx
from photo_db.ui.frames import ImportFrame


def test_import_frame():
    app = wx.App(0)
    ImportFrame(None, "Photo DB Importer")
    app.MainLoop()


if __name__ == "__main__":
    test_import_frame()