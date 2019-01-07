import asyncio
import asyncio.transports


from typing import Optional


class TcpDiallerProtocol(asyncio.Protocol):
    def __init__(self, dialler):
        self.dialler = dialler
        self.fsm = self.dialler.fsm
        self.dialler.protocol = self

    def connection_made(self, transport: asyncio.transports.BaseTransport):
        self.transport = transport
        self.fsm.connected('')

    def data_received(self, data: bytes):
        for c in data:
            self.fsm.dte_output(chr(c))

    def connection_lost(self, exc: Optional[Exception]):
        self.fsm.disconnected()
        self.dialler.protocol = None


class TcpDialler:
    def __init__(self, loop, fsm):
        self.loop = loop
        self.fsm = fsm
        self.protocol = None

    def dial(self, number):
        (host, port) = number.split(':')
        c = self.loop.create_connection(
            lambda: TcpDiallerProtocol(self), host, int(port))
        self.loop.create_task(c)
        return (None, '', '')

    def hangup(self):
        if self.protocol and self.protocol.transport:
            self.protocol.transport.abort()

    def write(self, s):
        if self.protocol and self.protocol.transport:
            self.protocol.transport.write(s.encode())
