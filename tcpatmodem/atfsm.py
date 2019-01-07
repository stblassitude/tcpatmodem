import re
import selectors

from enum import Enum
from time import time

ATState = Enum('ATState', 'IDLE A T CMD CONNECTING CONNECTED PLUS PLUSWAIT')
ATResultCode = {
    'OK': 0,
    'CONNECT': 1,
    'RING': 2,
    'NO CARRIER': 3,
    'ERROR': 4,
    'CONNECT 1200': 5,
    'NO DIALTONE': 6,
    'BUSY': 7,
    'NO ANSWER': 8,
    # there's no 9
    'CONNECT 2400': 10,
    'CONNECT 4800': 11,
    'CONNECT 9600': 12,
    'CONNECT 14400': 13,
    'CONNECT 19200': 14,
    # 15 to 21 missing
    'CONNECT 1200/75': 22,
    'CONNECT 75/1200': 23,
    'CONNECT 7200': 24,
    'CONNECT 12000': 25,
    # 26 and 27 missing
    'CONNECT 38400': 28,
}

starts_with_number_re = re.compile('^(\d*)(.*)$')


class ATFSM:
    def __init__(self, dte_file):
        self.dialler = None
        self.state = ATState.A
        self.dte_recv_ts = time()
        self.esc_char = '+'
        self.esc_timeout = 1.0
        self.cr_char = '\r'
        self.lf_char = '\n'
        self.bs_char = '\b'
        self.cmd = ''
        self.is_connected = False
        self.echo = True
        self.output = True
        self.verbose = True
        self.quit = False
        self.x = 0
        self.register = 0
        self.dte_file = dte_file
        self.commands = {
            'a': self.command_a,
            'd': self.command_d,
            'e': self.command_e,
            'h': self.command_h,
            'i': self.command_i,
            'l': self.command_l,
            'm': self.command_m,
            'o': self.command_o,
            'q': self.command_q,
            's': self.command_s,
            'v': self.command_v,
            'x': self.command_x,
            'z': self.command_z,
            ' ': self.command_space,
            '?': self.command_questionmark,
            '=': self.command_equals,
        }

    def check_escape(self):
        if self.state == ATState.PLUSWAIT and len(self.cmd) == 3 \
                and time() - self.dte_recv_ts > self.esc_timeout:
            self.dte_echo('\r\nOK\r\n')
            self.state = ATState.A

    def dce_output(self, c):
        if self.dialler:
            self.dialler.write(c)

    def dte_input(self, c):
        if self.state == ATState.IDLE:
            if c == '\r':
                self.state = ATState.A
            self.dte_echo(c)
        elif self.state == ATState.A:
            if c == 'a' or c == 'A':
                self.state = ATState.T
            elif c == '\r':
                self.state = ATState.A
            else:
                self.state = ATState.IDLE
            self.dte_echo(c)
        elif self.state == ATState.T:
            if c == '/':
                self.dte_echo(c)
                self.dte_echo('\r\n')
                self.state = ATState.A
                self.dte_command(self.cmd)
            else:
                if c == 't' or c == 'T':
                    self.state = ATState.CMD
                    self.cmd = ''
                elif c == '\r':
                    self.state = ATState.A
                else:
                    self.state = ATState.IDLE
                self.dte_echo(c)
        elif self.state == ATState.CMD:
            if c == '\r':
                self.dte_echo('\r\n')
                self.state = ATState.A
                self.dte_command(self.cmd)
            elif c == '\b':
                if len(self.cmd) > 0:
                    self.dte_echo('\b \b')
                    self.cmd = self.cmd[:-1]
            else:
                self.cmd += c
                self.dte_echo(c)
        elif self.state == ATState.CONNECTING:
            if self.dialler:
                self.dialler.hangup()
            self.disconnected()
        elif self.state == ATState.CONNECTED:
            if c == self.esc_char and time() - self.dte_recv_ts > self.esc_timeout:
                self.state = ATState.PLUS
                self.cmd = c
            else:
                self.dce_output(c)
        elif self.state == ATState.PLUS:
            if c == self.esc_char:
                self.cmd += c
                if len(self.cmd) == 3:
                    self.state = ATState.PLUSWAIT
            else:
                self.state = ATState.CONNECTED
                self.dce_output(self.cmd + c)
        elif self.state == ATState.PLUSWAIT:
            self.state = ATState.CONNECTED
            self.dce_output(self.cmd + c)
        else:
            raise Exception('Invalid internal state')
        self.dte_recv_ts = time()

    def dte_sel(self, key, mask):
        if mask & selectors.EVENT_READ:
            b = key.fileobj.read()
            for c in b:
                if c == '\n': # find a better way to get raw chars from a file
                    c = '\r'
                self.dte_input(c)
        if mask & selectors.EVENT_WRITE:
            pass # copy received data

    def dte_output(self, c):
        self.dte_file.write(c)
        self.dte_file.flush()

    def dte_echo(self, c):
        if self.echo:
            self.dte_output(c)

    def dte_response(self, s):
        if self.output:
            if self.verbose:
                self.dte_output(s + '\r\n')
            else:
                best = 'OK'
                for k in ATResultCode.keys():
                    if s[0:len(k)] == k and len(k) > len(best):
                        best = k
                self.dte_output(f'{ATResultCode[best]}\r\n')

    def dte_command(self, cmd):
        ok = True
        msg = 'OK'
        while len(cmd) > 0:
            c = cmd[0].lower()
            if c in self.commands:
                (ok, msg, cmd) = self.commands[c](cmd[1:])
                if ok is None:
                    return ok
                if not ok:
                    break
            else:
                msg = 'ERROR unknown command'
                ok = False
                break
        self.dte_response(msg)
        return ok

    def connected(self, msg=''):
        if len(msg) > 0:
            self.dte_response('CONNECT ' + msg)
        else:
            self.dte_response('CONNECT')
        self.is_connected = True
        self.state = ATState.CONNECTED

    def disconnected(self):
        self.dte_response('NO CARRIER')
        self.is_connected = False
        self.state = ATState.A

    def parse_number(self, cmd):
        m = starts_with_number_re.match(cmd)
        if m:
            n = m.group(1)
            n = int(n) if len(n) else 0
            return n, m.group(2)
        return None

    def command_nop_numeric(self, cmd):
        (n, cmd) = self.parse_number(cmd)
        if n is None:
            return (False, 'ERROR', '')
        return (True, 'OK', cmd)

    def command_a(self, cmd):
        return (False, 'ERROR not implemented', '')

    def command_d(self, cmd):
        if self.dialler:
            return self.dialler.dial(cmd)
        return (False, 'ERROR not implemented', '')

    def command_e(self, cmd):
        (n, cmd) = self.parse_number(cmd)
        if n is None:
            return (False, 'ERROR', '')
        self.echo = n == 1
        return (True, 'OK', cmd)

    def command_h(self, cmd):
        (n, cmd) = self.parse_number(cmd)
        if self.dialler:
            self.dialler.hangup()
        # return (True, 'NO CARRIER', cmd)
        return (None, '', '')

    def command_i(self, cmd):
        (n, cmd) = self.parse_number(cmd)
        if n is None:
            return (False, 'ERROR', '')
        if n == 0:
            i = 'tcpatmodem 115200'
        elif n == 1:
            i = 'v0.1'
        elif n == 2:
            i = 'https://github.com/stblassitude/tcpatmodem'
        else:
            return (False, 'ERROR', '')
        return (True, i, cmd)

    def command_l(self, cmd):
        return self.command_nop_numeric(cmd)

    def command_m(self, cmd):
        return self.command_nop_numeric(cmd)

    def command_o(self, cmd):
        if self.is_connected:
            self.state = ATState.CONNECTED
            return (True, 'CONNECTED', '')
        else:
            return (True, 'NO CARRIER', '')

    def command_q(self, cmd):
        (n, cmd) = self.parse_number(cmd)
        if n is None:
            return (False, 'ERROR', '')
        self.output = n == 1
        return (True, 'OK', cmd)

    def command_s(self, cmd):
        (n, cmd) = self.parse_number(cmd)
        if n is None:
            return (False, 'ERROR', '')
        self.register = n
        return (True, 'OK', cmd)

    def command_v(self, cmd):
        (n, cmd) = self.parse_number(cmd)
        if n is None:
            return (False, 'ERROR', '')
        self.verbose = n == 1
        return (True, 'OK', cmd)

    def command_x(self, cmd):
        (n, cmd) = self.parse_number(cmd)
        if n is None:
            return (False, 'ERROR', '')
        self.x = n
        return (True, 'OK', cmd)

    def command_z(self, cmd):
        return (False, 'ERROR not implemented', '')

    def command_space(self, cmd):
        return (True, 'OK', cmd)

    def command_questionmark(self, cmd):
        if self.register == 2:
            v = ord(self.esc_char)
        elif self.register == 3:
            v = ord(self.cr_char)
        elif self.register == 4:
            v = ord(self.lf_char)
        elif self.register == 5:
            v = ord(self.bs_char)
        elif self.register == 12:
            v = int(self.esc_timeout * 100)
        else:
            v = 0
        return (True, f'{v}\r\nOK', cmd)

    def command_equals(self, cmd):
        (n, cmd) = self.parse_number(cmd)
        if n is None:
            return (False, 'ERROR', '')
        if self.register == 2:
            self.esc_char = chr(n)
        elif self.register == 3:
            self.cr_char = chr(n)
        elif self.register == 4:
            self.lf_char = chr(n)
        elif self.register == 5:
            self.bs_char = chr(n)
        elif self.register == 12:
            self.esc_timeout = n * .01
        elif self.register == 99:
            self.quit = n == 99
        else:
            v = 0
        return (True, 'OK', cmd)
