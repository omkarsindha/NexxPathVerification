import time
import paramiko
import threading
import wx
from config import Config


class Panel(wx.Panel):
    def __init__(self, parent, wxconfig):
        wx.Panel.__init__(self, parent)
        self.wxconfig = wxconfig
        self.config = None
        self.parent = parent

        self.timer = wx.Timer(self)
        self.Bind(wx.EVT_TIMER, self.OnTimer, self.timer)

        self.inProgress = False
        self.animation_counter: int = 0
        top_box = wx.StaticBox(self, label='Test Configuration')
        top_box.SetFont(wx.Font(wx.FontInfo(12).Bold()))
        top_box_sizer = wx.StaticBoxSizer(top_box)

        ip_box = wx.StaticBox(self, label="Nexx IP Address")
        ip_box_sizer = wx.StaticBoxSizer(ip_box)
        self.ip = wx.TextCtrl(self, value=self.wxconfig.Read('/nexxIP', defaultVal=""))
        ip_box_sizer.Add(self.ip, 0, wx.EXPAND | wx.ALL, 5)

        port_box = wx.StaticBox(self, label="Port")
        port_box_sizer = wx.StaticBoxSizer(port_box)
        self.port = wx.TextCtrl(self, size=(60, -1), value=self.wxconfig.Read('/nexxPort', defaultVal=""))
        port_box_sizer.Add(self.port, 0, wx.EXPAND | wx.ALL, 5)

        delay_box = wx.StaticBox(self, label="Delay")
        delay_box_sizer = wx.StaticBoxSizer(delay_box)
        self.delay = wx.TextCtrl(self, size=(30, -1), value=self.wxconfig.Read('/nexxDelay', defaultVal=""))
        delay_box_sizer.Add(self.delay, 0, wx.EXPAND | wx.ALL, 5)
        delay_box_sizer.Add(wx.StaticText(self, label="Seconds"), 0, wx.EXPAND | wx.ALL, 5)

        self.load = wx.Button(self, label="Load IOs")
        self.load.Bind(wx.EVT_BUTTON, self.on_load)

        self.start = wx.Button(self, label="Start")
        self.start.Disable()
        self.start.Bind(wx.EVT_BUTTON, self.on_start)

        self.stop = wx.Button(self, label="Stop")
        self.stop.Disable()
        self.stop.Bind(wx.EVT_BUTTON, self.on_stop)

        self.text = wx.TextCtrl(self, style=wx.TE_MULTILINE | wx.TE_READONLY | wx.VSCROLL)
        self.text.WriteText("IO Modules")

        grid = wx.GridBagSizer()
        grid.Add(ip_box_sizer, pos=(0, 0), flag=wx.ALL | wx.ALIGN_CENTER_VERTICAL, border=5)
        grid.Add(port_box_sizer, pos=(0, 1), flag=wx.ALL | wx.ALIGN_CENTER_VERTICAL, border=5)
        grid.Add(delay_box_sizer, pos=(0, 2), flag=wx.ALL | wx.ALIGN_CENTER_VERTICAL, border=5)
        grid.Add(self.start, pos=(0, 3), flag=wx.ALL | wx.ALIGN_CENTER_VERTICAL, border=5)
        grid.Add(self.stop, pos=(0, 4), flag=wx.ALL | wx.ALIGN_CENTER_VERTICAL, border=5)
        grid.Add(self.load, pos=(0, 5), flag=wx.ALL | wx.ALIGN_CENTER_VERTICAL, border=5)

        top_box_sizer.Add(grid, 0, wx.EXPAND | wx.ALL, 5)

        box = wx.BoxSizer(wx.VERTICAL)
        box.Add(top_box_sizer, 0, wx.ALIGN_CENTER | wx.ALL, 10)
        box.Add(self.text, 1, wx.ALL | wx.EXPAND, 10)
        self.SetSizerAndFit(box)

    def on_load(self, event=None):
        self.load.Disable()
        try:
            self.config = Config(ip=self.ip.GetValue(), port=self.port.GetValue())
        except Exception as e:
            wx.MessageBox(f"Error occurred while loading: {e}\nPlease re-check IP, Port or Network")
            self.config = None
            self.load.Enable()
            return
        self.wxconfig.Write("/nexxIP", self.ip.GetValue())
        self.wxconfig.Write("/nexxPort", self.port.GetValue())
        self.load.SetLabel("Reload IOs")
        self.load.Enable()
        self.start.Enable()

        self.text.Clear()
        self.text.WriteText("IO Modules\n\n")
        for io in self.config.IOs:
            self.text.WriteText(io + "\n")


    def on_start(self, event):
        try:
            delay = float(self.delay.GetValue())
        except Exception as e:
            wx.MessageBox("Delay should be a number", 'Error', wx.OK | wx.ICON_ERROR)
            return
        self.timer.Start(200)
        self.load.Disable()
        self.wxconfig.Write("/nexxIP", self.ip.GetValue())
        self.wxconfig.Write("/nexxPort", self.port.GetValue())
        self.wxconfig.Write("/nexxDelay", self.delay.GetValue())
        self.stop.Enable()
        self.start.Disable()
        self.inProgress = True
        ip = self.ip.GetValue()
        port = self.port.GetValue()
        thread = threading.Thread(target=self.execute_ssh_cmds, args=(ip, port, delay))
        thread.start()

    def on_stop(self, event=None):
        self.start.Enable()
        self.load.Enable()
        self.stop.Disable()
        self.inProgress = False
        if self.timer.IsRunning():
            self.timer.Stop()
        self.parent.SetStatusText("Complete :-)")


    def print_result(self, result: str, cmd):
        lines = result.split('\r\n')
        filtered_lines = [line for line in lines if line.strip() and '\r\r' not in line]
        filtered_result = '\n'.join(filtered_lines)
        self.parent.output.append(f"{cmd}'s output\n\n{filtered_result}\n\n\n")
        print(f"{cmd}'s output\n" + filtered_result)
        print("-----------------------------------------------------------------------\n\n")

    def OnTimer(self, event):
        """Called periodically while the flooder threads are running."""
        self.animation_counter += 1
        self.parent.SetStatusText(f"In progress{'.' * (self.animation_counter % 10)}")
