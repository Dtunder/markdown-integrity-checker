import os
import re
from typing import List, Tuple, Dict, Set

class MarkdownChecker:
    def __init__(self, root_dir: str):
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
        md_files = []
        for root, _, files in os.walk(directory):
            for file in files:
                if file.lower().endswith('.md'):
                    md_files.append(os.path.abspath(os.path.join(root, file)))
        return md_files

    def _generate_anchor(self, header_text: str) -> str:
        header = header_text.strip().lower()
        header = re.sub(r'[^\w\s-]', '', header)
        header = re.sub(r'[-\s]+', '-', header)
        return header

    def _extract_anchors(self, filepath: str) -> Set[str]:
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
        except Exception:
            pass
        return anchors

    def _extract_links(self, filepath: str) -> List[Tuple[str, str]]:
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
        except Exception:
            pass
        return links

    def _verify_link(self, source_file: str, url: str) -> Tuple[bool, str]:
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
