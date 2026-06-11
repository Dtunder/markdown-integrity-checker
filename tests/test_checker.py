import os
import tempfile
import unittest
from markdown_checker import MarkdownChecker

class TestMarkdownChecker(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.root = self.temp_dir.name
        
    def tearDown(self):
        self.temp_dir.cleanup()
        
    def write_file(self, path, content):
        full_path = os.path.join(self.root, path)
        os.makedirs(os.path.dirname(full_path), exist_ok=True)
        with open(full_path, 'w', encoding='utf-8') as f:
            f.write(content)
            
    def test_valid_links(self):
        self.write_file('a.md', '# A\n[B](b.md)\n[A Section](#a-section)\n## A Section')
        self.write_file('b.md', '# B\n[A](a.md#a-section)')
        
        checker = MarkdownChecker(self.root)
        broken = checker.scan()
        self.assertEqual(len(broken), 0)
        
    def test_broken_file_link(self):
        self.write_file('a.md', '# A\n[Missing](missing.md)')
        
        checker = MarkdownChecker(self.root)
        broken = checker.scan()
        self.assertEqual(len(broken), 1)
        self.assertEqual(broken[0]['url'], 'missing.md')
        self.assertTrue('File not found' in broken[0]['reason'])
        
    def test_broken_anchor_link(self):
        self.write_file('a.md', '# A\n[Missing Anchor](#missing)')
        
        checker = MarkdownChecker(self.root)
        broken = checker.scan()
        self.assertEqual(len(broken), 1)
        self.assertEqual(broken[0]['url'], '#missing')
        self.assertTrue('Anchor not found' in broken[0]['reason'])

    def test_broken_cross_file_anchor(self):
        self.write_file('a.md', '# A\n[B missing](b.md#missing)')
        self.write_file('b.md', '# B\n## Valid')
        
        checker = MarkdownChecker(self.root)
        broken = checker.scan()
        self.assertEqual(len(broken), 1)
        self.assertEqual(broken[0]['url'], 'b.md#missing')
        self.assertTrue('Anchor not found' in broken[0]['reason'])

    def test_external_links_ignored(self):
        self.write_file('a.md', '# A\n[Google](http://google.com)\n[Mail](mailto:test@test.com)')
        
        checker = MarkdownChecker(self.root)
        broken = checker.scan()
        self.assertEqual(len(broken), 0)

    def test_url_with_title(self):
        self.write_file('a.md', '# A\n[B](b.md "B Title")\n[Missing](c.md "C Title")')
        self.write_file('b.md', '# B')
        
        checker = MarkdownChecker(self.root)
        broken = checker.scan()
        self.assertEqual(len(broken), 1)
        self.assertEqual(broken[0]['url'], 'c.md')

    def test_html_anchors(self):
        self.write_file('a.md', '# A\n<a name="html-anchor"></a>\n[HTML Anchor](#html-anchor)')
        checker = MarkdownChecker(self.root)
        broken = checker.scan()
        self.assertEqual(len(broken), 0)

    def test_extract_anchors_exception(self):
        self.write_file('a.md', '# A')
        checker = MarkdownChecker(self.root)
        os.chmod(os.path.join(self.root, 'a.md'), 0o000)
        try:
            anchors = checker._extract_anchors(os.path.join(self.root, 'a.md'))
            self.assertEqual(len(anchors), 0)
        finally:
            os.chmod(os.path.join(self.root, 'a.md'), 0o644)

    def test_extract_links_exception(self):
        self.write_file('a.md', '# A\n[B](b.md)')
        checker = MarkdownChecker(self.root)
        os.chmod(os.path.join(self.root, 'a.md'), 0o000)
        try:
            links = checker._extract_links(os.path.join(self.root, 'a.md'))
            self.assertEqual(len(links), 0)
        finally:
            os.chmod(os.path.join(self.root, 'a.md'), 0o644)

    def test_empty_url_parts(self):
        self.write_file('a.md', '# A\n[Empty]()')
        checker = MarkdownChecker(self.root)
        broken = checker.scan()
        self.assertEqual(len(broken), 0)
        
    def test_url_with_angle_brackets(self):
        self.write_file('a.md', '# A\n[B](<b.md>)')
        self.write_file('b.md', '# B')
        checker = MarkdownChecker(self.root)
        broken = checker.scan()
        self.assertEqual(len(broken), 0)

    def test_absolute_path_link(self):
        self.write_file('a.md', '# A\n[B](/b.md)')
        self.write_file('b.md', '# B')
        checker = MarkdownChecker(self.root)
        broken = checker.scan()
        self.assertEqual(len(broken), 0)
        
    def test_target_is_directory(self):
        self.write_file('a.md', '# A\n[Dir](subdir)')
        os.makedirs(os.path.join(self.root, 'subdir'), exist_ok=True)
        checker = MarkdownChecker(self.root)
        broken = checker.scan()
        self.assertEqual(len(broken), 1)
        self.assertTrue('Target is not a file' in broken[0]['reason'])
        
    def test_anchor_in_cache_miss(self):
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
        self.write_file('a.md', '# A\n[Empty](   )')
        checker = MarkdownChecker(self.root)
        broken = checker.scan()
        self.assertEqual(len(broken), 0)

    def test_anchor_in_cache_miss_valid(self):
        self.write_file('a.md', '# A\n[B anchor](b.md#valid)')
        self.write_file('b.md', '# B\n## Valid')
        checker = MarkdownChecker(self.root)
        
        # force cache miss logic
        checker.file_anchors_cache = {} 
        
        broken = checker.scan()
        
        self.assertEqual(len(broken), 0)

if __name__ == '__main__':
    unittest.main()
