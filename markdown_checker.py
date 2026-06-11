import os
import re
import sys
from typing import List, Tuple, Dict, Set

class MarkdownChecker:
    def __init__(self, root_dir: str):
        if not isinstance(root_dir, str):
            raise TypeError(f"root_dir must be a string, got {type(root_dir).__name__}")
        if not os.path.isdir(root_dir):
            raise ValueError(f"Directory not found or not a directory: {root_dir}")
        self.root_dir = os.path.abspath(root_dir)
        self.md_files = []
        self.file_anchors_cache: Dict[str, Set[str]] = {}

    def scan(self):
        self.md_files = self._find_md_files(self.root_dir)
        
        # Pre-cache anchors for all discovered files
        for f in self.md_files:
            self.file_anchors_cache[f] = self._extract_anchors(f)
            
        broken_links = []
        
        for file in self.md_files:
            links = self._extract_links(file)
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
        if not isinstance(directory, str):
            raise TypeError(f"directory must be a string, got {type(directory).__name__}")
        md_files = []
        for root, _, files in os.walk(directory):
            for file in files:
                if file.lower().endswith('.md'):
                    md_files.append(os.path.abspath(os.path.join(root, file)))
        return md_files

    def _generate_anchor(self, header_text: str) -> str:
        if not isinstance(header_text, str):
            raise TypeError(f"header_text must be a string, got {type(header_text).__name__}")
        header = header_text.strip().lower()
        header = re.sub(r'[^\w\s-]', '', header)
        header = re.sub(r'[-\s]+', '-', header)
        return header

    def _extract_anchors(self, filepath: str) -> Set[str]:
        if not isinstance(filepath, str):
            raise TypeError(f"filepath must be a string, got {type(filepath).__name__}")
        anchors = set()
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()
                content = re.sub(r'```.*?```', '', content, flags=re.DOTALL)
                content = re.sub(r'`[^`]*`', '', content)
                
                headers = re.findall(r'^#+\s+(.*)$', content, re.MULTILINE)
                for header in headers:
                    anchors.add(self._generate_anchor(header))
                    
                html_anchors = re.findall(r'<(?:a|div|span|h[1-6]).*?(?:name|id)=["\'](.*?)["\']', content)
                for a in html_anchors:
                    anchors.add(a)
        except (OSError, UnicodeDecodeError) as e:
            print(f"Warning: Could not read anchors from {filepath}: {e}", file=sys.stderr)
        return anchors

    def _extract_links(self, filepath: str) -> List[Tuple[str, str]]:
        if not isinstance(filepath, str):
            raise TypeError(f"filepath must be a string, got {type(filepath).__name__}")
        links = []
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()
                content_no_code = re.sub(r'```.*?```', '', content, flags=re.DOTALL)
                content_no_code = re.sub(r'`[^`]*`', '', content_no_code)
                
                raw_links = re.findall(r'\[([^\]]*)\]\(([^)]+)\)', content_no_code)
                
                for text, url_title in raw_links:
                    # Handle optional title in the url like `file.md "Title"`
                    url_parts = url_title.strip().split(maxsplit=1)
                    if not url_parts:
                        continue
                    url = url_parts[0]
                    # Clean < > if present
                    if url.startswith('<') and url.endswith('>'):
                        url = url[1:-1]
                        
                    if not url or re.match(r'^[a-zA-Z][a-zA-Z0-9+.-]*:', url):
                        continue
                        
                    links.append((text, url))
        except (OSError, UnicodeDecodeError) as e:
            print(f"Warning: Could not read links from {filepath}: {e}", file=sys.stderr)
        return links

    def _verify_link(self, source_file: str, url: str) -> Tuple[bool, str]:
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
            if abs_target_path not in self.file_anchors_cache:
                self.file_anchors_cache[abs_target_path] = self._extract_anchors(abs_target_path)
            if anchor not in self.file_anchors_cache[abs_target_path]:
                return False, f"Anchor not found: #{anchor}"
                
        return True, ""
