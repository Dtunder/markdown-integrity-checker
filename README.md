# markdown-integrity-checker

![Test Status](https://img.shields.io/badge/tests-passing-brightgreen)

Internal wiki/markdown link validator (checks for broken internal links).

This tool scans a directory recursively for markdown (`.md`) files. It extracts all internal relative markdown links (e.g. `[name](other_file.md#section)` or `[name](../dir/file.md)`) and verifies that the target files and sections/anchors exist. It generates a final summary report of any broken links.

## Installation

Ensure you have Python 3 installed. No external dependencies are required. Clone the repository and run the tool directly.

## Command Line Interface (CLI) Instructions

You can run the application directly from the command line:

```bash
python main.py [directory]
```

- `directory`: The directory to recursively scan. If omitted, it defaults to the current directory (`.`).

### Examples

Scanning the current directory:
```bash
python main.py
```

Scanning a specific directory:
```bash
python main.py /path/to/docs
```

### Exit codes
- `0`: All internal links are valid.
- `1`: One or more broken links were found, or the directory was invalid.

## Configuration Setup

The application uses Python's built-in `logging` module. You can control the verbosity of the output using the `LOG_LEVEL` environment variable.

Supported log levels are standard Python logging levels: `DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL`. The default log level is `INFO`.

**Example:**
```bash
# Run with maximum verbosity
LOG_LEVEL=DEBUG python main.py /path/to/docs

# Run silently (only output warnings and errors)
LOG_LEVEL=WARNING python main.py /path/to/docs
```

## API Reference Documentation

You can also use the `MarkdownChecker` programmatically in your own Python scripts.

```python
from markdown_checker import MarkdownChecker

# Initialize the checker with the root directory to scan
checker = MarkdownChecker('/path/to/docs')

# Run the scan
broken_links = checker.scan()

# Process results
if broken_links:
    for link in broken_links:
        print(f"File: {link['source']}")
        print(f"Broken Link: {link['text']} -> {link['url']}")
        print(f"Reason: {link['reason']}")
```

### `MarkdownChecker` Class

#### `__init__(self, root_dir: str)`
Initializes the checker.
- **`root_dir`**: The absolute or relative path to the directory containing markdown files.
- **Raises**: `TypeError` if `root_dir` is not a string. `ValueError` if the directory does not exist.

#### `scan(self) -> List[Dict[str, str]]`
Executes the scan across all markdown files found in the root directory.
- **Returns**: A list of dictionaries representing broken links. Each dictionary contains:
  - `source`: The absolute path of the file containing the link.
  - `text`: The visible text of the link.
  - `url`: The target URL (which may include an anchor `#`).
  - `reason`: A brief explanation of why the link is considered broken (e.g., "File not found", "Anchor not found").
