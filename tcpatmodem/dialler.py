import asyncio
import asyncio.transports

from typing import Optional


class Dialler:
    def __init__(self, loop, atfsm):
        self.loop = loop
        self.atfsm = atfsm
        self.protocol = None

    def hangup(self):
        pass

    def write(self):
        pass


class TcpDiallerProtocol(asyncio.Protocol):
    def __init__(self, dialler):
        self.dialler = dialler
        self.atfsm = self.dialler.atfsm
        self.dialler.protocol = self

    def connection_made(self, transport: asyncio.transports.BaseTransport):
        self.transport = transport
        self.atfsm.dialler_connected('')

    def data_received(self, data: bytes):
        for c in data:
            self.atfsm.dialler_received(chr(c))

    def connection_lost(self, exc: Optional[Exception]):
        self.atfsm.dialler_disconnected()
        self.dialler.protocol = None


class TcpDialler(Dialler):
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
