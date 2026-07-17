from time import sleep
from threading import Thread
import wx
from wx.lib.scrolledpanel import ScrolledPanel

from photo_db.photo.photo import LocalPhoto
from photo_db.scanner.scanner import Scanner
from photo_db.ui.filters import *

def_stl = wx.ALIGN_LEFT


class ImportFrame(wx.Frame):
    def __init__(self, parent, title):
        screenSize = wx.DisplaySize()
        self.screenWidth = screenSize[0]
        self.screenHeight = screenSize[1]
        super().__init__(parent, title=title, size=screenSize, style=wx.DEFAULT_FRAME_STYLE ^ wx.RESIZE_BORDER)
        self.cols = {"Path": ("local_path", 520, trim_path),
                     "Resolution": ("pixels", 65, mpixel),
                     "Camera": ("camera", 160, None),
                     "From": ("date", 160, taken_date),
                     "GPS": ("gps", 100, None),
                     "Status": ("status", 90, None),
                     "Details": ("reject_reason", 450, None),
                     }
        self.tPanel: wx.Panel = None
        self.InitUI()
        self.Centre()
        self.Show()

    def InitHeader(self, parent) -> wx.Panel:
        panel1 = wx.Panel(parent, size=(self.screenWidth, 28), style=wx.SIMPLE_BORDER)
        panel1.SetBackgroundColour('#FDDF99')

        sizer = wx.BoxSizer(wx.HORIZONTAL)
        font: wx.Font = wx.SystemSettings.GetFont(wx.SYS_SYSTEM_FONT)
        font.SetPointSize(12)
        font.SetStyle(wx.BOLD)
        for hdr, col in self.cols.items():
            txt = wx.StaticText(panel1, label=hdr, size=(col[1], 28))
            sizer.Add(txt, 0, wx.EXPAND | wx.LEFT, 5)
        panel1.SetSizer(sizer)
        return panel1

    def InitTable(self, parent) -> ScrolledPanel:
        panel2 = ScrolledPanel(
            parent,
            size=(self.screenWidth - 6, self.screenHeight - 50),
            # pos=(0, 40),
            style=wx.SIMPLE_BORDER)
        panel2.SetupScrolling()
        panel2.SetBackgroundColour('#FFFFFF')
        gs = wx.BoxSizer(wx.VERTICAL)
        panel2.SetSizer(gs)
        return panel2

    def InitImportMenu(self) -> wx.Menu:
        menubar = wx.MenuBar()
        importMenu = wx.Menu()
        newScanItem = importMenu.Append(wx.ID_ANY, 'Scan..', 'Scan for photos')
        loadScanItem = importMenu.Append(wx.ID_ANY, 'Load..', 'Load existing scan')

        menubar.Append(importMenu, '&Import')

        self.Bind(wx.EVT_MENU, self.OnNewImport, newScanItem)
        self.Bind(wx.EVT_MENU, self.OnLoadImport, loadScanItem)
        return menubar

    def InitUI(self):

        self.SetMenuBar(self.InitImportMenu())

        vbox = wx.BoxSizer(wx.VERTICAL)
        # Add header
        hPanel = self.InitHeader(self)
        vbox.Add(hPanel, proportion=0, flag=wx.ALIGN_LEFT | wx.EXPAND)
        # vbox.Add(wx.StaticLine(self, -1, size=(self.screenWidth, -1)), 0, wx.ALL, 5)

        self.tPanel = self.InitTable(self)
        vbox.Add(self.tPanel, proportion=0, flag=wx.ALIGN_LEFT | wx.EXPAND)
        self.SetSizer(vbox)

    def insertPhotoRow(self, ph: LocalPhoto):
        cells = []
        bs = wx.BoxSizer(wx.HORIZONTAL)
        for title, attr in self.cols.items():
            if attr[0]:
                if val := getattr(ph, attr[0], "N/A"):
                    if attr[2]:
                        val = attr[2](val)
            else:
                val = "??"
            txt = wx.StaticText(self.tPanel, label=val, size=(attr[1], 20))
            bs.Add(txt, 0, wx.LEFT | wx.EXPAND, 5)
        self.tPanel.GetSizer().Add(bs, 0, wx.TOP, 2)

    def OnNewImport(self, event):
        from photo_db.ui.dialogs import ScanInitDialog
        im_dia = ScanInitDialog(self, wx.ID_ANY, "Start new photo import")
        if sc := im_dia.scanner:
            Thread(target=self.monitor_scan_process, args=[sc]).start()

    def monitor_scan_process(self, sc: Scanner):
        if not sc:
            return
        finished = False
        while not finished:
            finished, photos = sc.uploading_complete(blocking=False, verbose=True)
            for ph in photos:
                self.insertPhotoRow(ph)
            if photos:
                self.GetSizer().Layout()
                self.Fit()
                print("Added rows")
            sleep(1)

    def OnLoadImport(self, event):
        pass
