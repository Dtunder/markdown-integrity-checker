"""
Unit tests for the CLI entry point (`main.py`).
"""

import unittest
from unittest.mock import patch, MagicMock
import os
import sys
import tempfile
import io

from main import main

class TestMain(unittest.TestCase):
    """
    Test suite for the `main()` function in `main.py`.

    Validates argument parsing, error handling, output formatting, and exit codes.
    """

    def setUp(self):
        """Sets up a temporary directory for test files."""
        self.temp_dir = tempfile.TemporaryDirectory()
        self.root = self.temp_dir.name
        
    def tearDown(self):
        self.temp_dir.cleanup()
        
    def write_file(self, path: str, content: str):
        """
        Helper method to create a test file with given content.

        Args:
            path (str): The relative path of the file to create within the temp directory.
            content (str): The string content to write to the file.
        """
        full_path = os.path.join(self.root, path)
        os.makedirs(os.path.dirname(full_path), exist_ok=True)
        with open(full_path, 'w', encoding='utf-8') as f:
            f.write(content)

    @patch('sys.argv', ['main.py', 'nonexistent_dir'])
    @patch('sys.stderr', new_callable=io.StringIO)
    def test_nonexistent_directory(self, mock_stderr):
        """Tests that specifying a non-existent directory results in a sys.exit(1)."""
        with self.assertRaises(SystemExit) as cm:
            main()
        self.assertEqual(cm.exception.code, 1)
        self.assertTrue("Error: Directory 'nonexistent_dir' not found or is not a directory." in mock_stderr.getvalue())

    @patch('sys.stdout', new_callable=io.StringIO)
    @patch('sys.stderr', new_callable=io.StringIO)
    @patch('main.MarkdownChecker')
    def test_unexpected_runtime_error(self, mock_checker_class, mock_stderr, mock_stdout):
        """Tests that an unexpected exception during scan results in a sys.exit(1)."""
        mock_checker_instance = MagicMock()
        mock_checker_instance.scan.side_effect = Exception("Test unexpected error")
        mock_checker_class.return_value = mock_checker_instance
        
        with patch('sys.argv', ['main.py', self.root]):
            with self.assertRaises(SystemExit) as cm:
                main()
            self.assertEqual(cm.exception.code, 1)
            self.assertTrue("Unexpected Runtime Error during scan: Test unexpected error" in mock_stderr.getvalue())

    @patch('sys.stdout', new_callable=io.StringIO)
    def test_valid_directory_no_broken_links(self, mock_stdout):
        """Tests that scanning a valid directory with no broken links exits with code 0."""
        self.write_file('a.md', '# A\n[B](b.md)')
        self.write_file('b.md', '# B')
        
        with patch('sys.argv', ['main.py', self.root]):
            with self.assertRaises(SystemExit) as cm:
                main()
            self.assertEqual(cm.exception.code, 0)
            self.assertTrue("All internal links are valid. Great job!" in mock_stdout.getvalue())

    @patch('sys.stdout', new_callable=io.StringIO)
    def test_valid_directory_broken_links(self, mock_stdout):
        """Tests that scanning a valid directory with broken links exits with code 1."""
        self.write_file('a.md', '# A\n[Missing](missing.md)')
        
        with patch('sys.argv', ['main.py', self.root]):
            with self.assertRaises(SystemExit) as cm:
                main()
            self.assertEqual(cm.exception.code, 1)
            self.assertTrue("Found 1 broken link(s):" in mock_stdout.getvalue())
            self.assertTrue("File:" in mock_stdout.getvalue())
            self.assertTrue("missing.md" in mock_stdout.getvalue())

    @patch('sys.stdout', new_callable=io.StringIO)
    @patch('main.MarkdownChecker')
    def test_default_directory(self, mock_checker_class, mock_stdout):
        """Tests that the CLI defaults to the current directory ('.') if no argument is provided."""
        mock_checker_instance = MagicMock()
        mock_checker_instance.scan.return_value = []
        mock_checker_class.return_value = mock_checker_instance
        
        with patch('sys.argv', ['main.py']):
            with self.assertRaises(SystemExit) as cm:
                main()
            self.assertEqual(cm.exception.code, 0)
            mock_checker_class.assert_called_with('.')

if __name__ == '__main__':
    unittest.main()
