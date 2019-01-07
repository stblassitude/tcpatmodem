from io import StringIO
from unittest import TestCase
from unittest.mock import patch

from .atfsm import ATFSM, ATState


class ATFSMTest(TestCase):
    def setUp(self):
        self.dte = StringIO()
        self.dut = ATFSM(self.dte)

    def send_cmd(self, cmd):
        self.assertIn(self.dut.state, (ATState.IDLE, ATState.A))
        for c in 'AT' + cmd:
            self.dut.dte_input(c)
        self.dut.dte_input('\r')
        self.assertEqual(self.dut.state, ATState.A)

    def test_dte_input_invalid_state(self):
        self.dut.state = None
        with self.assertRaises(Exception):
            self.dut.dte_input(' ')

    def test_dte_input_at(self):
        self.dut.dte_input('\r')
        self.assertEqual(self.dut.state, ATState.A)

        self.dut.dte_input('\r')
        self.assertEqual(self.dut.state, ATState.A)
        self.dut.dte_input('a')
        self.assertEqual(self.dut.state, ATState.T)
        self.dut.dte_input('b')
        self.assertEqual(self.dut.state, ATState.IDLE)

        self.dut.dte_input('\r')
        self.assertEqual(self.dut.state, ATState.A)
        self.dut.dte_input('a')
        self.assertEqual(self.dut.state, ATState.T)
        self.dut.dte_input('t')
        self.assertEqual(self.dut.state, ATState.CMD)

    def test_dte_echo(self):
        self.send_cmd('E1')
        self.assertEqual(self.dte.getvalue(), 'ATE1\r\nOK\r\n')

    @patch.object(ATFSM, 'dte_command')
    def test_dte_input_a_slash(self, m):
        self.dut = ATFSM(self.dte)
        self.send_cmd('i4')
        self.dut.dte_input('\r')
        self.assertEqual(self.dut.state, ATState.A)
        self.dut.dte_input('a')
        self.assertEqual(self.dut.state, ATState.T)
        self.dut.dte_input('/')
        self.assertEqual(self.dut.state, ATState.A)
        m.assert_called_with('i4')
        self.assertEqual(m.call_count, 2)

    @patch.object(ATFSM, 'dte_command')
    def test_dte_input_cmd(self, m):
        self.dut = ATFSM(self.dte)
        self.send_cmd('')
        m.assert_called_once()
        self.assertEqual(self.dut.cmd, '')

    @patch.object(ATFSM, 'dte_command')
    def test_dte_input_cmd_i4(self, m):
        self.dut = ATFSM(self.dte)
        self.send_cmd('i4')
        m.assert_called_once()
        m.assert_called_once_with('i4')

    @patch.object(ATFSM, 'dte_command')
    def test_dte_input_cmd_with_backspace(self, m):
        self.dut = ATFSM(self.dte)
        self.send_cmd('i5\b4')
        m.assert_called_once_with('i4')

    @patch('tcpatmodem.atfsm.time')
    def test_dte_input_escape(self, time):
        self.dut.state = ATState.CONNECTED
        time.return_value = 0.1
        self.dut.dte_input('a')
        self.assertEqual(self.dut.dte_recv_ts, 0.1, 'patch of time.time() didn\'t work')
        self.assertEqual(self.dut.state, ATState.CONNECTED)
        self.dut.dte_input('+')
        self.assertEqual(self.dut.state, ATState.CONNECTED)

        time.return_value += self.dut.esc_timeout + 0.01
        self.dut.dte_input('+')
        self.assertEqual(self.dut.state, ATState.PLUS)
        self.dut.dte_input('+')
        self.assertEqual(self.dut.state, ATState.PLUS)
        self.dut.dte_input('+')
        self.assertEqual(self.dut.state, ATState.PLUSWAIT)
        self.assertEqual(self.dut.cmd, '+++')
        self.dut.check_escape()
        self.assertEqual(self.dut.state, ATState.PLUSWAIT)
        time.return_value += self.dut.esc_timeout + 0.01
        self.dut.check_escape()
        self.assertEqual(self.dut.state, ATState.A)

    def test_dte_command_invalid(self):
        r = self.dut.dte_command('-')
        self.assertFalse(r)
        self.assertEqual(self.dte.getvalue(), 'ERROR unknown command\r\n')

    def test_dte_command_empty(self):
        r = self.dut.dte_command('')
        self.assertTrue(r)
        self.assertEqual(self.dte.getvalue(), 'OK\r\n')

    def test_dte_command_e(self):
        r = self.dut.dte_command('e')
        self.assertTrue(r)
        self.assertEqual(self.dut.echo, False)
        self.assertEqual(self.dte.getvalue(), 'OK\r\n')

    def test_dte_command_e0(self):
        r = self.dut.dte_command('e0')
        self.assertTrue(r)
        self.assertEqual(self.dut.echo, False)
        self.assertEqual(self.dte.getvalue(), 'OK\r\n')

    def test_dte_command_e1(self):
        r = self.dut.dte_command('e1')
        self.assertTrue(r)
        self.assertEqual(self.dut.echo, True)
        self.assertEqual(self.dte.getvalue(), 'OK\r\n')

    def test_dte_command_i(self):
        r = self.dut.dte_command('i')
        self.assertTrue(r)
        self.assertEqual(self.dte.getvalue(), 'tcpatmodem 115200\r\n')

    def test_dte_command_i1(self):
        r = self.dut.dte_command('i1')
        self.assertTrue(r)
        self.assertNotEqual(self.dte.getvalue(), '')

    def test_dte_command_i2(self):
        r = self.dut.dte_command('i2')
        self.assertTrue(r)
        self.assertIn('https://github.com', self.dte.getvalue())

    def test_dte_command_o(self):
        r = self.dut.dte_command('q')
        self.assertTrue(r)
        self.assertEqual(self.dut.output, False)
        self.assertEqual(self.dte.getvalue(), '')

    def test_dte_command_o0(self):
        r = self.dut.dte_command('q0')
        self.assertTrue(r)
        self.assertEqual(self.dut.output, False)
        self.assertEqual(self.dte.getvalue(), '')
        r = self.dut.dte_command('q1')

    def test_dte_command_o1(self):
        r = self.dut.dte_command('q1')
        self.assertTrue(r)
        self.assertEqual(self.dut.output, True)
        self.assertEqual(self.dte.getvalue(), 'OK\r\n')

    def test_dte_command_s(self):
        r = self.dut.dte_command('s')
        self.assertTrue(r)
        self.assertEqual(self.dut.register, 0)
        r = self.dut.dte_command('s0')
        self.assertTrue(r)
        self.assertEqual(self.dut.register, 0)
        r = self.dut.dte_command('s1')
        self.assertTrue(r)
        self.assertEqual(self.dut.register, 1)

    def test_dte_command_v(self):
        r = self.dut.dte_command('v')
        self.assertTrue(r)
        self.assertEqual(self.dut.verbose, False)
        self.assertEqual(self.dte.getvalue(), '0\r\n')

    def test_dte_command_v0(self):

        r = self.dut.dte_command('v0')
        self.assertTrue(r)
        self.assertEqual(self.dut.verbose, False)
        self.assertEqual(self.dte.getvalue(), '0\r\n')

    def test_dte_command_v1(self):
        r = self.dut.dte_command('v1')
        self.assertTrue(r)
        self.assertEqual(self.dut.output, True)
        self.assertEqual(self.dte.getvalue(), 'OK\r\n')

    def test_dte_command_questionmark(self):
        r = self.dut.dte_command('?')
        self.assertTrue(r)
        self.assertEqual(self.dte.getvalue(), '0\r\nOK\r\n')

    def test_dte_command_questionmark2(self):
        r = self.dut.dte_command('s2?')
        self.assertEqual(self.dut.register, 2)
        self.assertTrue(r)
        self.assertEqual(self.dte.getvalue(), '43\r\nOK\r\n')

    def test_dte_command_questionmark3(self):
        r = self.dut.dte_command('s3?')
        self.assertTrue(r)
        self.assertEqual(self.dte.getvalue(), '13\r\nOK\r\n')

    def test_dte_command_questionmark4(self):
        r = self.dut.dte_command('s4?')
        self.assertTrue(r)
        self.assertEqual(self.dte.getvalue(), '10\r\nOK\r\n')

    def test_dte_command_questionmark5(self):
        r = self.dut.dte_command('s5?')
        self.assertTrue(r)
        self.assertEqual(self.dte.getvalue(), '8\r\nOK\r\n')

    def test_dte_command_questionmark12(self):
        r = self.dut.dte_command('s12?')
        self.assertTrue(r)
        self.assertEqual(self.dte.getvalue(), '100\r\nOK\r\n')

    def test_dte_command_equals(self):
        r = self.dut.dte_command('=')
        self.assertTrue(r)
        self.assertEqual(self.dte.getvalue(), 'OK\r\n')

    def test_dte_command_equals1(self):
        r = self.dut.dte_command('=1')
        self.assertTrue(r)
        self.assertEqual(self.dte.getvalue(), 'OK\r\n')

    def test_dte_command_equals99(self):
        r = self.dut.dte_command('S99=99')
        self.assertTrue(r)
        self.assertEqual(self.dte.getvalue(), 'OK\r\n')
        self.assertEqual(self.dut.quit, True)

    def test_dte_command_combined(self):
        r = self.dut.dte_command('e1q1s1=1?')
        self.assertEqual(self.dut.echo, True)
        self.assertEqual(self.dut.output, True)
        self.assertEqual(self.dut.register, 1)
        self.assertTrue(r)
        self.assertEqual(self.dte.getvalue(), '0\r\nOK\r\n')
