import wx
import threading
import sys
import logging
import socket
import select
import SocketServer
import struct
import string
import hashlib
import json
import logging
import icon

def get_table(key):
    m = hashlib.md5()
    m.update(key)
    s = m.digest()
    (a, b) = struct.unpack('<QQ', s)
    table = [c for c in string.maketrans('', '')]
    for i in xrange(1, 1024):
        table.sort(lambda x, y: int(a % (ord(x) + i) - a % (ord(y) + i)))
    return table

def send_all(sock, data):
    bytes_sent = 0
    while True:
        r = sock.send(data[bytes_sent:])
        if r < 0:
            return r
        bytes_sent += r
        if bytes_sent == len(data):
            return bytes_sent

class ThreadingTCPServer(SocketServer.ThreadingMixIn, SocketServer.TCPServer):
    allow_reuse_address = True
    daemon_threads = True

class Socks5Server(SocketServer.StreamRequestHandler):
    def handle_tcp(self, sock, remote):
        try:
            fdset = [sock, remote]
            while True:
                r, w, e = select.select(fdset, [], [])
                if sock in r:
                    data = sock.recv(4096)
                    if len(data) <= 0:
                        break
                    result = send_all(remote, self.encrypt(data))
                    if result < len(data):
                        raise Exception('failed to send all data')

                if remote in r:
                    data = remote.recv(4096)
                    if len(data) <= 0:
                        break
                    result = send_all(sock, self.decrypt(data))
                    if result < len(data):
                        raise Exception('failed to send all data')
        finally:
            sock.close()
            remote.close()

    def encrypt(self, data):
        return data.translate(encrypt_table)

    def decrypt(self, data):
        return data.translate(decrypt_table)

    def send_encrypt(self, sock, data):
        sock.send(self.encrypt(data))

    def handle(self):
        try:
            sock = self.connection
            sock.recv(262)
            sock.send("\x05\x00")
            data = self.rfile.read(4) or '\x00' * 4
            mode = ord(data[1])
            if mode != 1:
                logging.warn('mode != 1')
                return
            addrtype = ord(data[3])
            addr_to_send = data[3]
            if addrtype == 1:
                addr_ip = self.rfile.read(4)
                addr = socket.inet_ntoa(addr_ip)
                addr_to_send += addr_ip
            elif addrtype == 3:
                addr_len = self.rfile.read(1)
                addr = self.rfile.read(ord(addr_len))
                addr_to_send += addr_len + addr
            else:
                logging.warn('addr_type not support')
                # not support
                return
            addr_port = self.rfile.read(2)
            addr_to_send += addr_port
            port = struct.unpack('>H', addr_port)
            try:
                reply = "\x05\x00\x00\x01"
                reply += socket.inet_aton('0.0.0.0') + struct.pack(">H", 2222)
                self.wfile.write(reply)
                # reply immediately
                if '-6' in sys.argv[1:]:
                    remote = socket.socket(socket.AF_INET6, socket.SOCK_STREAM)
                else:
                    remote = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                remote.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
                remote.connect((SERVER, REMOTE_PORT))
                self.send_encrypt(remote, addr_to_send)
                logging.info('connecting %s:%d' % (addr, port[0]))
            except socket.error, e:
                logging.warn(e)
                return
            self.handle_tcp(sock, remote)
        except socket.error, e:
            logging.warn(e)

with open('config.json', 'rb') as f:
    config = json.load(f)
SERVER = config['server']
REMOTE_PORT = config['server_port']
PORT = config['local_port']
KEY = config['password']
encrypt_table = ''.join(get_table(KEY))
decrypt_table = string.maketrans(encrypt_table, string.maketrans('', ''))

class WxLog(logging.Handler):
    def __init__(self, ctrl):
        logging.Handler.__init__(self)
        self.ctrl = ctrl
    def emit(self, record):
        self.ctrl.AppendText(self.format(record)+"\n")

class TaskBarIcon(wx.TaskBarIcon):
    ID_Play = wx.NewId()
    ID_About = wx.NewId()
    ID_Minshow=wx.NewId()
    ID_Maxshow=wx.NewId()
    ID_Closeshow=wx.NewId()
    ID_ShowFrame=wx.NewId()
    ID_ShowConfig=wx.NewId()

    def __init__(self,frame):
        wx.TaskBarIcon.__init__(self)
        self.frame = frame
        self.SetIcon(icon.getwxIcon(), u'shadowsocks')
        self.Bind(wx.EVT_TASKBAR_LEFT_DCLICK, self.OnTaskBarLeftDClick)
        self.Bind(wx.EVT_MENU, self.OnAbout, id=self.ID_About)
        self.Bind(wx.EVT_MENU, self.ShowFrame, id=self.ID_ShowFrame)
        self.Bind(wx.EVT_MENU, self.ShowConfig, id=self.ID_ShowConfig)
        self.Bind(wx.EVT_MENU, self.OnCloseshow, id=self.ID_Closeshow)

    def ShowConfig(self,event):
        cf = ConfigFrame()

    def OnTaskBarLeftDClick(self, event):
        if self.frame.IsIconized():
           self.frame.Iconize(False)
        if not self.frame.IsShown():
           self.frame.Show(True)
        self.frame.Raise()

    def OnAbout(self,event):
        wx.MessageBox(u'shadowsocks-wxPython', u'About')

    def OnCloseshow(self,event):
        self.frame.Close(True)

    def ShowFrame(self,event):
        if self.frame.IsIconized():
           self.frame.Iconize(False)
        if not self.frame.IsShown():
           self.frame.Show(True)
        self.frame.Raise()

    def CreatePopupMenu(self):
        menu = wx.Menu()
        menu.Append(self.ID_ShowFrame, 'Show Log')
        menu.Append(self.ID_ShowConfig, 'Config')
        menu.Append(self.ID_About, 'About')
        menu.Append(self.ID_Closeshow, 'Exit')
        return menu

class Frame(wx.Frame):
    def __init__(
            self, parent=None, id=wx.ID_ANY, title='shadowsocks-wxPython', pos=wx.DefaultPosition,
            size=wx.DefaultSize, style=wx.DEFAULT_FRAME_STYLE
            ):
        wx.Frame.__init__(self, parent, id, title, pos, size, style) 
        
        self.SetIcon(icon.getwxIcon())
        self.Bind(wx.EVT_CLOSE, self.OnClose)
        self.Bind(wx.EVT_ICONIZE, self.OnIconfiy)
        self.taskBarIcon = TaskBarIcon(self) 

        log = wx.TextCtrl(self, -1, '', size=(500,400), style=wx.TE_MULTILINE|wx.TE_READONLY)

        self.logr = logging.getLogger('')
        self.logr.setLevel(logging.DEBUG)
        hdlr = WxLog(log)
        hdlr.setFormatter(logging.Formatter('%(levelname)s |%(message)s'))
        self.logr.addHandler(hdlr)
    def OnIconfiy(self, event):
        self.Hide()
        event.Skip()
    def OnClose(self, event):
        threading.Thread(target=server.shutdown).start()
        try:
            self.taskBarIcon.Destroy()
        except wx._core.PyDeadObjectError, e:
            logging.info(e)
        self.Destroy()

class ConfigFrame(wx.Frame):
    def __init__(self):
        wx.Frame.__init__(self, None, -1, title = "Config",size=(300,180))
        self.SetIcon(icon.getwxIcon())
        panel = wx.Panel(self)
        gbs = wx.GridBagSizer(5,5)
        self.st1 = wx.StaticText(panel, label="Server")
        self.st2 = wx.StaticText(panel, label="Remote Port")
        self.st3 = wx.StaticText(panel, label="Local Port")
        self.st4 = wx.StaticText(panel, label="Key")
        self.tc1 = wx.TextCtrl(panel)
        self.tc2 = wx.TextCtrl(panel)
        self.tc3 = wx.TextCtrl(panel)
        self.tc4 = wx.TextCtrl(panel)
        self.tc1.SetValue(SERVER)
        self.tc2.SetValue(str(REMOTE_PORT))
        self.tc3.SetValue(str(PORT))
        self.tc4.SetValue(KEY)
        self.button1 = wx.Button(panel, label="Save")  
        self.button2 = wx.Button(panel, label="Cancel")  
        gbs.Add(self.st1, pos=(0,0), border=10, flag=wx.EXPAND|wx.LEFT|wx.RIGHT)
        gbs.Add(self.st2, pos=(1,0), border=10, flag=wx.EXPAND|wx.LEFT|wx.RIGHT)
        gbs.Add(self.st3, pos=(2,0), border=10, flag=wx.EXPAND|wx.LEFT|wx.RIGHT)
        gbs.Add(self.st4, pos=(3,0), border=10, flag=wx.EXPAND|wx.LEFT|wx.RIGHT)
        gbs.Add(self.tc1, pos=(0,1), border=10, flag=wx.EXPAND|wx.LEFT|wx.RIGHT)
        gbs.Add(self.tc2, pos=(1,1), border=10, flag=wx.EXPAND|wx.LEFT|wx.RIGHT)
        gbs.Add(self.tc3, pos=(2,1), border=10, flag=wx.EXPAND|wx.LEFT|wx.RIGHT)
        gbs.Add(self.tc4, pos=(3,1), border=10, flag=wx.EXPAND|wx.LEFT|wx.RIGHT)
        gbs.Add(self.button1, pos=(4,0), border=10, flag=wx.LEFT|wx.RIGHT)
        gbs.Add(self.button2, pos=(4,1), border=10, flag=wx.LEFT|wx.RIGHT)
        gbs.AddGrowableCol(1)
        self.Bind(wx.EVT_BUTTON, self.OnCloseWindow, self.button2)  
        self.Bind(wx.EVT_BUTTON, self.SaveConfig, self.button1)  
        panel.SetSizerAndFit(gbs)
        self.Center()
        self.Show()
        self.Raise()
    def OnCloseWindow(self, event):  
        self.Destroy()  
    def SaveConfig(self, event):
        SERVER = self.tc1.GetValue()
        REMOTE_PORT = int(self.tc2.GetValue())
        PORT = int(self.tc3.GetValue())
        KEY = self.tc4.GetValue()
        config['server'] = SERVER
        config['server_port'] = REMOTE_PORT
        config['local_port'] = PORT
        config['password'] = KEY
        with open('config.json', 'wb') as fw:
            json.dump(config,fw)
        server.shutdown()
        server = ThreadingTCPServer(('', PORT), Socks5Server)
        server.serve_forever()
        self.Destroy()

class myThread(threading.Thread):
    def __init__(self):
        threading.Thread.__init__(self)
 
    def run(self):
        logging.info("starting server at port %d ..." % PORT)
        server.serve_forever()

server = ThreadingTCPServer(('', PORT), Socks5Server)
app = wx.PySimpleApp()
frame = Frame(size=(520, 450))
frame.Centre()
th = myThread()
th.setDaemon(True)
th.start()
app.MainLoop()