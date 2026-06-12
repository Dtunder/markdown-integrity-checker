import unittest
from unittest.mock import patch, MagicMock
from resilience import retry, fallback


class TestResilience(unittest.TestCase):
    def test_retry_success(self):
        mock_func = MagicMock(return_value="success")

        @retry(exceptions=(ValueError,), tries=3, delay=0.1)
        def test_func():
            return mock_func()

        self.assertEqual(test_func(), "success")
        self.assertEqual(mock_func.call_count, 1)

    @patch('time.sleep', return_value=None)
    def test_retry_eventual_success(self, mock_sleep):
        mock_func = MagicMock(side_effect=[ValueError("error 1"), ValueError("error 2"), "success"])

        @retry(exceptions=(ValueError,), tries=3, delay=0.1)
        def test_func():
            return mock_func()

        self.assertEqual(test_func(), "success")
        self.assertEqual(mock_func.call_count, 3)

    @patch('time.sleep', return_value=None)
    def test_retry_failure(self, mock_sleep):
        mock_func = MagicMock(side_effect=ValueError("persistent error"))

        @retry(exceptions=(ValueError,), tries=3, delay=0.1)
        def test_func():
            return mock_func()

        with self.assertRaises(ValueError):
            test_func()
        self.assertEqual(mock_func.call_count, 3)

    def test_fallback_success(self):
        def fallback_func():
            return "fallback success"

        @fallback(fallback_func=fallback_func, exceptions=(ValueError,))
        def test_func():
            raise ValueError("error")

        self.assertEqual(test_func(), "fallback success")

    def test_fallback_not_triggered(self):
        def fallback_func():
            return "fallback success"

        @fallback(fallback_func=fallback_func, exceptions=(ValueError,))
        def test_func():
            return "primary success"

        self.assertEqual(test_func(), "primary success")


if __name__ == '__main__':
    unittest.main()
