import os
import re
import sys
import logging
from typing import List, Tuple, Dict, Set

logger = logging.getLogger(__name__)

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
    """
    A tool to scan a directory for markdown files and verify internal links.

    This class provides functionality to recursively traverse a given directory,
    parse all markdown files, extract internal relative links (including anchors),
    and verify that the target files and specific sections/anchors exist within
    the directory structure.

    Attributes:
        root_dir (str): The absolute path to the root directory to be scanned.
        md_files (List[str]): A list of absolute paths to all discovered markdown files.
        file_anchors_cache (Dict[str, Set[str]]): A cache mapping file paths to their generated anchor IDs.
        file_links_cache (Dict[str, List[Tuple[str, str]]]): A cache mapping file paths to lists of extracted links.
    """

    def __init__(self, root_dir: str) -> None:
        """
        Initializes the MarkdownChecker with the specified root directory.

        Args:
            root_dir (str): The path to the directory containing markdown files to scan.

        Raises:
            TypeError: If the provided `root_dir` is not a string.
            ValueError: If the provided `root_dir` does not exist or is not a directory.
        """
        if not isinstance(root_dir, str):
            raise TypeError(f"root_dir must be a string, got {type(root_dir).__name__}")
        if not os.path.isdir(root_dir):
            raise ValueError(f"Directory not found or not a directory: {root_dir}")
        self.root_dir = os.path.abspath(root_dir)
        logger.debug(f"MarkdownChecker initialized with root directory: {self.root_dir}")
        self.md_files: List[str] = []
        self.file_anchors_cache: Dict[str, Set[str]] = {}
        self.file_links_cache: Dict[str, List[Tuple[str, str]]] = {}

    def scan(self) -> List[Dict[str, str]]:
        """
        Scans the root directory for markdown files and verifies internal links.

        This is the primary method to execute the validation process. It finds all
        markdown files, parses them to extract internal links, and verifies each link
        against the cached files and anchors.

        Returns:
            List[Dict[str, str]]: A list of dictionaries detailing broken links. Each dictionary contains:
                - 'source' (str): The absolute path of the file containing the broken link.
                - 'text' (str): The display text of the broken link.
                - 'url' (str): The target URL of the broken link.
                - 'reason' (str): A description of why the link is considered broken.
        """
        logger.info(f"Scanning directory {self.root_dir} for markdown files.")
        self.md_files = self._find_md_files(self.root_dir)
        logger.info(f"Found {len(self.md_files)} markdown file(s).")

        broken_links = []

        # Process files only when needed, but typically we iterate through all to check their links.
        # However, anchors for other files are populated lazily inside _verify_link.
        for file in self.md_files:
            logger.debug(f"Scanning file for links: {file}")
            self._parse_file(file)
            links = self.file_links_cache.get(file, [])
            for link_text, url in links:
                is_valid, reason = self._verify_link(file, url)
                if not is_valid:
                    logger.debug(f"Broken link found in {file}: '{link_text}' -> {url} ({reason})")
                    broken_links.append({
                        'source': file,
                        'text': link_text,
                        'url': url,
                        'reason': reason
                    })

        return broken_links

    def _find_md_files(self, directory: str) -> List[str]:
        """
        Recursively finds all markdown files within a specified directory.

        Args:
            directory (str): The root directory path to start the recursive search.

        Returns:
            List[str]: A list of absolute file paths to all discovered markdown files (ending with '.md').

        Raises:
            TypeError: If the `directory` argument is not a string.
        """
        if not isinstance(directory, str):
            raise TypeError(f"directory must be a string, got {type(directory).__name__}")
        md_files = []
        for root, _, files in os.walk(directory):
            for file in files:
                if file.lower().endswith('.md'):
                    md_files.append(os.path.abspath(os.path.join(root, file)))
        return md_files

    def _generate_anchor(self, header_text: str) -> str:
        """
        Converts a markdown header text into an HTML anchor ID.

        Simulates how standard markdown renderers generate anchor links from headers.
        Converts the text to lowercase, removes non-word characters (excluding dashes),
        and replaces spaces with dashes.

        Args:
            header_text (str): The raw text of the markdown header.

        Returns:
            str: The generated HTML anchor ID string.

        Raises:
            TypeError: If `header_text` is not a string.
        """
        if not isinstance(header_text, str):
            raise TypeError(f"header_text must be a string, got {type(header_text).__name__}")
        header = header_text.strip().lower()
        header = RE_NON_WORD_CHARS.sub('', header)
        header = RE_DASH_SPACES.sub('-', header)
        return header

    def _parse_file(self, filepath: str) -> None:
        """
        Parses a markdown file to extract its anchors and internal links, and caches them.

        Reads the content of the file, strips out code blocks to avoid false positives,
        extracts all headers (to generate anchors), explicit HTML anchors, and markdown links.
        Results are stored in `self.file_anchors_cache` and `self.file_links_cache`.

        Args:
            filepath (str): The absolute path to the markdown file to be parsed.

        Raises:
            TypeError: If the `filepath` argument is not a string.
        """
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
            logger.warning(f"Could not parse file {filepath}: {e}", exc_info=True)
            # We want to use the same print warning format to preserve backward compatibility
            print(f"Warning: Could not read anchors from {filepath}: {e}", file=sys.stderr)
            print(f"Warning: Could not read links from {filepath}: {e}", file=sys.stderr)

        logger.debug(f"Parsed {filepath}: found {len(anchors)} anchors and {len(links)} internal links.")
        self.file_anchors_cache[filepath] = anchors
        self.file_links_cache[filepath] = links

    def _extract_anchors(self, filepath: str) -> Set[str]:
        """
        Extracts anchors from a given markdown file.

        This is a legacy helper method maintained primarily for test compatibility
        if any existing tests mock this specific function. It relies on `_parse_file`.

        Args:
            filepath (str): The absolute path to the markdown file.

        Returns:
            Set[str]: A set of anchor IDs found in the file. Returns an empty set if parsing fails or none are found.
        """
        self._parse_file(filepath)
        return self.file_anchors_cache.get(filepath, set())

    def _extract_links(self, filepath: str) -> List[Tuple[str, str]]:
        """
        Extracts internal links from a given markdown file.

        This is a legacy helper method maintained primarily for test compatibility
        if any existing tests mock this specific function. It relies on `_parse_file`.

        Args:
            filepath (str): The absolute path to the markdown file.

        Returns:
            List[Tuple[str, str]]: A list of tuples, where each tuple contains (link_text, url).
                                   Returns an empty list if parsing fails or no links are found.
        """
        self._parse_file(filepath)
        return self.file_links_cache.get(filepath, [])

    def _verify_link(self, source_file: str, url: str) -> Tuple[bool, str]:
        """
        Verifies if an internal link resolves to an existing file and/or anchor.

        Resolves the relative target URL against the source file's directory. Checks
        if the target file exists on the filesystem and, if an anchor is provided,
        parses the target file to ensure the anchor exists within it.

        Args:
            source_file (str): The absolute path of the file containing the link.
            url (str): The target URL of the link to verify (may include an anchor `#`).

        Returns:
            Tuple[bool, str]: A tuple where the first element is a boolean indicating
                              if the link is valid (True) or broken (False). The second
                              element is a string detailing the reason if the link is broken.

        Raises:
            TypeError: If `source_file` or `url` are not strings.
        """
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
            logger.debug(f"Verification failed: File not found ({abs_target_path})")
            return False, f"File not found: {target_path}"

        if not os.path.isfile(abs_target_path):
            logger.debug(f"Verification failed: Target is not a file ({abs_target_path})")
            return False, f"Target is not a file: {target_path}"

        if anchor and abs_target_path.lower().endswith('.md'):
            self._parse_file(abs_target_path)
            if anchor not in self.file_anchors_cache.get(abs_target_path, set()):
                logger.debug(f"Verification failed: Anchor not found ({anchor} in {abs_target_path})")
                return False, f"Anchor not found: #{anchor}"

        return True, ""
