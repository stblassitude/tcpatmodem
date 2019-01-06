import selectors
import socket


class TcpDialler:
    def __init__(self, fsm, sel):
        self.fsm = fsm
        self.sel = sel

    def dial(self, number):
        (host, port) = number.split(':')
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.setblocking(False)
        self.sock.connect_ex((host, int(port)))
        events = selectors.EVENT_READ | selectors.EVENT_WRITE
        self.sel.register(self.sock, events, data=self.handle)
        return (True, '', '')

    def handle(self, key, mask):
        if mask & selectors.EVENT_READ:
            self.fsm.dte_output(key.fileobj.recv(1024).decode('UTF-8'))
        if mask & selectors.EVENT_WRITE:
            if not self.fsm.connected:
                self.fsm.connected = True
                self.fsm.dte_response('CONNECTED')

    def write(self, s):
        self.sock.sendall(s)
