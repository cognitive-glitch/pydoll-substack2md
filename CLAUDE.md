# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**pydoll-substack2md** is a Python web scraper that downloads Substack newsletter posts and converts them to Markdown/HTML formats. The project uses Pydoll for browser automation and html-to-markdown for content conversion.

## Key Technology Stack

- **Browser Automation**: Pydoll - async Chrome DevTools Protocol (CDP) library (see `pydoll-comprehensive-docs.md`)
- **HTML to Markdown**: [html-to-markdown](https://github.com/Goldziher/html-to-markdown) - a robust Python library for HTML to Markdown conversion
- **Async Architecture**: All browser operations use Python's asyncio

## Commands

### Install Dependencies
```bash
# Using pip
pip install -e .

# Or install from requirements
pip install -r requirements.txt
```

### Run Scraper
```bash
# Free posts only
pydoll-substack2md <substack_url>

# With login for premium content
pydoll-substack2md <substack_url> -l

# Limit number of posts
pydoll-substack2md <substack_url> -n 10

# Run in headless mode (default is non-headless)
pydoll-substack2md <substack_url> --headless
```

## Architecture

### Core Components

1. **BaseSubstackScraper** (Abstract Base Class)
   - Manages URL discovery via sitemap.xml/feed.xml
   - Handles directory structure creation
   - Filters URLs by keywords
   - Fully async implementation with aiofiles

2. **PydollSubstackScraper** (Main Implementation)
   - Async browser automation using Pydoll's CDP connection
   - Event-driven content loading detection
   - Login handling for premium content with network interception
   - Concurrent post processing capabilities
   - Resource blocking for performance (images, fonts, media)
   - Built-in Cloudflare bypass support

3. **Content Processing Pipeline**
   - HTML extraction from Substack posts
   - Conversion to Markdown using html-to-markdown library
   - Metadata extraction (date, likes, title)
   - JSON data generation for HTML interface
   - Async file operations throughout

### Directory Structure
```
├── substack_md_files/      # Markdown output (organized by author)
├── substack_html_pages/    # HTML browsing interface
├── data/                   # JSON metadata files
└── assets/                 # CSS/JS for HTML interface
```

## Implementation Guidelines

### Key Pydoll Patterns for Substack

1. **Browser Initialization**
   ```python
   from pydoll.browser.chromium import Chrome

   async with Chrome() as browser:
       tab = await browser.start()
       await tab.go_to(url)
   ```

2. **Element Selection**
   ```python
   # Find by ID, class, or attributes
   element = await tab.find(id="email-input")
   element = await tab.find(class_name="post-content")
   elements = await tab.find(tag_name="article", find_all=True)
   ```

3. **Wait Strategies**
   ```python
   # Wait for specific elements
   content = await tab.find(id="post-content", timeout=10)

   # Wait for network idle
   await tab.wait_for_load_state("networkidle")
   ```

4. **Login Flow with Network Interception**
   ```python
   # Monitor authentication responses
   await tab.enable_network_events()

   async def capture_auth_response(tab, event):
       response = event['params']['response']
       if '/api/v1/login' in response['url'] and response['status'] == 200:
           # Capture authentication token
           pass

   await tab.on(NetworkEvent.RESPONSE_RECEIVED, partial(capture_auth_response, tab))
   ```

5. **Cloudflare Protection Handling**
   ```python
   # Pydoll has built-in Cloudflare bypass
   await tab.enable_auto_solve_cloudflare_captcha()
   await tab.go_to(url)
   # Or use context manager
   async with tab.expect_and_bypass_cloudflare_captcha():
       await tab.go_to(url)
   ```

### HTML to Markdown Conversion

Use html-to-markdown for robust conversion:
```python
from html_to_markdown import convert_to_markdown

# Basic conversion
markdown = convert_to_markdown(html_content)

# With options
markdown = convert_to_markdown(
    html_content,
    heading_style="atx",  # Use # style headers
    strong_em_symbol="*",  # Use * for bold/italic
    bullets="*+-",  # Bullet characters
    wrap=True,  # Enable text wrapping
    wrap_width=100,  # Set wrap width
    escape_asterisks=True,  # Escape * characters
    code_language="python",  # Default code block language
    strip=["script", "style", "meta", "head"],  # Remove these tags
)

# For migration from markdownify
from html_to_markdown import markdownify as md
# Works as drop-in replacement
```

## Important Considerations

1. **Authentication**: Login credentials are stored in `.env` file (SUBSTACK_EMAIL, SUBSTACK_PASSWORD)
2. **Rate Limiting**: Respect Substack's servers; use async delays between requests
3. **Browser Support**: Pydoll supports Chrome and Edge browsers natively
4. **Error Handling**: Leverage Pydoll's event system for robust error detection
5. **Python Version**: Requires Python ≥ 3.10 for Pydoll

## Testing Approach

When working with the Pydoll implementation:
1. Test basic scraping on a free Substack first
2. Verify login flow works for premium content using network monitoring
3. Ensure all metadata is correctly extracted through DOM queries
4. Validate Markdown output quality from html-to-markdown
5. Test concurrent scraping of multiple posts

## Performance Optimizations

1. **Concurrent Processing**: Use `asyncio.gather()` for parallel post scraping
2. **Event-Driven Loading**: Monitor network events to detect when content is ready
3. **Resource Filtering**: Block unnecessary resources during scraping:
   ```python
   # Block unnecessary resources
   await tab.enable_fetch_events(resource_type=ResourceType.IMAGE)
   await tab.enable_fetch_events(resource_type=ResourceType.FONT)

   async def block_resources(tab, event):
       request_id = event['params']['requestId']
       await browser.fail_request(request_id, NetworkErrorReason.BLOCKED_BY_CLIENT)

   await tab.on(FetchEvent.REQUEST_PAUSED, partial(block_resources, tab))
   ```
4. **Connection Reuse**: Keep browser instance alive for multiple operations

## Example: Scraping a Substack Post

```python
from pydoll.browser.chromium import Chrome
from pydoll.constants import NetworkEvent, FetchEvent, ResourceType, NetworkErrorReason
from html_to_markdown import convert_to_markdown
from functools import partial
import asyncio

async def scrape_substack_post(url: str) -> dict:
    async with Chrome() as browser:
        tab = await browser.start()

        # Block unnecessary resources for faster loading
        await tab.enable_fetch_events(resource_type=ResourceType.IMAGE)
        async def block_images(tab, event):
            request_id = event['params']['requestId']
            await browser.fail_request(request_id, NetworkErrorReason.BLOCKED_BY_CLIENT)
        await tab.on(FetchEvent.REQUEST_PAUSED, partial(block_images, tab))

        # Navigate to post
        await tab.go_to(url)

        # Wait for content to load
        article = await tab.find(tag_name="article", timeout=10)

        # Extract post data
        title_elem = await tab.find(tag_name="h1", class_name="post-title")
        title = await title_elem.text if title_elem else "Untitled"

        # Get post content HTML
        content_elem = await tab.find(class_name="post-content")
        content_html = await content_elem.inner_html if content_elem else ""

        # Convert to markdown
        markdown_content = convert_to_markdown(
            content_html,
            heading_style="atx",
            strip=["script", "style", "button", "svg"],
            code_language="python"
        )

        # Extract metadata
        date_elem = await tab.find(tag_name="time")
        date = await date_elem.get_attribute("datetime") if date_elem else ""

        return {
            "title": title,
            "content": markdown_content,
            "date": date,
            "url": url
        }
```

## Dependencies

Core dependencies for the project:
- `pydoll-python`: Browser automation via CDP (requires Python 3.10+)
- `html-to-markdown`: HTML to Markdown conversion (pip install html-to-markdown)
- `beautifulsoup4`: HTML parsing (used by both Pydoll and html-to-markdown)
- `aiofiles`: Async file operations
- `tqdm`: Progress bars (async-compatible)
- `aiohttp`: HTTP client (required by Pydoll)
- `websockets`: WebSocket communication (required by Pydoll)
- `python-dotenv`: Environment variable management
- `markdown`: Markdown to HTML conversion for preview pages
