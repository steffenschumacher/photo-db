import wx
from photo_db.ui.dialogs.scan_init import ScanInitDialog


def test_scan_init():
    app = wx.App(0)
    ScanInitDialog(None, -1, "Start new Scan")
    app.MainLoop()
