"""Bounded startup retries must tolerate resets without hiding permanent failure."""
import unittest
from unittest.mock import MagicMock, patch
from smoke_compose import read_url


class StartupRetryTests(unittest.TestCase):
    @patch('smoke_compose.time.sleep')
    @patch('smoke_compose.urllib.request.urlopen')
    def test_reset_then_ready(self, urlopen, sleep):
        response = MagicMock()
        response.__enter__.return_value.read.return_value = b'ready'
        urlopen.side_effect = [ConnectionResetError(), response]
        self.assertEqual(read_url('http://localhost'), 'ready')
        self.assertEqual(urlopen.call_count, 2)
        sleep.assert_called_once_with(1)

    @patch('smoke_compose.time.monotonic', side_effect=[0, 91])
    @patch('smoke_compose.urllib.request.urlopen', side_effect=ConnectionResetError())
    def test_deadline_raises(self, urlopen, clock):
        with self.assertRaises(ConnectionResetError):
            read_url('http://localhost')
        self.assertEqual(urlopen.call_count, 1)


if __name__ == '__main__':
    unittest.main()
