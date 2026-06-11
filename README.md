# markdown-integrity-checker

Internal wiki/markdown link validator (checks for broken internal links).

This tool scans a directory recursively for markdown (`.md`) files. It extracts all internal relative markdown links (e.g. `[name](other_file.md#section)` or `[name](../dir/file.md)`) and verifies that the target files and sections/anchors exist. It generates a final summary report of any broken links.

## Usage

```bash
python main.py [directory]
```

- `directory`: The directory to recursively scan. If omitted, it defaults to the current directory (`.`).

## Examples

Scanning the current directory:
```bash
python main.py
```

Scanning a specific directory:
```bash
python main.py /path/to/docs
```

## Exit codes
- `0`: All internal links are valid.
- `1`: One or more broken links were found, or the directory was invalid.
