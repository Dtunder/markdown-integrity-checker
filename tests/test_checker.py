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

if __name__ == '__main__':
    unittest.main()
