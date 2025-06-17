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

## Installation

Clone the repo and install the dependencies:

```bash
git clone https://github.com/cognitive-glitch/pydoll-substack2md.git
cd pydoll-substack2md

# Option 1: Using uv (recommended - fast and efficient)
uv venv
source .venv/bin/activate  # Linux/Mac
.venv\Scripts\activate     # Windows

# Install with uv
uv pip install -e .
# Or install requirements directly
uv pip install -r requirements.txt

# Option 2: Using pip
python -m venv venv
source venv/bin/activate  # Linux/Mac
.\venv\Scripts\activate   # Windows

# Install the package
pip install -e .
# Or install requirements directly
pip install -r requirements.txt
```

For the premium scraper, create a `.env` file in the root directory with your Substack credentials:

```bash
# Copy the example file
cp .env.example .env

# Edit .env with your credentials
SUBSTACK_EMAIL=your-email@domain.com
SUBSTACK_PASSWORD=your-password
```

The tool uses Pydoll for browser automation, which works with Chrome or Microsoft Edge browsers.

## Usage

Run the tool using any of these commands:

### Basic Usage

```bash
# Using the installed command
substack2md https://example.substack.com

# Or using Python module
python -m pydoll_substack2md https://example.substack.com

# Or use the main command
pydoll-substack2md https://example.substack.com
```

### Scraping with Login (Premium Content)

```bash
# Login for premium content access
substack2md https://example.substack.com --login

# Or use short flag
substack2md https://example.substack.com -l
```

### Advanced Options

```bash
# Scrape only 10 posts
substack2md https://example.substack.com -n 10

# Run in headless mode (default is non-headless to allow user intervention)
substack2md https://example.substack.com --headless

# Use concurrent scraping for better performance
substack2md https://example.substack.com --concurrent --max-concurrent 5

# Specify custom directories
substack2md https://example.substack.com -d ./posts --html-directory ./html

# Custom browser path
substack2md https://example.substack.com --browser-path "/path/to/chrome"
```

## Migration to Pydoll

This project has been migrated from Selenium to Pydoll for improved performance and reliability. Key benefits include:

- **Faster execution**: Direct Chrome DevTools Protocol connection
- **Better reliability**: Event-driven architecture for dynamic content
- **Async support**: Concurrent post scraping capabilities
- **Cloudflare handling**: Built-in bypass for protected sites
- **Resource optimization**: Block images/fonts for faster loading
