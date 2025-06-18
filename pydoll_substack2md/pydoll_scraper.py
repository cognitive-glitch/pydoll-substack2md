import argparse
import asyncio
import glob
import json
import os
import random
import re
import sys
from abc import ABC, abstractmethod
from datetime import datetime

# from functools import partial  # Unused import removed
from typing import Any, Tuple, List, Dict, Optional, Union
from urllib.parse import urljoin, urlparse
from xml.etree import ElementTree as ET

import aiofiles
import dateutil.parser
import markdown
import requests
from bs4 import BeautifulSoup
from dotenv import load_dotenv
from html_to_markdown import convert_to_markdown
from pydoll.browser.chromium import Chrome  # type: ignore
from pydoll.browser.options import ChromiumOptions  # type: ignore

# Note: Resource blocking feature temporarily disabled - imports not available in current Pydoll version
from tqdm.asyncio import tqdm

# Load environment variables
load_dotenv()

# Configuration from environment variables
SUBSTACK_EMAIL = os.getenv("SUBSTACK_EMAIL", "")
SUBSTACK_PASSWORD = os.getenv("SUBSTACK_PASSWORD", "")
USE_PREMIUM = os.getenv("USE_PREMIUM", "false").lower() == "true"
BASE_SUBSTACK_URL = os.getenv("DEFAULT_SUBSTACK_URL", "https://www.thefitzwilliam.com/")
NUM_POSTS_TO_SCRAPE = int(os.getenv("NUM_POSTS_TO_SCRAPE", "0"))
HEADLESS = os.getenv("HEADLESS", "false").lower() == "true"  # Default to non-headless for user intervention
BROWSER_PATH = os.getenv("BROWSER_PATH", "")
USER_AGENT = os.getenv("USER_AGENT", "")

# Directory configuration
BASE_MD_DIR = "substack_md_files"
BASE_HTML_DIR = "substack_html_pages"
HTML_TEMPLATE = "author_template.html"
JSON_DATA_DIR = "data"


def extract_main_part(url: str) -> str:
    """Extract the main part of a domain from a URL."""
    parts = urlparse(url).netloc.split(".")
    return parts[1] if parts[0] == "www" else parts[0]


async def generate_html_file(author_name: str) -> None:
    """Generates a HTML file for the given author."""
    if not os.path.exists(BASE_HTML_DIR):
        os.makedirs(BASE_HTML_DIR)

    json_path = os.path.join(JSON_DATA_DIR, f"{author_name}.json")
    async with aiofiles.open(json_path, encoding="utf-8") as file:
        content = await file.read()
        essays_data = json.loads(content)

    embedded_json_data = json.dumps(essays_data, ensure_ascii=False, indent=4)

    async with aiofiles.open(HTML_TEMPLATE, encoding="utf-8") as file:
        html_template = await file.read()

    html_with_data = html_template.replace("<!-- AUTHOR_NAME -->", author_name).replace(
        '<script type="application/json" id="essaysData"></script>',
        f'<script type="application/json" id="essaysData">{embedded_json_data}</script>',
    )
    html_with_author = html_with_data.replace("author_name", author_name)

    html_output_path = os.path.join(BASE_HTML_DIR, f"{author_name}.html")
    async with aiofiles.open(html_output_path, "w", encoding="utf-8") as file:
        await file.write(html_with_author)


class BaseSubstackScraper(ABC):
    """Abstract base class for Substack scrapers."""

    def __init__(
        self, base_substack_url: str, md_save_dir: str, html_save_dir: str, delay_range: Tuple[int, int] = (1, 3)
    ):
        if not base_substack_url.endswith("/"):
            base_substack_url += "/"
        self.base_substack_url = base_substack_url
        self.writer_name = extract_main_part(base_substack_url)

        md_save_dir = f"{md_save_dir}/{self.writer_name}"
        self.md_save_dir = md_save_dir
        self.html_save_dir = f"{html_save_dir}/{self.writer_name}"

        # Create directories if they don't exist
        os.makedirs(md_save_dir, exist_ok=True)
        print(f"Created md directory {md_save_dir}")
        os.makedirs(self.html_save_dir, exist_ok=True)
        print(f"Created html directory {self.html_save_dir}")

        # Create images directory
        self.images_dir = os.path.join(md_save_dir, "images")
        os.makedirs(self.images_dir, exist_ok=True)
        print(f"Created images directory {self.images_dir}")

        self.keywords = ["about", "archive", "podcast"]
        self.post_urls = self.get_all_post_urls()

        # Delay configuration for rate limiting
        self.delay_range = delay_range

    def get_all_post_urls(self) -> List[str]:
        """Attempts to fetch URLs from sitemap.xml, falling back to feed.xml if necessary."""
        urls = self.fetch_urls_from_sitemap()
        if not urls:
            urls = self.fetch_urls_from_feed()
        return self.filter_urls(urls, self.keywords)

    def load_scraping_state(self) -> Dict[str, Any]:
        """Load the scraping state from the metadata file."""
        state_file = os.path.join(self.md_save_dir, ".scraping_state.json")
        if os.path.exists(state_file):
            try:
                with open(state_file) as f:
                    return json.load(f)
            except Exception as e:
                print(f"Error loading scraping state: {e}")
        return {}

    async def save_scraping_state(self, state: Dict[str, Any]) -> None:
        """Save the scraping state to the metadata file."""
        state_file = os.path.join(self.md_save_dir, ".scraping_state.json")
        try:
            async with aiofiles.open(state_file, "w") as f:
                await f.write(json.dumps(state, indent=2))
        except Exception as e:
            print(f"Error saving scraping state: {e}")

    def _get_existing_urls_from_files(self) -> set[str]:
        """Get existing URLs from markdown files."""
        existing_urls = set()

        # Check all markdown files
        pattern = os.path.join(self.md_save_dir, "*.md")
        md_files = glob.glob(pattern)

        for filepath in md_files:
            filename = os.path.basename(filepath)

            # Handle date-prefixed files (YYYYMMDD-*.md)
            if len(filename) > 9 and filename[8] == "-":
                # Remove date prefix and .md extension
                url_part = filename[9:-3]
                existing_urls.add(url_part)
            else:
                # Handle old format files (just remove .md)
                url_part = filename[:-3]
                existing_urls.add(url_part)

        return existing_urls

    def fetch_urls_from_sitemap(self) -> List[str]:
        """Fetches URLs from sitemap.xml."""
        sitemap_url = f"{self.base_substack_url}sitemap.xml"
        try:
            response = requests.get(sitemap_url, timeout=10)
            if not response.ok:
                print(f"Error fetching sitemap at {sitemap_url}: {response.status_code}")
                return []

            root = ET.fromstring(response.content)
            urls = [
                element.text
                for element in root.iter("{http://www.sitemaps.org/schemas/sitemap/0.9}loc")
                if element.text
            ]
            print(f"Found {len(urls)} URLs in sitemap")
            return urls
        except Exception as e:
            print(f"Failed to fetch sitemap: {e}")
            return []

    def fetch_urls_from_feed(self) -> List[str]:
        """Fetches URLs from feed.xml."""
        print("Falling back to feed.xml. This will only contain up to the 22 most recent posts.")
        feed_url = f"{self.base_substack_url}feed.xml"
        try:
            response = requests.get(feed_url, timeout=10)
            if not response.ok:
                print(f"Error fetching feed at {feed_url}: {response.status_code}")
                return []

            root = ET.fromstring(response.content)
            urls: List[str] = []
            for item in root.findall(".//item"):
                link = item.find("link")
                if link is not None and link.text:
                    urls.append(link.text)
            print(f"Found {len(urls)} URLs in feed")
            return urls
        except Exception as e:
            print(f"Failed to fetch feed: {e}")
            return []

    @staticmethod
    def filter_urls(urls: List[str], keywords: List[str]) -> List[str]:
        """Filters out URLs that contain certain keywords."""
        filtered = [url for url in urls if all(keyword not in url for keyword in keywords)]
        print(f"Filtered {len(urls)} URLs to {len(filtered)} post URLs")
        return filtered

    @staticmethod
    def html_to_md(html_content: str) -> str:
        """Converts HTML to Markdown using html-to-markdown library."""

        return convert_to_markdown(
            html_content,
            heading_style="atx",
            strong_em_symbol="*",
            bullets="*+-",
            wrap=True,
            wrap_width=100,
            escape_asterisks=True,
            code_language="python",
            strip=["script", "style", "meta", "head", "button", "svg"],
        )

    @staticmethod
    async def save_to_file(filepath: str, content: str) -> None:
        """Saves content to a file asynchronously."""

        if os.path.exists(filepath):
            print(f"File already exists: {filepath}")
            return

        async with aiofiles.open(filepath, "w", encoding="utf-8") as file:
            await file.write(content)

    @staticmethod
    def md_to_html(md_content: str) -> str:
        """Converts Markdown to HTML."""
        return markdown.markdown(md_content, extensions=["extra"])

    async def save_to_html_file(self, filepath: str, content: str) -> None:
        """Saves HTML content to a file with CSS link."""

        html_dir = os.path.dirname(filepath)
        css_path = os.path.relpath("./assets/css/essay-styles.css", html_dir)
        css_path = css_path.replace("\\", "/")

        html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Substack Post</title>
    <link rel="stylesheet" href="{css_path}">
</head>
<body>
    <main class="markdown-content">
    {content}
    </main>
</body>
</html>"""

        async with aiofiles.open(filepath, "w", encoding="utf-8") as file:
            await file.write(html_content)

    @staticmethod
    def get_filename_from_url(url: str, filetype: str = ".md") -> str:
        """Gets the filename from the URL."""

        if not filetype.startswith("."):
            filetype = f".{filetype}"
        return url.split("/")[-1] + filetype

    @staticmethod
    def combine_metadata_and_content(title: str, subtitle: str, date: str, like_count: str, content: str) -> str:
        """Combines metadata and content into Markdown format."""

        metadata = f"# {title}\n\n"
        if subtitle:
            metadata += f"## {subtitle}\n\n"
        metadata += f"**{date}**\n\n"
        metadata += f"**Likes:** {like_count}\n\n"
        return metadata + content

    async def download_image(self, img_url: str, post_title: str, img_context: str = "", post_date: str = "") -> str:
        """Download image and return local path with descriptive filename."""
        try:
            # Clean the post title for use in filename
            safe_title = re.sub(r"[^\w\s-]", "", post_title).strip()
            safe_title = re.sub(r"[-\s]+", "-", safe_title)[:50]  # Limit length

            # Extract original filename or description from URL
            parsed_url = urlparse(img_url)
            path = parsed_url.path
            original_name = os.path.basename(path)
            name_without_ext = os.path.splitext(original_name)[0]
            ext = os.path.splitext(path)[1] or ".jpg"

            # Try to extract meaningful name from the original filename
            if name_without_ext and not name_without_ext.isdigit() and len(name_without_ext) > 3:
                # Clean the original name
                clean_name = re.sub(r"[^\w\s-]", "", name_without_ext).strip()
                clean_name = re.sub(r"[-\s]+", "-", clean_name)[:30]
            else:
                clean_name = ""

            # Build filename parts
            parts = []

            # Add date prefix if available
            if post_date:
                try:
                    parsed_date = dateutil.parser.parse(post_date)
                    date_prefix = parsed_date.strftime("%Y%m%d")
                    parts.append(date_prefix)
                except Exception:
                    pass

            # Add post title
            if safe_title:
                parts.append(safe_title)

            # Add image context or original name
            if img_context:
                clean_context = re.sub(r"[^\w\s-]", "", img_context).strip()
                clean_context = re.sub(r"[-\s]+", "-", clean_context)[:30]
                if clean_context:
                    parts.append(clean_context)
            elif clean_name:
                parts.append(clean_name)

            # Add a short hash for uniqueness (only 6 chars)
            img_hash = str(abs(hash(img_url)))[:6]
            parts.append(img_hash)

            # Create filename
            filename = "-".join(parts) + ext
            # Ensure filename isn't too long
            if len(filename) > 200:
                filename = filename[:196] + img_hash + ext

            local_path = os.path.join(self.images_dir, filename)

            # Check if already downloaded
            if os.path.exists(local_path):
                return f"images/{filename}"

            # Download with rate limiting
            print(f"  Downloading image: {filename}")
            response = requests.get(img_url, headers={"User-Agent": USER_AGENT}, timeout=30)
            response.raise_for_status()

            # Save image
            with open(local_path, "wb") as f:
                f.write(response.content)

            # Add small delay for rate limiting (30-100ms)
            delay = random.uniform(0.03, 0.1)
            await asyncio.sleep(delay)

            return f"images/{filename}"
        except Exception as e:
            print(f"  Error downloading image {img_url}: {e}")
        return img_url  # Return original URL on error

    async def process_images_in_content(self, content: str, post_title: str, post_date: str = "") -> str:
        """Process all images in content and replace with local paths."""
        soup = BeautifulSoup(content, "html.parser")
        images = soup.find_all("img")

        for img in images:
            if hasattr(img, "get") and hasattr(img, "__setitem__"):  # Type guard for Tag
                src = img.get("src")  # type: ignore
                if src and isinstance(src, str):  # Type guard
                    # Make URL absolute if relative
                    if not src.startswith(("http://", "https://")):
                        src = urljoin(self.base_substack_url, src)

                    # Extract image context from alt text or nearby text
                    img_context = ""
                    alt_text = img.get("alt", "")  # type: ignore
                    if alt_text and isinstance(alt_text, str):
                        img_context = alt_text[:50]  # Limit length

                    # Download image and get local path
                    local_path = await self.download_image(src, post_title, img_context, post_date)
                    img["src"] = local_path  # type: ignore

        return str(soup)

    async def extract_post_data(self, soup: BeautifulSoup, url: str) -> Tuple[str, str, str, str, str]:
        """Extracts post data from BeautifulSoup object."""
        # Title extraction
        title_elem = soup.select_one("h1.post-title, h2")
        title = title_elem.text.strip() if title_elem else "Untitled"

        # Subtitle extraction
        subtitle_elem = soup.select_one("h3.subtitle")
        subtitle = subtitle_elem.text.strip() if subtitle_elem else ""

        # Date extraction - try multiple selectors
        date = "Date not found"
        date_selectors = [
            "time",
            "div.post-meta time",
            "div[class*='meta'] time",
            "div.pencraft",
        ]
        for selector in date_selectors:
            date_elem = soup.select_one(selector)
            if date_elem:
                # Try to get datetime attribute first
                date_attr = date_elem.get("datetime")
                date = str(date_attr) if date_attr else date_elem.text.strip()
                if date:
                    break

        # Like count extraction
        like_count_elem = soup.select_one("a.post-ufi-button .label")
        like_count = "0"
        if like_count_elem:
            text = like_count_elem.text.strip()
            if text.isdigit():
                like_count = text

        # Content extraction - look for the actual content container
        content_elem = soup.select_one("div.available-content div.body.markup")
        if not content_elem:
            # Fallback to available-content
            content_elem = soup.select_one("div.available-content")
        if not content_elem:
            # Final fallback to article
            content_elem = soup.select_one("article")
        content = str(content_elem) if content_elem else ""

        # Process images before converting to markdown
        print(f"Processing images for: {title}")
        content = await self.process_images_in_content(content, title, date)

        md = self.html_to_md(content)
        md_content = self.combine_metadata_and_content(title, subtitle, date, like_count, md)
        return title, subtitle, like_count, date, md_content

    @abstractmethod
    async def get_url_soup(self, url: str) -> Optional[BeautifulSoup]:
        """Abstract method to get BeautifulSoup from URL."""
        raise NotImplementedError

    async def scrape_single_post_with_date(self, url: str) -> Optional[Dict[str, Any]]:
        """Scrape a single post and save with date-based filename."""
        try:
            # Get page content
            soup = await self.get_url_soup(url)
            if soup is None:
                return None

            # Extract date for filename
            date_str = "1970-01-01"
            date_selectors = ["time", "div.post-meta time", "div[class*='meta'] time"]
            for selector in date_selectors:
                date_elem = soup.select_one(selector)
                if date_elem:
                    date_attr = date_elem.get("datetime")
                    if date_attr:
                        date_str = str(date_attr)
                        break
                    elif date_elem.text.strip():
                        try:
                            parsed_date = dateutil.parser.parse(date_elem.text.strip())
                            date_str = parsed_date.isoformat()
                        except Exception:
                            date_str = date_elem.text.strip()
                        break

            # Convert to YYYYMMDD format
            try:
                parsed_date = dateutil.parser.parse(date_str)
                date_prefix = parsed_date.strftime("%Y%m%d")
            except Exception:
                date_prefix = "19700101"

            # Extract post data
            title, subtitle, like_count, date, md = await self.extract_post_data(soup, url)

            # Generate date-based filename
            base_filename = self.get_filename_from_url(url, filetype="")
            md_filename = f"{date_prefix}-{base_filename}.md"
            html_filename = f"{date_prefix}-{base_filename}.html"

            md_filepath = os.path.join(self.md_save_dir, md_filename)
            html_filepath = os.path.join(self.html_save_dir, html_filename)

            # Save files
            await self.save_to_file(md_filepath, md)

            # Convert markdown to HTML and save
            html_content = self.md_to_html(md)
            await self.save_to_html_file(html_filepath, html_content)

            return {
                "title": title,
                "subtitle": subtitle,
                "like_count": like_count,
                "date": date,
                "date_str": date_str,
                "url": url,
                "file_link": md_filepath,
                "html_link": html_filepath,
            }

        except Exception as e:
            print(f"Error scraping post {url}: {e}")
            return None

    async def save_essays_data_to_json(self, essays_data: List[Dict[str, Any]]) -> None:
        """Saves essays data to JSON file."""
        data_dir = os.path.join(JSON_DATA_DIR)
        os.makedirs(data_dir, exist_ok=True)

        json_path = os.path.join(data_dir, f"{self.writer_name}.json")
        existing_data: List[Dict[str, Any]] = []

        if os.path.exists(json_path):
            async with aiofiles.open(json_path, encoding="utf-8") as file:
                content = await file.read()
                loaded_data = json.loads(content)
                if isinstance(loaded_data, list):
                    existing_data = loaded_data  # type: ignore

        # Merge with existing data
        merged_data: List[Dict[str, Any]] = existing_data + [data for data in essays_data if data not in existing_data]

        async with aiofiles.open(json_path, "w", encoding="utf-8") as file:
            await file.write(json.dumps(merged_data, ensure_ascii=False, indent=4))

    async def scrape_posts(self, num_posts_to_scrape: int = 0, continuous: bool = False) -> None:
        """Scrapes posts asynchronously and saves them with date-based filenames.

        Args:
            num_posts_to_scrape: Number of posts to scrape (0 for all)
            continuous: If True, only scrape new posts since last run
        """
        print(f"Starting async scraping of posts from {self.base_substack_url}")

        # Load previous state
        state = self.load_scraping_state() if continuous else {}
        scraped_urls = set(state.get("scraped_urls", []))
        latest_date = state.get("latest_post_date")

        if continuous and latest_date:
            print(f"Continuous mode: Only fetching posts newer than {latest_date}")

        # Get existing URLs from files
        existing_urls = self._get_existing_urls_from_files()

        # Filter URLs
        urls_to_process = self.post_urls[:num_posts_to_scrape] if num_posts_to_scrape else self.post_urls
        filtered_urls = []

        for url in urls_to_process:
            original_filename = self.get_filename_from_url(url, filetype=".md")
            url_slug = original_filename.replace(".md", "")

            # Skip if already scraped in continuous mode
            if continuous and (url in scraped_urls or url_slug in existing_urls):
                print(f"Skipping already scraped: {original_filename}")
                continue

            # Check for existing files
            if not continuous:
                old_filepath = os.path.join(self.md_save_dir, original_filename)

                # Check for date-prefixed files
                pattern = "[0-9][0-9][0-9][0-9][0-9][0-9][0-9][0-9]-*.md"
                matching_files = glob.glob(os.path.join(self.md_save_dir, pattern))
                date_prefixed_exists = any(url_slug in file for file in matching_files)

                if os.path.exists(old_filepath) or date_prefixed_exists:
                    print(f"File already exists: {original_filename}")
                    continue

            filtered_urls.append(url)

        if not filtered_urls:
            print("No new posts to scrape.")
            return

        print(f"Found {len(filtered_urls)} posts to scrape")

        # Create async tasks
        semaphore = asyncio.Semaphore(3)  # Limit concurrent requests

        async def process_with_semaphore(url: str) -> Optional[Dict[str, Any]]:
            async with semaphore:
                # Add random delay to be respectful
                delay = random.uniform(self.delay_range[0], self.delay_range[1])
                await asyncio.sleep(delay)

                result = await self.scrape_single_post_with_date(url)
                if result and continuous and latest_date:
                    # Skip if older than latest date
                    if result["date_str"] <= latest_date:
                        print(f"Skipping older post (date: {result['date_str']})")
                        return None
                return result

        # Create tasks for all URLs
        tasks = [asyncio.create_task(process_with_semaphore(url)) for url in filtered_urls]

        # Process with progress bar
        essays_data = []
        with tqdm(total=len(tasks), desc="Scraping posts") as pbar:
            for coro in asyncio.as_completed(tasks):
                result = await coro
                if result:
                    essays_data.append(result)
                    scraped_urls.add(result["url"])
                pbar.update(1)

        # Save data and update state
        if essays_data:
            await self.save_essays_data_to_json(essays_data)
            print(f"✓ Scraped {len(essays_data)} posts successfully")

            # Update state for continuous mode
            if continuous:
                latest_post = max(essays_data, key=lambda x: x.get("date_str", ""))
                new_state = {
                    "latest_post_date": latest_post.get("date_str", ""),
                    "latest_post_url": latest_post.get("url", ""),
                    "scraped_urls": list(scraped_urls),
                    "last_update": datetime.now().isoformat(),
                }
                await self.save_scraping_state(new_state)

        # Generate HTML file
        await generate_html_file(self.writer_name)


class PydollSubstackScraper(BaseSubstackScraper):
    """Pydoll-based Substack scraper with async support."""

    def __init__(
        self,
        base_substack_url: str,
        md_save_dir: str,
        html_save_dir: str,
        headless: bool = False,
        browser_path: str = "",
        user_agent: str = "",
        delay_range: Tuple[int, int] = (1, 3),
        manual_login: bool = False,
    ):
        super().__init__(base_substack_url, md_save_dir, html_save_dir, delay_range)
        self.headless = headless
        self.browser_path = browser_path
        self.user_agent = user_agent
        self.browser = None
        self.tab = None
        self.auth_token = None
        self.is_logged_in = False
        self.manual_login = manual_login

    async def initialize_browser(self):
        """Initialize Pydoll browser with options."""
        options = ChromiumOptions()

        if self.headless:
            options.add_argument("--headless=new")

        if self.browser_path:
            options.binary_location = self.browser_path

        if self.user_agent:
            options.add_argument(f"user-agent={self.user_agent}")

        # Performance optimizations
        options.add_argument("--disable-blink-features=AutomationControlled")
        options.add_argument("--disable-notifications")
        options.add_argument("--disable-extensions")

        self.browser = Chrome(options=options)
        self.tab = await self.browser.start()

        # Enable network events for monitoring
        await self.tab.enable_network_events()

        # Resource blocking temporarily disabled
        # await self.setup_resource_blocking()

    # Resource blocking temporarily disabled - imports not available in current Pydoll version
    # async def setup_resource_blocking(self):
    #     """Set up resource blocking for faster page loads."""
    #     # Block images, fonts, and media
    #     for resource_type in [ResourceType.IMAGE, ResourceType.FONT, ResourceType.MEDIA]:
    #         await self.tab.enable_fetch_events(resource_type=resource_type)
    #
    #     async def block_resources(tab, event):
    #         request_id = event["params"]["requestId"]
    #         await self.browser.fail_request(request_id, NetworkErrorReason.BLOCKED_BY_CLIENT)
    #
    #     await self.tab.on(FetchEvent.REQUEST_PAUSED, partial(block_resources, self.tab))

    async def login(self) -> None:
        """Login to Substack using Pydoll."""
        if not SUBSTACK_EMAIL or not SUBSTACK_PASSWORD:
            print("No credentials provided, skipping login")
            return

        if self.tab is None:
            raise RuntimeError("Browser not initialized. Call initialize_browser() first.")

        print("Logging in to Substack...")

        # Network interception temporarily disabled - NetworkEvent not available in current Pydoll version
        # async def capture_auth_response(tab, event):
        #     response = event["params"]["response"]
        #     url = response["url"]
        #
        #     if "/api/v1/login" in url and response["status"] == 200:
        #         # Capture authentication success
        #         self.is_logged_in = True
        #         print("Login successful!")
        #
        # await self.tab.on(NetworkEvent.RESPONSE_RECEIVED, partial(capture_auth_response, self.tab))

        # Navigate to login page
        await self.tab.go_to("https://substack.com/sign-in")

        # Click "Sign in with password"
        signin_button = await self.tab.find(
            tag_name="a", class_name="login-option", text="Sign in with password", timeout=10
        )
        if signin_button:
            await signin_button.click()  # type: ignore

        # Wait for form to appear
        await asyncio.sleep(2)

        # Fill in credentials
        email_input = await self.tab.find(name="email", timeout=5)
        if email_input:
            await email_input.type_text(SUBSTACK_EMAIL, interval=0.05)  # type: ignore

        password_input = await self.tab.find(name="password", timeout=5)
        if password_input:
            await password_input.type_text(SUBSTACK_PASSWORD, interval=0.05)  # type: ignore

        # Submit form
        submit_button = await self.tab.find(tag_name="button", timeout=5)
        if submit_button:
            await submit_button.click()  # type: ignore

        # Wait for login to complete
        await asyncio.sleep(5)

        # Check for error
        error_container = await self.tab.find(id="error-container", timeout=2, raise_exc=False)
        if error_container:
            raise Exception("Login failed. Please check your credentials.")
        else:
            # Assume login successful if no error
            self.is_logged_in = True
            print("Login successful!")

    async def perform_manual_login(self) -> None:
        """Manual login mode - opens login page and waits for user to login manually."""
        if self.tab is None:
            raise RuntimeError("Browser not initialized. Call initialize_browser() first.")

        print("Opening Substack login page for manual login...")
        print("You will be able to login manually in the browser window.")

        # Navigate to login page
        await self.tab.go_to("https://substack.com/sign-in")

        # Wait for page to load
        await asyncio.sleep(2)

        print("\n" + "=" * 60)
        print("MANUAL LOGIN MODE")
        print("=" * 60)
        print("1. The browser should now show the Substack login page")
        print("2. Please login manually in the browser window")
        print("3. You can use any login method (email/password, Google, etc.)")
        print("4. Once you're logged in, press Enter to continue...")
        print("=" * 60)

        # Pause for manual login
        input("Press Enter after you have successfully logged in: ")

        # Verify login by checking for common logged-in elements
        print("Verifying login status...")

        # Check multiple indicators of being logged in
        # Try various selectors that indicate logged-in state

        # Check for user menu/avatar button
        user_menu = await self.tab.find(class_name="user-menu", timeout=3, raise_exc=False)
        avatar_button = await self.tab.query("button.avatarButton-lZBlGB", timeout=2, raise_exc=False)

        # Check for Dashboard button (only visible when logged in)
        dashboard_button = await self.tab.find(text="Dashboard", timeout=2, raise_exc=False)

        # Check for reader navigation elements (shown on home page when logged in)
        reader_nav = await self.tab.find(class_name="reader-nav-root", timeout=2, raise_exc=False)

        # Check for "Home" in the title (Substack home page after login)
        home_title = await self.tab.find(tag_name="h1", text="Home", timeout=2, raise_exc=False)

        # Check for subscriber-only elements
        subscriber_elem = await self.tab.query("[data-testid='subscriber-only']", timeout=2, raise_exc=False)

        # Check for any element containing user email or "Sign out" text
        signout_elem = await self.tab.find(text="Sign out", timeout=2, raise_exc=False)

        if (
            user_menu
            or avatar_button
            or dashboard_button
            or reader_nav
            or home_title
            or subscriber_elem
            or signout_elem
        ):
            self.is_logged_in = True
            print("✓ Login verification successful!")
            if dashboard_button or home_title:
                print("  (Detected Substack home page)")
        else:
            print("⚠ Warning: Could not verify login status. Continuing anyway...")
            print("If you encounter access issues with premium content, please try again.")
            self.is_logged_in = True  # Assume successful for manual mode

    async def get_url_soup(self, url: str) -> Optional[BeautifulSoup]:
        """Get BeautifulSoup from URL using Pydoll."""
        if self.tab is None:
            raise RuntimeError("Browser not initialized. Call initialize_browser() first.")

        try:
            # Enable Cloudflare bypass if needed
            async with self.tab.expect_and_bypass_cloudflare_captcha():
                await self.tab.go_to(url)

            # Wait for content to load - multiple strategies for thorough loading
            print("  Waiting for page to fully load...")

            # 1. Wait for page load event
            # Note: Pydoll doesn't have wait_for_load_state, so we use a simple delay
            # This could be enhanced with PageEvent.LOAD_EVENT_FIRED if needed
            await asyncio.sleep(2)
            print("  ✓ Initial page load delay completed")

            # 2. Wait for specific content indicators - check for the actual content div
            content_loaded = False

            # First try to find the body markup which contains the actual content
            # Note: Using CSS selector for multiple classes
            print("  Looking for content elements...")
            body_markup = await self.tab.query("div.body.markup", timeout=5, raise_exc=False)
            if body_markup:
                content_loaded = True
                print("  ✓ Found div.body.markup")
                # Wait a bit for any lazy-loaded content within the body
                await asyncio.sleep(1)
            else:
                # Try other selectors
                for selector in ["available-content", "article", "post-content"]:
                    content_elem = await self.tab.find(class_name=selector, timeout=3, raise_exc=False)
                    if content_elem:
                        content_loaded = True
                        print(f"  ✓ Found {selector}")
                        break

            # 3. Additional wait for dynamic content if needed
            if not content_loaded:
                # Last resort - wait for any article tag
                article = await self.tab.find(tag_name="article", timeout=5, raise_exc=False)
                if article:
                    content_loaded = True
                    await asyncio.sleep(2)  # Give extra time for content to render
                else:
                    # If still no content found, wait a bit longer
                    print("  Warning: Could not find expected content selectors")
                    await asyncio.sleep(3)

            # Check for paywall
            paywall = await self.tab.find(tag_name="h2", class_name="paywall-title", raise_exc=False)
            if paywall and not self.is_logged_in:
                print(f"Skipping premium article: {url}")
                return None

            # Get page source
            page_source = await self.tab.page_source
            return BeautifulSoup(page_source, "html.parser")

        except Exception as e:
            print(f"Error fetching page {url}: {e}")
            return None

    async def scrape_posts(self, num_posts_to_scrape: int = 0, continuous: bool = False) -> None:
        """Override to handle browser lifecycle."""
        try:
            await self.initialize_browser()

            # Login if premium scraping is enabled
            if USE_PREMIUM or (SUBSTACK_EMAIL and SUBSTACK_PASSWORD) or self.manual_login:
                if self.manual_login:
                    await self.perform_manual_login()
                else:
                    await self.login()

            # Call parent scrape_posts with continuous parameter
            await super().scrape_posts(num_posts_to_scrape, continuous)

        finally:
            if self.browser:
                await self.browser.stop()

    async def scrape_posts_concurrently(
        self, num_posts_to_scrape: int = 0, max_concurrent: int = 3, continuous: bool = False
    ) -> None:
        """Scrape posts concurrently for better performance."""
        try:
            await self.initialize_browser()

            if USE_PREMIUM or (SUBSTACK_EMAIL and SUBSTACK_PASSWORD) or self.manual_login:
                if self.manual_login:
                    await self.perform_manual_login()
                else:
                    await self.login()

            # Use the base class async scrape_posts method
            await super().scrape_posts(num_posts_to_scrape, continuous)

        finally:
            if self.browser:
                await self.browser.stop()

    async def scrape_single_post(self, url: str) -> Optional[Dict[str, Any]]:
        """Scrape a single post and return its data using date-based filenames."""
        # Simply delegate to the new method
        return await self.scrape_single_post_with_date(url)


def parse_args() -> argparse.Namespace:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Scrape a Substack site and convert posts to Markdown.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Scrape free posts from a Substack
  pydoll-substack2md https://example.substack.com

  # Scrape with login for premium content
  pydoll-substack2md https://example.substack.com -l

  # Manual login mode (works with any login method)
  pydoll-substack2md https://example.substack.com --manual-login

  # Scrape only 10 posts
  pydoll-substack2md https://example.substack.com -n 10

  # Run in headless mode (default is non-headless for user intervention)
  pydoll-substack2md https://example.substack.com --headless

  # Use concurrent scraping
  pydoll-substack2md https://example.substack.com --concurrent

  # Custom delay between requests (1-5 seconds)
  pydoll-substack2md https://example.substack.com --delay-min 1 --delay-max 5

  # Continuous mode - only fetch new posts since last run
  pydoll-substack2md https://example.substack.com --continuous
""",
    )

    parser.add_argument(
        "url",
        nargs="?",
        type=str,
        help="The base URL of the Substack site to scrape",
    )
    parser.add_argument(
        "-d",
        "--directory",
        type=str,
        default=BASE_MD_DIR,
        help="The directory to save scraped posts (default: substack_md_files)",
    )
    parser.add_argument(
        "-n",
        "--number",
        type=int,
        default=0,
        help="Number of posts to scrape (0 = all posts)",
    )
    parser.add_argument(
        "-l",
        "--login",
        action="store_true",
        help="Login to Substack for premium content (requires SUBSTACK_EMAIL and SUBSTACK_PASSWORD in .env)",
    )
    parser.add_argument(
        "--manual-login",
        action="store_true",
        help="Open login page and pause for manual login (works with any login method)",
    )
    parser.add_argument(
        "--headless",
        action="store_true",
        help="Run browser in headless mode (default: non-headless to allow user intervention)",
    )
    parser.add_argument(
        "--browser-path",
        type=str,
        default="",
        help="Path to Chrome/Edge browser executable",
    )
    parser.add_argument(
        "--user-agent",
        type=str,
        default="",
        help="Custom user agent string",
    )
    parser.add_argument(
        "--html-directory",
        type=str,
        default=BASE_HTML_DIR,
        help="Directory to save HTML files (default: substack_html_pages)",
    )
    parser.add_argument(
        "--concurrent",
        action="store_true",
        help="Use concurrent scraping for better performance",
    )
    parser.add_argument(
        "--max-concurrent",
        type=int,
        default=3,
        help="Maximum concurrent scraping tasks (default: 3)",
    )
    parser.add_argument(
        "--delay-min",
        type=float,
        default=1.0,
        help="Minimum delay between requests in seconds (default: 1.0)",
    )
    parser.add_argument(
        "--delay-max",
        type=float,
        default=3.0,
        help="Maximum delay between requests in seconds (default: 3.0)",
    )
    parser.add_argument(
        "--continuous",
        "-c",
        action="store_true",
        help="Enable continuous/incremental fetching mode - only scrape new posts since last run",
    )

    return parser.parse_args()


async def main():
    """Main entry point."""
    args = parse_args()

    # Use URL from args or environment
    url = args.url or BASE_SUBSTACK_URL
    if not url:
        print("Error: No Substack URL provided. Use -h for help.")
        sys.exit(1)

    # Determine if we should use premium scraping
    use_login = args.login or USE_PREMIUM or (SUBSTACK_EMAIL and SUBSTACK_PASSWORD)
    use_manual_login = args.manual_login

    # Validate manual login with headless mode
    if use_manual_login and (args.headless or HEADLESS):
        print("Error: Manual login mode cannot be used with headless mode")
        print("Either remove --manual-login or remove --headless")
        sys.exit(1)

    # Validate delay parameters
    if args.delay_min > args.delay_max:
        print("Error: --delay-min cannot be greater than --delay-max")
        sys.exit(1)

    print(f"Scraping: {url}")
    print(f"Login enabled: {use_login}")
    print(f"Manual login mode: {use_manual_login}")
    print(f"Headless mode: {args.headless or HEADLESS}")
    print(f"Delay range: {args.delay_min}-{args.delay_max} seconds")

    scraper = PydollSubstackScraper(
        base_substack_url=url,
        md_save_dir=args.directory,
        html_save_dir=args.html_directory,
        headless=args.headless or HEADLESS,
        browser_path=args.browser_path or BROWSER_PATH,
        user_agent=args.user_agent or USER_AGENT,
        delay_range=(args.delay_min, args.delay_max),
        manual_login=use_manual_login,
    )

    if args.concurrent:
        await scraper.scrape_posts_concurrently(
            num_posts_to_scrape=args.number or NUM_POSTS_TO_SCRAPE,
            max_concurrent=args.max_concurrent,
            continuous=args.continuous,
        )
    else:
        await scraper.scrape_posts(num_posts_to_scrape=args.number or NUM_POSTS_TO_SCRAPE, continuous=args.continuous)

    print("Scraping completed!")


def run():
    """Entry point for command line execution."""
    asyncio.run(main())


if __name__ == "__main__":
    run()
