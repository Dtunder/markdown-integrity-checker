"""
Unit tests for the MarkdownChecker class.
"""

import os
import tempfile
import unittest
from markdown_checker import MarkdownChecker
from unittest.mock import patch

class TestMarkdownChecker(unittest.TestCase):
    """
    Test suite for the MarkdownChecker class.

    Validates the functionality of extracting and verifying internal markdown links.
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
            
    def test_valid_links(self):
        """Tests that valid internal links are correctly identified as not broken."""
        self.write_file('a.md', '# A\n[B](b.md)\n[A Section](#a-section)\n## A Section')
        self.write_file('b.md', '# B\n[A](a.md#a-section)')
        
        checker = MarkdownChecker(self.root)
        broken = checker.scan()
        self.assertEqual(len(broken), 0)
        
    def test_broken_file_link(self):
        """Tests that a link to a non-existent file is flagged as broken."""
        self.write_file('a.md', '# A\n[Missing](missing.md)')
        
        checker = MarkdownChecker(self.root)
        broken = checker.scan()
        self.assertEqual(len(broken), 1)
        self.assertEqual(broken[0]['url'], 'missing.md')
        self.assertTrue('File not found' in broken[0]['reason'])
        
    def test_broken_anchor_link(self):
        """Tests that a link to a non-existent anchor in the same file is flagged."""
        self.write_file('a.md', '# A\n[Missing Anchor](#missing)')
        
        checker = MarkdownChecker(self.root)
        broken = checker.scan()
        self.assertEqual(len(broken), 1)
        self.assertEqual(broken[0]['url'], '#missing')
        self.assertTrue('Anchor not found' in broken[0]['reason'])

    def test_broken_cross_file_anchor(self):
        """Tests that a link to a non-existent anchor in another file is flagged."""
        self.write_file('a.md', '# A\n[B missing](b.md#missing)')
        self.write_file('b.md', '# B\n## Valid')
        
        checker = MarkdownChecker(self.root)
        broken = checker.scan()
        self.assertEqual(len(broken), 1)
        self.assertEqual(broken[0]['url'], 'b.md#missing')
        self.assertTrue('Anchor not found' in broken[0]['reason'])

    def test_external_links_ignored(self):
        """Tests that external URLs (http, mailto, etc.) are ignored during verification."""
        self.write_file('a.md', '# A\n[Google](http://google.com)\n[Mail](mailto:test@test.com)')
        
        checker = MarkdownChecker(self.root)
        broken = checker.scan()
        self.assertEqual(len(broken), 0)

    def test_url_with_title(self):
        """Tests that markdown links containing optional title strings are parsed correctly."""
        self.write_file('a.md', '# A\n[B](b.md "B Title")\n[Missing](c.md "C Title")')
        self.write_file('b.md', '# B')
        
        checker = MarkdownChecker(self.root)
        broken = checker.scan()
        self.assertEqual(len(broken), 1)
        self.assertEqual(broken[0]['url'], 'c.md')

    def test_html_anchors(self):
        """Tests that explicit HTML anchor tags are recognized as valid link targets."""
        self.write_file('a.md', '# A\n<a name="html-anchor"></a>\n[HTML Anchor](#html-anchor)')
        checker = MarkdownChecker(self.root)
        broken = checker.scan()
        self.assertEqual(len(broken), 0)

    def test_extract_anchors_exception(self):
        """Tests the error handling when reading a file to extract anchors fails."""
        self.write_file('a.md', '# A')
        checker = MarkdownChecker(self.root)
        os.chmod(os.path.join(self.root, 'a.md'), 0o000)
        try:
            anchors = checker._extract_anchors(os.path.join(self.root, 'a.md'))
            self.assertEqual(len(anchors), 0)
        finally:
            os.chmod(os.path.join(self.root, 'a.md'), 0o644)

    def test_extract_links_exception(self):
        """Tests the error handling when reading a file to extract links fails."""
        self.write_file('a.md', '# A\n[B](b.md)')
        checker = MarkdownChecker(self.root)
        os.chmod(os.path.join(self.root, 'a.md'), 0o000)
        try:
            links = checker._extract_links(os.path.join(self.root, 'a.md'))
            self.assertEqual(len(links), 0)
        finally:
            os.chmod(os.path.join(self.root, 'a.md'), 0o644)

    def test_empty_url_parts(self):
        """Tests that empty URLs are handled without raising exceptions."""
        self.write_file('a.md', '# A\n[Empty]()')
        checker = MarkdownChecker(self.root)
        broken = checker.scan()
        self.assertEqual(len(broken), 0)
        
    def test_url_with_angle_brackets(self):
        """Tests that URLs wrapped in angle brackets are parsed correctly."""
        self.write_file('a.md', '# A\n[B](<b.md>)')
        self.write_file('b.md', '# B')
        checker = MarkdownChecker(self.root)
        broken = checker.scan()
        self.assertEqual(len(broken), 0)

    def test_absolute_path_link(self):
        """Tests that absolute paths relative to the root are resolved correctly."""
        self.write_file('a.md', '# A\n[B](/b.md)')
        self.write_file('b.md', '# B')
        checker = MarkdownChecker(self.root)
        broken = checker.scan()
        self.assertEqual(len(broken), 0)
        
    def test_target_is_directory(self):
        """Tests that a link pointing to a directory rather than a file is flagged as broken."""
        self.write_file('a.md', '# A\n[Dir](subdir)')
        os.makedirs(os.path.join(self.root, 'subdir'), exist_ok=True)
        checker = MarkdownChecker(self.root)
        broken = checker.scan()
        self.assertEqual(len(broken), 1)
        self.assertTrue('Target is not a file' in broken[0]['reason'])
        
    def test_anchor_in_cache_miss(self):
        """Tests the lazy loading of file anchors when resolving a cross-file anchor link."""
        self.write_file('a.md', '# A\n[B missing anchor](b.md#missing)')
        self.write_file('b.md', '# B')
        checker = MarkdownChecker(self.root)
        
        # force cache miss logic
        checker.file_anchors_cache = {} 
        
        # this will try to verify the link by reading b.md's anchors manually since it's not in cache
        broken = checker.scan()
        
        self.assertEqual(len(broken), 1)
        self.assertTrue('Anchor not found' in broken[0]['reason'])


    def test_whitespace_only_url(self):
        """Tests that URLs containing only whitespace are ignored safely."""
        self.write_file('a.md', '# A\n[Empty](   )')
        checker = MarkdownChecker(self.root)
        broken = checker.scan()
        self.assertEqual(len(broken), 0)

    def test_anchor_in_cache_miss_valid(self):
        """Tests lazy loading of file anchors for a valid link."""
        self.write_file('a.md', '# A\n[B anchor](b.md#valid)')
        self.write_file('b.md', '# B\n## Valid')
        checker = MarkdownChecker(self.root)
        
        # force cache miss logic
        checker.file_anchors_cache = {} 
        
        broken = checker.scan()
        
        self.assertEqual(len(broken), 0)
        
    def test_invalid_types_raise_errors(self):
        """Tests that TypeErrors are raised for invalid argument types across methods."""
        with self.assertRaises(TypeError):
            MarkdownChecker(123)
            
        checker = MarkdownChecker(self.root)
        
        with self.assertRaises(TypeError):
            checker._find_md_files(123)
            
        with self.assertRaises(TypeError):
            checker._generate_anchor(None)
            
        with self.assertRaises(TypeError):
            checker._extract_anchors(456)
            
        with self.assertRaises(TypeError):
            checker._extract_links(["not a string"])
            
        with self.assertRaises(TypeError):
            checker._verify_link(123, "url")
            
        with self.assertRaises(TypeError):
            checker._verify_link("source", 123)

    def test_invalid_directory_raises_value_error(self):
        """Tests that a ValueError is raised if the root directory does not exist."""
        with self.assertRaises(ValueError):
            MarkdownChecker("nonexistent_directory_that_really_should_not_exist")


    def test_file_read_fallback_triggered(self):
        """Tests that a UnicodeDecodeError triggers the fallback to return empty string."""
        self.write_file('a.md', '# A\n[B](b.md)')
        
        class FailingChecker(MarkdownChecker):
            def _read_file_content(self, filepath: str) -> str:
                raise UnicodeDecodeError('utf-8', b'', 0, 1, 'invalid start byte')
                
        # we still want the decorator applied to the override
        from resilience import fallback
        FailingChecker._read_file_content = fallback(fallback_func=MarkdownChecker._read_fallback, exceptions=(UnicodeDecodeError,))(FailingChecker._read_file_content)
        
        checker = FailingChecker(self.root)
        checker._parse_file(os.path.join(self.root, 'a.md'))
        self.assertEqual(len(checker.file_links_cache[os.path.join(self.root, 'a.md')]), 0)

    @patch('time.sleep', return_value=None)
    def test_file_read_retry_triggered(self, mock_sleep):
        """Tests that OSError correctly retries and ultimately fails."""
        self.write_file('a.md', '# A\n[B](b.md)')
        checker = MarkdownChecker(self.root)
        
        os.chmod(os.path.join(self.root, 'a.md'), 0o000)
        try:
            broken = checker.scan()
            self.assertEqual(len(broken), 0)
        finally:
            os.chmod(os.path.join(self.root, 'a.md'), 0o644)
            
    @patch('time.sleep', return_value=None)
    def test_file_read_retry_success(self, mock_sleep):
        """Tests that retry success works."""
        self.write_file('a.md', '# A\n[B](b.md)')
        
        class RetrySuccessChecker(MarkdownChecker):
            def __init__(self, *args, **kwargs):
                super().__init__(*args, **kwargs)
                self.calls = 0
            
            def _read_file_content(self, filepath: str) -> str:
                self.calls += 1
                if self.calls == 1:
                    raise OSError('error 1')
                with open(filepath, 'r', encoding='utf-8') as f:
                    return f.read()

        from resilience import retry, fallback
        RetrySuccessChecker._read_file_content = retry(exceptions=(OSError,), tries=3, delay=0.1)(RetrySuccessChecker._read_file_content)
        
        checker = RetrySuccessChecker(self.root)
        checker._parse_file(os.path.join(self.root, 'a.md'))
        self.assertEqual(len(checker.file_links_cache[os.path.join(self.root, 'a.md')]), 1)
        self.assertEqual(checker.calls, 2)

if __name__ == '__main__':
    unittest.main()
