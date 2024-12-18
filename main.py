import os
import sys
import threading
import wx
import wx.adv
from panel import Panel


class MyFrame(wx.Frame):
    def __init__(self, *args, **kw):
        super(MyFrame, self).__init__(*args, **kw)
        menubar = wx.MenuBar()
        helpMenu = wx.Menu()

        helpMenu.Append(wx.ID_ABOUT, "&About")
        menubar.Append(helpMenu, "&Help")

        self.Bind(wx.EVT_MENU, self.on_about, id=wx.ID_ABOUT)
        self.SetMenuBar(menubar)

        self.CreateStatusBar(number=2, style=wx.STB_DEFAULT_STYLE)
        self.SetStatusWidths([-1, 100])
        self.SetStatusText("Setup the test", 0)

        self.wxconfig = wx.Config("nexxPathVerification")
        self.panel = Panel(self, wxconfig=self.wxconfig)

        self.Bind(wx.EVT_CLOSE, self.OnClose)

        self.SetTitle("Nexx Path Verification")
        self.SetSize((700, 500))
        self.Centre()

    def OnClose(self, event: wx.CloseEvent):
        """User wants to close the application. Forward to app_panel."""
        # Skip event by default, so it propagates the closing the application.
        event.Skip()
        self.panel.inProgress = False

    def on_about(self, event):
        info = wx.adv.AboutDialogInfo()
        info.SetName('NEXX Path Verification Automation')
        info.SetDescription(
            "Python version %s.%s.%s (%s %s)\n" % tuple(sys.version_info) +
            "Powered by wxPython %s\n" % (wx.version()) +
            "Running on %s\n\n" % (wx.GetOsDescription()) +
            "Process ID = %s\n" % (os.getpid()))
        info.SetWebSite("www.evertz.com", "Evertz")
        info.AddDeveloper("Omkarsinh Sindha")
        wx.adv.AboutBox(info)


class MyApp(wx.App):
    def OnInit(self):
        frame = MyFrame(None)
        frame.Show(True)
        return True


if __name__ == "__main__":
    app = MyApp()
    app.MainLoop()
