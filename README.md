# pydoll-substack2md

pydoll-substack2md is a Python tool for downloading free and premium Substack posts and saving them as both Markdown and HTML files, and includes a simple HTML interface to browse and sort through the posts.

This project is inspired by and forked from [timf34/Substack2Markdown](https://github.com/timf34/Substack2Markdown), and has been migrated from Selenium to Pydoll for improved performance and reliability.

The tool creates a folder structure organized by Substack author name, downloads posts as Markdown files, and generates an HTML interface for easy browsing.

## Features

- Converts Substack posts into Markdown files using html-to-markdown
- Generates an HTML file to browse Markdown files
- Supports free and premium content (with subscription)
- The HTML interface allows sorting essays by date or likes
- Async architecture for improved performance
- Direct Chrome DevTools Protocol connection via Pydoll
- Built-in Cloudflare bypass capability
- Resource blocking for faster page loads
- Concurrent post scraping support

## Requirements

- Python 3.10 or higher, Python 3.11 recommended
- Chrome or Edge browser installed

## Quick Start

Clone the repository:

```bash
git clone https://github.com/cognitive-glitch/pydoll-substack2md.git
cd pydoll-substack2md
```

### Run with uv (Recommended - No Installation Needed!)

```bash
# Run directly with uv - it handles all dependencies automatically
uv run pydoll-substack2md https://example.substack.com

# Or use the shorter alias
uv run substack2md https://example.substack.com

# With login for premium content
uv run substack2md https://example.substack.com --login

# Run with custom options
uv run substack2md https://example.substack.com -n 10 --headless
```

### Traditional Installation

If you prefer to install the package:

```bash
# Option 1: Using uv
uv venv
uv pip install -e .

# Option 2: Using pip
python -m venv venv
source venv/bin/activate  # Linux/Mac
.\venv\Scripts\activate   # Windows
pip install -e .
```

### Configuration

For premium content access, create a `.env` file:

```bash
# Copy the example file
cp .env.example .env

# Edit .env with your credentials
SUBSTACK_EMAIL=your-email@domain.com
SUBSTACK_PASSWORD=your-password
```

## Usage Examples

### Basic Usage

```bash
# Using uv run (no installation needed)
uv run substack2md https://example.substack.com

# Or if you installed the package
substack2md https://example.substack.com
pydoll-substack2md https://example.substack.com
```

### Premium Content

```bash
# Login for premium content access
uv run substack2md https://example.substack.com --login
uv run substack2md https://example.substack.com -l
```

### Advanced Options

```bash
# Scrape only 10 posts
uv run substack2md https://example.substack.com -n 10

# Run in headless mode (default is non-headless for user intervention)
uv run substack2md https://example.substack.com --headless

# Use concurrent scraping for better performance
uv run substack2md https://example.substack.com --concurrent --max-concurrent 5

# Specify custom directories
uv run substack2md https://example.substack.com -d ./posts --html-directory ./html

# Custom browser path
uv run substack2md https://example.substack.com --browser-path "/path/to/chrome"
```

## Output Structure

After running the tool, you'll find:

```
pydoll-substack2md/
├── substack_md_files/          # Markdown files organized by author
│   └── author-name/
│       ├── post-title-1.md
│       ├── post-title-2.md
│       └── ...
├── substack_html_pages/        # HTML interface for browsing
│   └── author-name.html
└── data/                       # JSON metadata for the HTML interface
    └── author-name_data.json
```

## Development

```bash
# Install development dependencies
uv pip install -e ".[dev]"

# Run tests
uv run pytest

# Format code
uv run black .

# Lint
uv run ruff check . --fix

# Type check
uv run pyright

# Run pre-commit hooks
pre-commit run --all-files
```

## Migration to Pydoll

This project has been migrated from Selenium to Pydoll for improved performance and reliability. Key benefits include:

- **Faster execution**: Direct Chrome DevTools Protocol connection
- **Better reliability**: Event-driven architecture for dynamic content
- **Async support**: Concurrent post scraping capabilities
- **Cloudflare handling**: Built-in bypass for protected sites
- **Resource optimization**: Block images/fonts for faster loading

## Environment Variables

Configure the tool using a `.env` file (see `.env.example` for template):

- `SUBSTACK_EMAIL`: Your Substack account email
- `SUBSTACK_PASSWORD`: Your Substack account password
- `HEADLESS`: Set to `true` for headless browser mode (default: `false`)
- `BROWSER_PATH`: Custom path to Chrome/Edge binary (optional)
- `USER_AGENT`: Custom user agent string (optional)

## Viewing Output

The tool generates both Markdown files and an HTML interface for easy viewing. To view the raw Markdown files in your browser, you can install the [Markdown Viewer](https://chromewebstore.google.com/detail/markdown-viewer/ckkdlimhmcjmikdlpkmbgfkaikojcbjk) browser extension.

Alternatively, you can use the [Substack Reader](https://www.substacktools.com/reader) online tool built by @Firevvork, which allows you to read and export free Substack articles directly in your browser without any installation. Note that premium content export is only available in the local version.

## Contributing

Contributions are welcome! Please ensure all tests pass and code is formatted before submitting a PR.

## License

MIT License - see [LICENSE](LICENSE) file for details.

## Acknowledgments

- Original project by [timf34](https://github.com/timf34/Substack2Markdown)
- Web version by [@Firevvork](https://github.com/Firevvork)
- Built with [Pydoll](https://github.com/pydoll/pydoll) and [html-to-markdown](https://github.com/Goldziher/html-to-markdown)
