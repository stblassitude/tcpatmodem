import atexit
import sys
import termios
import tty

from os import isatty

old_settings = {}

def setraw(fd=sys.stdin.fileno()):
    global old_settings
    if not isatty(fd):
        return
    if fd in old_settings:
        return
    old_settings[fd] = termios.tcgetattr(fd)
    tty.setraw(fd)
    atexit.register(restore, fd)

def restore(fd=sys.stdin.fileno()):
    if fd not in old_settings:
        return
    termios.tcsetattr(fd, termios.TCSADRAIN, old_settings[fd])
    atexit.unregister(restore)
    del old_settings[fd]


if __name__ == '__main__':
    print(f'Testing raw input')
    setraw()
    c = sys.stdin.buffer.raw.read(1)
    print(f'Input: {ord(c)}\r')
    restore()
    print('Cooked again...')