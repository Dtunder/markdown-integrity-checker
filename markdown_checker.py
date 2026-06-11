import os
import re
import sys
from typing import List, Tuple, Dict, Set

# Compiled regular expressions for optimization
RE_CODE_BLOCK = re.compile(r'```.*?```', flags=re.DOTALL)
RE_INLINE_CODE = re.compile(r'`[^`]*`')
RE_HEADER = re.compile(r'^#+\s+(.*)$', re.MULTILINE)
RE_HTML_ANCHOR = re.compile(r'<(?:a|div|span|h[1-6]).*?(?:name|id)=["\'](.*?)["\']')
RE_LINK = re.compile(r'\[([^\]]*)\]\(([^)]+)\)')
RE_NON_WORD_CHARS = re.compile(r'[^\w\s-]')
RE_DASH_SPACES = re.compile(r'[-\s]+')
RE_URL_SCHEME = re.compile(r'^[a-zA-Z][a-zA-Z0-9+.-]*:')

class MarkdownChecker:
    """A tool to scan a directory for markdown files and verify internal links."""

    def __init__(self, root_dir: str):
        if not isinstance(root_dir, str):
            raise TypeError(f"root_dir must be a string, got {type(root_dir).__name__}")
        if not os.path.isdir(root_dir):
            raise ValueError(f"Directory not found or not a directory: {root_dir}")
        self.root_dir = os.path.abspath(root_dir)
        self.md_files: List[str] = []
        self.file_anchors_cache: Dict[str, Set[str]] = {}
        self.file_links_cache: Dict[str, List[Tuple[str, str]]] = {}

    def scan(self) -> List[Dict[str, str]]:
        """
        Scans the root directory for markdown files and verifies internal links.
        Returns a list of dictionaries detailing broken links.
        """
        self.md_files = self._find_md_files(self.root_dir)
        broken_links = []
        
        # Process files only when needed, but typically we iterate through all to check their links.
        # However, anchors for other files are populated lazily inside _verify_link.
        for file in self.md_files:
            self._parse_file(file)
            links = self.file_links_cache.get(file, [])
            for link_text, url in links:
                is_valid, reason = self._verify_link(file, url)
                if not is_valid:
                    broken_links.append({
                        'source': file,
                        'text': link_text,
                        'url': url,
                        'reason': reason
                    })
                    
        return broken_links

    def _find_md_files(self, directory: str) -> List[str]:
        """Recursively finds all markdown files in the given directory."""
        if not isinstance(directory, str):
            raise TypeError(f"directory must be a string, got {type(directory).__name__}")
        md_files = []
        for root, _, files in os.walk(directory):
            for file in files:
                if file.lower().endswith('.md'):
                    md_files.append(os.path.abspath(os.path.join(root, file)))
        return md_files

    def _generate_anchor(self, header_text: str) -> str:
        """Converts a markdown header text into an HTML anchor ID."""
        if not isinstance(header_text, str):
            raise TypeError(f"header_text must be a string, got {type(header_text).__name__}")
        header = header_text.strip().lower()
        header = RE_NON_WORD_CHARS.sub('', header)
        header = RE_DASH_SPACES.sub('-', header)
        return header

    def _parse_file(self, filepath: str) -> None:
        """Parses a markdown file to extract its anchors and internal links, and caches them."""
        if filepath in self.file_anchors_cache:
            return  # Already parsed
            
        if not isinstance(filepath, str):
            raise TypeError(f"filepath must be a string, got {type(filepath).__name__}")
            
        anchors = set()
        links = []
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()
                # Remove code blocks and inline code to prevent false positives
                content_no_code = RE_CODE_BLOCK.sub('', content)
                content_no_code = RE_INLINE_CODE.sub('', content_no_code)
                
                # Extract headers for anchors
                headers = RE_HEADER.findall(content_no_code)
                for header in headers:
                    anchors.add(self._generate_anchor(header))
                    
                # Extract explicit HTML anchors
                html_anchors = RE_HTML_ANCHOR.findall(content_no_code)
                anchors.update(html_anchors)
                
                # Extract markdown links
                raw_links = RE_LINK.findall(content_no_code)
                
                for text, url_title in raw_links:
                    # Handle optional title in the url like `file.md "Title"`
                    url_parts = url_title.strip().split(maxsplit=1)
                    if not url_parts:
                        continue
                    url = url_parts[0]
                    # Clean < > if present
                    if url.startswith('<') and url.endswith('>'):
                        url = url[1:-1]
                        
                    if not url or RE_URL_SCHEME.match(url):
                        continue
                        
                    links.append((text, url))
        except (OSError, UnicodeDecodeError) as e:
            # We want to use the same print warning format to preserve backward compatibility
            print(f"Warning: Could not read anchors from {filepath}: {e}", file=sys.stderr)
            print(f"Warning: Could not read links from {filepath}: {e}", file=sys.stderr)
            
        self.file_anchors_cache[filepath] = anchors
        self.file_links_cache[filepath] = links

    def _extract_anchors(self, filepath: str) -> Set[str]:
        """Legacy helper maintained for test compatibility if any tests mock this."""
        self._parse_file(filepath)
        return self.file_anchors_cache.get(filepath, set())

    def _extract_links(self, filepath: str) -> List[Tuple[str, str]]:
        """Legacy helper maintained for test compatibility if any tests mock this."""
        self._parse_file(filepath)
        return self.file_links_cache.get(filepath, [])

    def _verify_link(self, source_file: str, url: str) -> Tuple[bool, str]:
        """Verifies if an internal link resolves to an existing file/anchor."""
        if not isinstance(source_file, str):
            raise TypeError(f"source_file must be a string, got {type(source_file).__name__}")
        if not isinstance(url, str):
            raise TypeError(f"url must be a string, got {type(url).__name__}")
            
        target_path = url
        anchor = None
        if '#' in url:
            target_path, anchor = url.split('#', 1)
            
        if not target_path:
            abs_target_path = source_file
        else:
            if target_path.startswith('/'):
                abs_target_path = os.path.abspath(os.path.join(self.root_dir, target_path.lstrip('/')))
            else:
                source_dir = os.path.dirname(source_file)
                abs_target_path = os.path.abspath(os.path.join(source_dir, target_path))
                
        if not os.path.exists(abs_target_path):
            return False, f"File not found: {target_path}"
            
        if not os.path.isfile(abs_target_path):
            return False, f"Target is not a file: {target_path}"
            
        if anchor and abs_target_path.lower().endswith('.md'):
            self._parse_file(abs_target_path)
            if anchor not in self.file_anchors_cache.get(abs_target_path, set()):
                return False, f"Anchor not found: #{anchor}"
                
        return True, ""
