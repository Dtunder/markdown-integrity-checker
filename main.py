import argparse
import sys
import os
import logging
from markdown_checker import MarkdownChecker

def setup_logging():
    """
    Configures structured logging for the application.

    Sets up the Python built-in `logging` module to output logs to standard output.
    The verbosity level is determined by the `LOG_LEVEL` environment variable.
    If the variable is not set or contains an invalid level, it defaults to `INFO`.
    Logs are formatted to include the timestamp, logger name, severity level, and message.
    """
    log_level_str = os.environ.get("LOG_LEVEL", "INFO").upper()
    log_level = getattr(logging, log_level_str, logging.INFO)
    
    logging.basicConfig(
        level=log_level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[logging.StreamHandler(sys.stdout)]
    )

def main():
    """
    Entry point for the markdown-integrity-checker CLI tool.

    This function is responsible for:
    1. Initializing the application logging setup.
    2. Parsing command-line arguments to retrieve the target directory to scan.
    3. Validating the provided directory path.
    4. Initializing the `MarkdownChecker` with the given directory.
    5. Executing the scan and collecting the list of broken internal links.
    6. Outputting the results to the standard output and exiting with the
       appropriate status code (0 if all links are valid, 1 otherwise).

    Raises:
        SystemExit: Exits with code 1 if directory validation fails, 
                    if a configuration/runtime error occurs, or if broken links are found.
                    Exits with code 0 if the scan succeeds and no broken links are found.
    """
    setup_logging()
    logger = logging.getLogger(__name__)
    
    parser = argparse.ArgumentParser(description="Markdown Integrity Checker: Scans for broken internal links in markdown files.")
    parser.add_argument('directory', nargs='?', default='.', help="Directory to scan (default: current directory)")
    
    args = parser.parse_args()
    
    scan_dir = args.directory
    if not isinstance(scan_dir, str):
        logger.error("Invalid directory path type provided.")
        print(f"Error: Invalid directory path type.", file=sys.stderr)
        sys.exit(1)
        
    if not os.path.isdir(scan_dir):
        logger.error(f"Directory '{scan_dir}' not found or is not a directory.")
        print(f"Error: Directory '{scan_dir}' not found or is not a directory.", file=sys.stderr)
        sys.exit(1)
        
    abs_scan_dir = os.path.abspath(scan_dir)
    logger.info(f"Starting scan for directory: {abs_scan_dir}")
    print(f"Scanning directory: {abs_scan_dir}")
    
    try:
        logger.debug("Initializing MarkdownChecker.")
        checker = MarkdownChecker(scan_dir)
        logger.info("Beginning markdown link scan.")
        broken_links = checker.scan()
        logger.info("Scan completed successfully.")
    except (TypeError, ValueError) as e:
        logger.error(f"Configuration Error: {e}", exc_info=True)
        print(f"Configuration Error: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        logger.error(f"Unexpected Runtime Error during scan: {e}", exc_info=True)
        print(f"Unexpected Runtime Error during scan: {e}", file=sys.stderr)
        sys.exit(1)
    
    if not broken_links:
        logger.info("No broken internal links found.")
        print("\nAll internal links are valid. Great job!")
        sys.exit(0)
        
    logger.warning(f"Found {len(broken_links)} broken link(s).")
    print(f"\nFound {len(broken_links)} broken link(s):\n")
    for link in broken_links:
        logger.debug(f"Broken link in {link['source']}: '{link['text']}' -> {link['url']} ({link['reason']})")
        print(f"File: {link['source']}")
        print(f"  Link Text: '{link['text']}'")
        print(f"  URL: {link['url']}")
        print(f"  Reason: {link['reason']}")
        print("-" * 40)
        
    sys.exit(1)

if __name__ == "__main__":
    main()
