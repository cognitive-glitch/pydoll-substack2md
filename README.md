# pydoll-substack2md

**A CAPTCHA-safe Substack scraper with automatic Cloudflare bypass and human-like behavior**

pydoll-substack2md is a Python tool for downloading free and premium Substack posts that handles modern web challenges:

🛡️ **Automatic Cloudflare bypass** - No manual intervention needed
🤖 **CAPTCHA handling** - Built-in solver for common challenges
🕰️ **Human-like scraping** - Random delays and respectful rate limiting
🔒 **Premium content support** - Login capability for paid subscriptions
📁 **Organized output** - Numbered posts by date, Markdown + HTML formats

Built on [Pydoll](https://github.com/pydoll/pydoll), a powerful browser automation library that handles anti-bot measures automatically.

## Key Features

### 🛡️ Anti-Bot Protection Handling
- **Automatic Cloudflare bypass** - No manual solving needed
- **CAPTCHA support** - Built-in handling for common challenges
- **Stealth mode** - Mimics real browser behavior
- **Smart retries** - Automatic retry with backoff strategies

### 🤖 Human-Like Scraping
- **Random delays** - Configurable delay ranges between requests
- **Respectful rate limiting** - Default 1-3 second delays
- **Browser fingerprinting** - Realistic browser profiles
- **Session persistence** - Maintains cookies and state

### 📥 Content Management
- **Markdown conversion** - Clean, readable Markdown files
- **Image downloading** - Local storage with smart naming
- **Post numbering** - Chronological ordering (01-oldest to newest)
- **Continuous updates** - Fetch only new posts on subsequent runs
- **Premium content** - Login support for paid subscriptions

### ⚡ Performance & Reliability
- **Concurrent scraping** - Multiple posts at once
- **Async architecture** - Non-blocking I/O operations
- **Resource optimization** - Blocks unnecessary assets
- **Error resilience** - Continues on individual post failures

## How It Handles Protected Sites

### Cloudflare Protection
When encountering Cloudflare's "Checking your browser" page, pydoll-substack2md:
1. Automatically detects the challenge
2. Waits for JavaScript execution
3. Solves challenges without user intervention
4. Proceeds with scraping once verified

### CAPTCHA Handling
The tool uses Pydoll's built-in CAPTCHA solving capabilities:
```python
# Automatic handling in the code
async with tab.expect_and_bypass_cloudflare_captcha():
    await tab.go_to(url)
```

### Human-Like Behavior
To avoid detection and respect servers:
- Random delays between 1-3 seconds (configurable)
- Realistic mouse movements and clicks
- Maintains browser session and cookies
- Uses real Chrome/Edge browser (not headless by default)

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
