# pydoll-substack2md

pydoll-substack2md is a Python tool for downloading free and premium Substack posts and saving them as both Markdown and HTML files, and includes a simple HTML interface to browse and sort through the posts.

This project is inspired by and forked from [timf34/Substack2Markdown](https://github.com/timf34/Substack2Markdown), and has been migrated from Selenium to Pydoll for improved performance and reliability.

The tool creates a folder structure organized by Substack author name, downloads posts as Markdown files, and generates an HTML interface for easy browsing.

## Features

- Converts Substack posts into Markdown files using html-to-markdown
- Generates an HTML file to browse Markdown files
- Supports free and premium content (with subscription)
- The HTML interface allows sorting essays by date or likes
- Downloads and saves images locally with rate limiting
- Async architecture for improved performance
- Direct Chrome DevTools Protocol connection via Pydoll
- Built-in Cloudflare bypass capability
- Resource blocking for faster page loads
- Concurrent post scraping support
- Continuous/incremental fetching - only download new posts since last run
- Automatic post numbering by date (oldest first)

## Requirements

- Python 3.10 or higher, Python 3.11 recommended
- Chrome or Edge browser installed

## Installation

### Install from PyPI (Recommended)

```bash
pip install substack2md
```

View on PyPI: https://pypi.org/project/substack2md/

### Install from Source

Clone the repository:

```bash
git clone https://github.com/cognitive-glitch/pydoll-substack2md.git
cd pydoll-substack2md
```

## Usage

After installing with `pip install substack2md`, you can use the command directly:

```bash
# Use the short command
substack2md https://example.substack.com

# Or the full command
substack2markdown https://example.substack.com

# With login for premium content
substack2md https://example.substack.com --login

# Manual login mode (works with any login method)
substack2md https://example.substack.com --manual-login

# Run with custom options
substack2md https://example.substack.com -n 10 --headless
```

### Running from Source with uv

If you cloned the repository and want to run without installing:

```bash
# Run directly with uv - it handles all dependencies automatically
uv run substack2md https://example.substack.com

# With login for premium content
uv run substack2md https://example.substack.com --login

# Run with custom options
uv run substack2md https://example.substack.com -n 10 --headless
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

## Advanced Options

```bash
# Scrape only 10 posts
substack2md https://example.substack.com -n 10

# Run in headless mode (default is non-headless for user intervention)
substack2md https://example.substack.com --headless

# Use concurrent scraping for better performance
substack2md https://example.substack.com --concurrent --max-concurrent 5

# Specify custom directories
substack2md https://example.substack.com -d ./posts --html-directory ./html

# Custom browser path
substack2md https://example.substack.com --browser-path "/path/to/chrome"

# Custom delay between requests (respectful rate limiting)
substack2md https://example.substack.com --delay-min 2 --delay-max 5

# Continuous/incremental mode - only fetch new posts since last run
substack2md https://example.substack.com --continuous
```

## Continuous Fetching & Post Numbering

### Automatic Post Numbering
Posts are automatically numbered based on their publication date (oldest first):
- `01-first-post-title.md`
- `02-second-post-title.md`
- `03-latest-post-title.md`

This makes it easy to read posts in chronological order.

### Continuous/Incremental Mode
Use the `--continuous` or `-c` flag to only fetch new posts since your last run:

```bash
# First run - fetches all posts
substack2md https://example.substack.com

# Later runs - only fetches new posts
substack2md https://example.substack.com --continuous
```

The tool maintains a `.scraping_state.json` file in the output directory to track:
- The latest post date and URL
- The highest number used
- Previously scraped URLs

This allows you to run the scraper periodically to keep your collection up-to-date without re-downloading existing posts.

## Output Structure

After running the tool, you'll find:

```
├── substack_md_files/      # Markdown versions of posts
│   └── {author_name}/      # Organized by Substack author
│       ├── images/         # Downloaded images for posts
│       │   ├── image1.jpg
│       │   └── image2.png
│       ├── post1.md
│       ├── post2.md
│       └── ...
├── substack_html_pages/    # HTML versions for browsing
│   └── {author_name}.html  # Single HTML file per author
├── data/                   # JSON metadata files
└── assets/                 # CSS/JS for HTML interface
```
pydoll-substack2md/
├── substack_md_files/          # Markdown files organized by author
│   └── author-name/
│       ├── post-title-1.md
│       ├── post-title-2.md
│       ├── ...
│       └── images/             # Downloaded images from posts
│           ├── image1.jpg
│           └── image2.png
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
