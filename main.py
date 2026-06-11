import argparse
import sys
import os
from markdown_checker import MarkdownChecker

def main():
    """
    Entry point for the markdown-integrity-checker CLI tool.
    Parses arguments, initializes the MarkdownChecker, and outputs broken links if any.
    """
    parser = argparse.ArgumentParser(description="Markdown Integrity Checker: Scans for broken internal links in markdown files.")
    parser.add_argument('directory', nargs='?', default='.', help="Directory to scan (default: current directory)")
    
    args = parser.parse_args()
    
    scan_dir = args.directory
    if not isinstance(scan_dir, str):
        print(f"Error: Invalid directory path type.", file=sys.stderr)
        sys.exit(1)
        
    if not os.path.isdir(scan_dir):
        print(f"Error: Directory '{scan_dir}' not found or is not a directory.", file=sys.stderr)
        sys.exit(1)
        
    print(f"Scanning directory: {os.path.abspath(scan_dir)}")
    
    try:
        checker = MarkdownChecker(scan_dir)
        broken_links = checker.scan()
    except (TypeError, ValueError) as e:
        print(f"Configuration Error: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Unexpected Runtime Error during scan: {e}", file=sys.stderr)
        sys.exit(1)
    
    if not broken_links:
        print("\nAll internal links are valid. Great job!")
        sys.exit(0)
        
    print(f"\nFound {len(broken_links)} broken link(s):\n")
    for link in broken_links:
        print(f"File: {link['source']}")
        print(f"  Link Text: '{link['text']}'")
        print(f"  URL: {link['url']}")
        print(f"  Reason: {link['reason']}")
        print("-" * 40)
        
    sys.exit(1)

if __name__ == "__main__":
    main()
