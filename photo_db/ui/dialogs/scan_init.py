from os.path import dirname, exists, join

import wx

from photo_db.config import Config
from photo_db.scanner.scanner import Scanner


class ScanInitDialog(wx.Dialog):
    def __init__(self, parent, id, title):
        wx.Dialog.__init__(self, parent, id, title, size=(700, 300))
        self.SetIcon(
            wx.Icon(
                join(dirname(__file__), "scan_init.ico"),
                wx.BITMAP_TYPE_ICON,
            )
        )
        self.scanner: Scanner = None
        pnl = wx.Panel(self)
        vBox = wx.BoxSizer(wx.VERTICAL)

        # -- Import path controls
        hBoxImPath = wx.BoxSizer(wx.HORIZONTAL)
        lb_ip = wx.StaticText(pnl, label="Import path")
        hBoxImPath.Add(lb_ip, flag=wx.EXPAND | wx.ALL, border=10)
        self.import_path = wx.TextCtrl(pnl, wx.ID_STATIC, "", size=(460, 22))
        hBoxImPath.Add(self.import_path, flag=wx.EXPAND | wx.ALL, border=10)
        hBoxImPath.Add(wx.Button(pnl, 3, "&Select"), flag=wx.ALL, border=10)
        vBox.Add(hBoxImPath, flag=wx.ALL | wx.ALIGN_LEFT, border=10)
        vBox.Add((-1, 5))

        # -- Store path controls
        hBoxStPath = wx.BoxSizer(wx.HORIZONTAL)
        lb_ip = wx.StaticText(pnl, label="Store path/url")
        hBoxStPath.Add(lb_ip, flag=wx.EXPAND | wx.ALL, border=10)
        self.store_uri = wx.TextCtrl(pnl, wx.ID_STATIC, "", size=(460, 22))
        if Config.STORE_URL:
            self.store_uri.SetValue(Config.STORE_URL)
        hBoxStPath.Add(self.store_uri, flag=wx.EXPAND | wx.ALL, border=10)
        hBoxStPath.Add(wx.Button(pnl, 4, "&Select"), flag=wx.ALL, border=10)
        vBox.Add(hBoxStPath, flag=wx.ALL | wx.ALIGN_LEFT, border=10)
        vBox.Add((-1, 5))

        # -- Store path controls
        hBoxCred = wx.BoxSizer(wx.HORIZONTAL)
        lb_us = wx.StaticText(pnl, label="Username for webservice")
        hBoxCred.Add(lb_us, flag=wx.EXPAND | wx.ALL, border=10)
        self.store_user = wx.TextCtrl(pnl, wx.ID_STATIC, "", size=(160, 22))
        if Config.STORE_USER:
            self.store_user.SetValue(Config.STORE_USER)
        hBoxCred.Add(self.store_user, flag=wx.EXPAND | wx.ALL, border=10)

        lb_pw = wx.StaticText(pnl, label="Password")
        hBoxCred.Add(lb_pw, flag=wx.EXPAND | wx.ALL, border=10)
        self.store_pw = wx.TextCtrl(pnl, wx.ID_STATIC, "", size=(160, 22), style=wx.TE_PASSWORD)
        if Config.STORE_PASS:
            self.store_pw.SetValue(Config.STORE_PASS)
        hBoxCred.Add(self.store_pw, flag=wx.EXPAND | wx.ALL, border=10)

        vBox.Add(hBoxCred, flag=wx.ALL | wx.ALIGN_LEFT, border=10)
        vBox.Add((-1, 5))

        # -- Buttons
        hBoxCtrl = wx.BoxSizer(wx.HORIZONTAL)
        hBoxCtrl.Add(wx.Button(pnl, 1, "&Cancel"), flag=wx.ALL, border=10)
        hBoxCtrl.Add(wx.Button(pnl, 2, "&Start scan"), flag=wx.ALL, border=10)
        vBox.Add(hBoxCtrl, flag=wx.ALL | wx.ALIGN_CENTER, border=10)
        # ------------

        self.Bind(wx.EVT_BUTTON, self.OnClose, id=1)
        self.Bind(wx.EVT_BUTTON, self.OnStartScan, id=2)
        self.Bind(wx.EVT_BUTTON, self.OnSelectIP, id=3)
        self.Bind(wx.EVT_BUTTON, self.OnSelectSP, id=4)
        pnl.SetSizer(vBox)
        # ------------

        self.Centre()

        # ------------

        self.ShowModal()
        self.Destroy()

    # -----------------------------------------------------------------------

    def OnClose(self, event):
        self.Close(True)

    def OnStartScan(self, event):
        from photo_db.client import init_client

        try:
            if uri := self.store_uri.GetValue():
                Config.STORE_URL = uri
                if uri.lower().startswith("http"):
                    if user := self.store_user.GetValue():
                        Config.STORE_USER = user
                    else:
                        raise ValueError(f"Missing username for {uri}")
                    if pw := self.store_pw.GetValue():
                        Config.STORE_PASS = pw
                    else:
                        raise ValueError(f"Missing password for {uri}")
            else:
                raise ValueError("Store path/url is missing")
            if path := self.import_path.GetValue():
                pass
            else:
                raise ValueError("Import path is missing")

            client = init_client(uri)
            self.scanner = Scanner(client)
            self.scanner.scan_dir(path)
            msg = f"Scan of {self.scanner.detected} possible images started.."
            stl = wx.ICON_INFORMATION | wx.OK
            wx.MessageBox(msg, "Scan started", stl, self)
            self.Close()
        except Exception as e:
            msg = f"Error: {e}"
            stl = wx.ICON_ERROR | wx.OK
            wx.MessageBox(msg, "Error", stl, self)
            import traceback

            traceback.print_exc()

    def OnSelectIP(self, event):
        if path := self.select_dir("Select import path"):
            self.import_path.SetValue(path)

    def OnSelectSP(self, event):
        if path := self.select_dir("Select local photo store folder"):
            db = join(path, ".photo.db")
            if not exists(db):
                msg = f"Empty photo path: {path} - setup new photo db here?"
                stl = wx.ICON_QUESTION | wx.YES_NO
                yn = wx.MessageBox(msg, "Please confirm", stl, self)
                if yn == wx.NO:
                    return  # don't use value of
            self.store_uri.SetValue(path)

    def select_dir(self, msg: str):
        # otherwise ask the user what new file to open
        stl = wx.DD_DIR_MUST_EXIST | wx.DD_SHOW_HIDDEN
        with wx.DirDialog(None, msg, "", style=stl) as dd:
            if dd.ShowModal() == wx.ID_CANCEL:
                return ""  # the user changed their mind

            # Proceed loading the file chosen by the user
            return dd.GetPath()
