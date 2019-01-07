import asyncio
import sys

from .atfsm import ATFSM
from.rawtty import setraw


class StdioFrontend:
    def __init__(self, dialler_class):
        self.fsm = ATFSM(sys.stdout)
        self.dialler_class = dialler_class

    def run(self):
        fd = sys.stdin.fileno()
        setraw(fd)
        self.loop = asyncio.get_event_loop()
        self.fsm.dialler = self.dialler_class(self.loop, self.fsm)
        self.loop.add_reader(fd, self.reader)
        self.loop.call_later(0.1, self.repeat)
        self.loop.run_forever()

    def repeat(self):
        self.fsm.check_escape()
        self.loop.call_later(0.1, self.repeat)
        if self.fsm.quit:
            self.loop.stop()

    def reader(self):
        b = sys.stdin.buffer.raw.read(1024)
        for c in b:
            self.fsm.dte_input(chr(c))
