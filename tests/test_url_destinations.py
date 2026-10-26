"""Regression tests for real Markdown URL destinations, using synthetic files."""
import os
import tempfile
import unittest
from markdown_checker import MarkdownChecker


class TestUrlDestinations(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)

    def write(self, name, content):
        path = os.path.join(self.temp.name, name)
        with open(path, "w", encoding="utf-8") as file:
            file.write(content)

    def broken(self):
        return MarkdownChecker(self.temp.name).scan()

    def test_percent_encoded_space_in_filename(self):
        self.write("index.md", "[Guide](space%20name.md)")
        self.write("space name.md", "# Guide")
        self.assertEqual(self.broken(), [])

    def test_percent_encoded_unicode_anchor(self):
        self.write("index.md", "[Section](guide.md#caf%C3%A9)")
        self.write("guide.md", "## Café")
        self.assertEqual(self.broken(), [])

    def test_angle_bracket_destination_with_spaces(self):
        self.write("index.md", "[Guide](<space name.md>)")
        self.write("space name.md", "# Guide")
        self.assertEqual(self.broken(), [])

    def test_query_string_does_not_change_local_file_path(self):
        self.write("index.md", "[Guide](guide.md?plain=1)")
        self.write("guide.md", "# Guide")
        self.assertEqual(self.broken(), [])

    def test_percent_encoded_hash_in_filename(self):
        self.write("index.md", "[Guide](section%23one.md)")
        self.write("section#one.md", "# Guide")
        self.assertEqual(self.broken(), [])

    def test_missing_percent_encoded_target_remains_broken(self):
        self.write("index.md", "[Missing](missing%20file.md)")
        broken = self.broken()
        self.assertEqual(len(broken), 1)
        self.assertEqual(broken[0]["url"], "missing%20file.md")
        self.assertIn("File not found", broken[0]["reason"])


if __name__ == "__main__":
    unittest.main()
