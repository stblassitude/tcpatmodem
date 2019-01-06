import fcntl
import os
import selectors
import sys
import termios
import tty

from io import StringIO

from readchar import readchar

from .atfsm import ATFSM
from .tcpdialler import TcpDialler

# set sys.stdin non-blocking
orig_fl = fcntl.fcntl(sys.stdin, fcntl.F_GETFL)
fcntl.fcntl(sys.stdin, fcntl.F_SETFL, orig_fl | os.O_NONBLOCK)
tty.setraw(sys.stdin.fileno(), termios.TCSANOW)

sel = selectors.DefaultSelector()
fsm = ATFSM(sys.stdout)
dialler = TcpDialler(fsm, sel)
fsm.dialler = dialler
sel.register(sys.stdin, selectors.EVENT_READ, fsm.dte_sel)


while not fsm.quit:
    events = sel.select(timeout=0.1)
    for key, mask in events:
        if key.data is not None:
            key.data(key, mask)
    fsm.check_escape()

    # fsm.dte_input(readchar())
