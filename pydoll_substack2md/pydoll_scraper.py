"""
Pydoll Substack Scraper - Enhanced with CLAUDE.md Paywall Handling

Key improvements implemented:
1. Paywall Handling: Always try to click login button when paywall is detected
2. Timeout Optimization: Reduced timeouts throughout to avoid blocking too long with page fully loaded detection mechanism
3. Error Resilience: Added better error handling for element interactions
4. Performance: Optimized wait times while maintaining functionality

Following CLAUDE.md guidance for paywall handling and page load detection.
"""

import argparse
import asyncio
import glob
import json
import os
import random
import re
import sys
import time
from abc import ABC, abstractmethod
from datetime import datetime

# from functools import partial  # Unused import removed
from typing import Any
from urllib.parse import urljoin, urlparse
from xml.etree import ElementTree as ET

import aiofiles
import dateparser
import dateutil.parser
import markdown
import requests
import requests.exceptions
from bs4 import BeautifulSoup
from dotenv import load_dotenv
from html_to_markdown import convert_to_markdown
from pydoll.browser.chromium import Chrome  # type: ignore
from pydoll.browser.options import ChromiumOptions  # type: ignore
from pydoll.constants import Key  # type: ignore

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
    netloc = urlparse(url).netloc.lower()

    # Remove www. prefix if present
    if netloc.startswith("www."):
        netloc = netloc[4:]

    # Split by dots
    parts = netloc.split(".")

    # Handle special cases
    if len(parts) >= 2:
        # For substack.com domains, use the subdomain
        if parts[-2] == "substack" and parts[-1] == "com":
            return parts[0] if len(parts) > 2 else "substack"

        # For custom domains with subdomains (e.g., blog.paperswithbacktest.com)
        # Check if it's a known TLD pattern
        if len(parts) == 3 and parts[0] in ["blog", "newsletter", "mail", "read"]:
            # Use the main domain name
            return parts[1]

        # For research.hangukquant.com -> use full subdomain+domain
        if len(parts) == 3 and parts[0] not in ["www"]:
            return f"{parts[0]}-{parts[1]}"

        # For simple custom domains (e.g., algos.org, vertoxquant.com)
        # Use the main domain name without TLD
        if len(parts) == 2:
            return parts[0]

    # Fallback: use the first substantial part
    return parts[0] if parts else "unknown"


async def generate_html_file(author_name: str) -> None:
    """Generates a HTML file for the given author."""
    if not os.path.exists(BASE_HTML_DIR):
        os.makedirs(BASE_HTML_DIR)

    json_path = os.path.join(JSON_DATA_DIR, f"{author_name}.json")

    # Check if JSON file exists
    if not os.path.exists(json_path):
        print(f"No JSON data file found for {author_name}, skipping HTML generation")
        return

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
        self, base_substack_url: str, md_save_dir: str, html_save_dir: str, delay_range: tuple[int, int] = (1, 3)
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

    def get_all_post_urls(self) -> list[str]:
        """Attempts to fetch URLs from sitemap.xml, falling back to feed.xml if necessary."""
        urls = self.fetch_urls_from_sitemap()
        if not urls:
            urls = self.fetch_urls_from_feed()
            print("Warning: Falling back to feed.xml. This will only contain up to the 22 most recent posts.")
        return self.filter_urls(urls, self.keywords)

    def load_scraping_state(self) -> dict[str, Any]:
        """Load the scraping state from the metadata file."""
        state_file = os.path.join(self.md_save_dir, ".scraping_state.json")
        if os.path.exists(state_file):
            try:
                with open(state_file) as f:
                    return json.load(f)
            except Exception as e:
                print(f"Error loading scraping state: {e}")
        return {}

    async def save_scraping_state(self, state: dict[str, Any]) -> None:
        """Save the scraping state to the metadata file."""
        state_file = os.path.join(self.md_save_dir, ".scraping_state.json")
        try:
            async with aiofiles.open(state_file, "w") as f:
                await f.write(json.dumps(state, indent=2))
        except Exception as e:
            print(f"Error saving scraping state: {e}")

    def _get_existing_urls_from_files(self) -> set[str]:
        """Get existing URLs from markdown files.

        Returns a set of URL slugs that have already been downloaded.
        Handles both date-prefixed (YYYYMMDD-slug.md) and old format (slug.md) files.
        """
        existing_urls = set()

        # Check all markdown files
        pattern = os.path.join(self.md_save_dir, "*.md")
        md_files = glob.glob(pattern)

        for filepath in md_files:
            filename = os.path.basename(filepath)

            # Handle date-prefixed files (YYYYMMDD-*.md)
            if len(filename) > 9 and filename[8] == "-" and filename[:8].isdigit():
                # Remove date prefix and .md extension
                url_part = filename[9:-3]
                existing_urls.add(url_part)
            else:
                # Handle old format files (just remove .md)
                url_part = filename[:-3]
                existing_urls.add(url_part)

        print(f"Found {len(existing_urls)} existing URL slugs in {len(md_files)} markdown files")
        return existing_urls

    def fetch_urls_from_sitemap(self) -> list[str]:
        """Fetches URLs from sitemap.xml."""
        # Ensure base URL ends with /
        base_url = self.base_substack_url.rstrip("/") + "/"
        sitemap_url = f"{base_url}sitemap.xml"
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
        except requests.exceptions.ConnectionError as e:
            if "NameResolutionError" in str(e) or "Failed to resolve" in str(e):
                print(f"⚠️  Cannot reach domain: {self.base_substack_url}")
                print("   The domain might not exist or might have changed.")
            else:
                print(f"Failed to fetch sitemap: {e}")
            return []
        except Exception as e:
            print(f"Failed to fetch sitemap: {e}")
            return []

    def fetch_urls_from_feed(self) -> list[str]:
        """Fetches URLs from feed.xml."""
        print("Falling back to feed.xml. This will only contain up to the 22 most recent posts.")
        # Ensure base URL ends with /
        base_url = self.base_substack_url.rstrip("/") + "/"
        feed_url = f"{base_url}feed.xml"
        try:
            response = requests.get(feed_url, timeout=10)
            if not response.ok:
                print(f"Error fetching feed at {feed_url}: {response.status_code}")
                return []

            root = ET.fromstring(response.content)
            urls: list[str] = []
            for item in root.findall(".//item"):
                link = item.find("link")
                if link is not None and link.text:
                    urls.append(link.text)
            print(f"Found {len(urls)} URLs in feed")
            return urls
        except requests.exceptions.ConnectionError as e:
            if "NameResolutionError" in str(e) or "Failed to resolve" in str(e):
                print(f"⚠️  Skipping unreachable domain: {self.base_substack_url}")
            else:
                print(f"Failed to fetch feed: {e}")
            return []
        except Exception as e:
            print(f"Failed to fetch feed: {e}")
            return []

    @staticmethod
    def filter_urls(urls: list[str], keywords: list[str]) -> list[str]:
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
    def get_url_slug_from_url(url: str) -> str:
        """Extract URL slug from URL for consistent comparison.

        This is used to match URLs against existing files regardless of date prefixes.
        """
        return url.split("/")[-1]

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

            # Add small delay for rate limiting (3-10ms)
            delay = random.uniform(0.003, 0.01)
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

    async def extract_post_data(self, soup: BeautifulSoup, url: str) -> tuple[str, str, str, str, str]:
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
            # Very specific selector for the date div in byline-wrapper
            # Target the date-containing div that has classes like 'color-pub-secondary-text-*'
            "div.byline-wrapper div[class*='color-pub-secondary-text'] > div",
            # More specific: the innermost div that contains the date text
            "div.byline-wrapper div.pencraft.pc-display-flex.pc-gap-4 div[class*='color-pub-secondary-text']",
            # Even more specific: look for div with date-like classes
            "div[class*='date'][class*='pub-secondary']",
            # Time elements with datetime attribute
            "time[datetime]",  # Time elements with datetime
            "article time[datetime]",  # Time in article with datetime
            "div.post-header time[datetime]",  # Time in post header
            # Text-based selectors as fallback
            "span.post-meta-date",
            "div.post-date",
            "div.post-meta time",
            "span[class*='date']",
        ]

        for selector in date_selectors:
            date_elem = soup.select_one(selector)
            if date_elem:
                # Try to get datetime attribute first
                date_attr = date_elem.get("datetime")
                if date_attr and str(date_attr) != "None":
                    date = str(date_attr)
                    print(f"  Date found from datetime attribute: {date}")
                    break
                else:
                    # Check if this element has child divs that might contain the actual date
                    child_divs = date_elem.find_all("div")
                    if child_divs:
                        # Try to get the innermost div that contains text
                        for child in child_divs:
                            child_text = child.get_text(strip=True)
                            # Check if this looks like a date
                            if child_text and any(
                                month in child_text
                                for month in [
                                    "Jan",
                                    "Feb",
                                    "Mar",
                                    "Apr",
                                    "May",
                                    "Jun",
                                    "Jul",
                                    "Aug",
                                    "Sep",
                                    "Oct",
                                    "Nov",
                                    "Dec",
                                ]
                            ):
                                # Check if this div has no children with text (i.e., it's the innermost)
                                if not child.find_all(text=True, recursive=False)[1:]:  # [1:] to skip its own text
                                    date = child_text
                                    print(f"  Date extracted from innermost div: {date}")
                                    break

                    # If we didn't find it in child divs, try the original element
                    if date == "Date not found":
                        raw_text = date_elem.text.strip()
                        if raw_text and raw_text != "None":
                            # Clean up the text - remove author names and extra content
                            # Split by common separators and look for date patterns
                            parts = raw_text.split("∙")
                            for part in parts:
                                # Check if this part looks like a date
                                if any(
                                    month in part
                                    for month in [
                                        "Jan",
                                        "Feb",
                                        "Mar",
                                        "Apr",
                                        "May",
                                        "Jun",
                                        "Jul",
                                        "Aug",
                                        "Sep",
                                        "Oct",
                                        "Nov",
                                        "Dec",
                                    ]
                                ):
                                    date = part.strip()
                                    print(f"  Date extracted from text: {date}")
                                    break
                            else:
                                # If no month found, use the first part that contains numbers
                                for part in parts:
                                    if any(char.isdigit() for char in part):
                                        date = part.strip()
                                        print(f"  Date extracted from text: {date}")
                                        break

                    if date != "Date not found":
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
    async def get_url_soup(self, url: str) -> BeautifulSoup | None:
        """Abstract method to get BeautifulSoup from URL."""
        raise NotImplementedError

    async def scrape_single_post_with_date(self, url: str) -> dict[str, Any] | None:
        """Scrape a single post and save with date-based filename."""
        try:
            # Get page content
            soup = await self.get_url_soup(url)
            if soup is None:
                return None

            # Extract date for filename
            date_str = "1970-01-01"
            date_selectors = [
                # Very specific selector for the date div in byline-wrapper
                # Target the date-containing div that has classes like 'color-pub-secondary-text-*'
                "div.byline-wrapper div[class*='color-pub-secondary-text'] > div",
                # More specific: the innermost div that contains the date text
                "div.byline-wrapper div.pencraft.pc-display-flex.pc-gap-4 div[class*='color-pub-secondary-text']",
                # Even more specific: look for div with date-like classes
                "div[class*='date'][class*='pub-secondary']",
                # Time elements with datetime attribute
                "time[datetime]",  # Time elements with datetime
                "article time[datetime]",  # Time in article with datetime
                "div.post-header time[datetime]",  # Time in post header
                # Text-based selectors as fallback
                "span.post-meta-date",
                "div.post-date",
                "div.post-meta time",
                "span[class*='date']",
            ]

            extracted_date = None
            for selector in date_selectors:
                date_elem = soup.select_one(selector)
                if date_elem:
                    # Try to get datetime attribute first
                    date_attr = date_elem.get("datetime")
                    if date_attr and str(date_attr) != "None":
                        extracted_date = str(date_attr)
                        print(f"  Date found from datetime attribute: {extracted_date}")
                        break
                    else:
                        # Check if this element has child divs that might contain the actual date
                        child_divs = date_elem.find_all("div")
                        if child_divs:
                            # Try to get the innermost div that contains text
                            for child in child_divs:
                                child_text = child.get_text(strip=True)
                                # Check if this looks like a date
                                if child_text and any(
                                    month in child_text
                                    for month in [
                                        "Jan",
                                        "Feb",
                                        "Mar",
                                        "Apr",
                                        "May",
                                        "Jun",
                                        "Jul",
                                        "Aug",
                                        "Sep",
                                        "Oct",
                                        "Nov",
                                        "Dec",
                                    ]
                                ):
                                    # Check if this div has no children with text (i.e., it's the innermost)
                                    if not child.find_all(text=True, recursive=False)[1:]:  # [1:] to skip its own text
                                        extracted_date = child_text
                                        print(f"  Date extracted from innermost div: {extracted_date}")
                                        break

                        # If we didn't find it in child divs, try the original element
                        if not extracted_date:
                            raw_text = date_elem.text.strip()
                            if raw_text and raw_text != "None":
                                # Clean up the text - remove author names and extra content
                                # Split by common separators and look for date patterns
                                parts = raw_text.split("∙")
                                for part in parts:
                                    # Check if this part looks like a date
                                    if any(
                                        month in part
                                        for month in [
                                            "Jan",
                                            "Feb",
                                            "Mar",
                                            "Apr",
                                            "May",
                                            "Jun",
                                            "Jul",
                                            "Aug",
                                            "Sep",
                                            "Oct",
                                            "Nov",
                                            "Dec",
                                        ]
                                    ):
                                        extracted_date = part.strip()
                                        print(f"  Date extracted from text: {extracted_date}")
                                        break
                                else:
                                    # If no month found, use the first part that contains numbers
                                    for part in parts:
                                        if any(char.isdigit() for char in part):
                                            extracted_date = part.strip()
                                            print(f"  Date extracted from text: {extracted_date}")
                                            break

                        if extracted_date:
                            break

            # Parse the extracted date to create filename
            if extracted_date and extracted_date != "Date not found":
                try:
                    # Use dateparser for robust date parsing
                    parsed_date = dateparser.parse(extracted_date, settings={"PREFER_DAY_OF_MONTH": "first"})
                    if parsed_date:
                        date_str = parsed_date.strftime("%Y%m%d")
                    else:
                        print(f"  Warning: dateparser could not parse date '{extracted_date}'")
                        date_str = "19700101"
                except Exception as e:
                    print(f"  Warning: Error parsing date '{extracted_date}': {e}")
                    date_str = "19700101"

            # Use the parsed date string as the prefix
            date_prefix = date_str if date_str != "1970-01-01" else "19700101"

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

    async def save_essays_data_to_json(self, essays_data: list[dict[str, Any]]) -> None:
        """Saves essays data to JSON file."""
        data_dir = os.path.join(JSON_DATA_DIR)
        os.makedirs(data_dir, exist_ok=True)

        json_path = os.path.join(data_dir, f"{self.writer_name}.json")
        existing_data: list[dict[str, Any]] = []

        if os.path.exists(json_path):
            async with aiofiles.open(json_path, encoding="utf-8") as file:
                content = await file.read()
                loaded_data = json.loads(content)
                if isinstance(loaded_data, list):
                    existing_data = loaded_data  # type: ignore

        # Merge with existing data
        merged_data: list[dict[str, Any]] = existing_data + [data for data in essays_data if data not in existing_data]

        async with aiofiles.open(json_path, "w", encoding="utf-8") as file:
            await file.write(json.dumps(merged_data, ensure_ascii=False, indent=4))

    async def scrape_posts(self, num_posts_to_scrape: int = 0, continuous: bool = False) -> None:
        """Scrapes posts asynchronously and saves them with date-based filenames.

        Args:
            num_posts_to_scrape: Number of posts to scrape (0 for all)
            continuous: If True, only scrape new posts since last run
        """
        print(f"Starting async scraping of posts from {self.base_substack_url}")

        # Check if we have any URLs to process
        if not self.post_urls:
            print("No posts found to scrape. The domain might be unreachable or have no content.")
            return

        # Load previous state
        state = self.load_scraping_state() if continuous else {}
        scraped_urls = set(state.get("scraped_urls", []))
        scraped_slugs = set(state.get("scraped_slugs", []))  # New: track URL slugs for better matching
        latest_date = state.get("latest_post_date")

        if continuous and latest_date:
            print(f"Continuous mode: Only fetching posts newer than {latest_date}")

        # Get existing URLs from files
        existing_urls = self._get_existing_urls_from_files()

        # Filter URLs - improved logic for continuous fetching with date-prefixed filenames
        urls_to_process = self.post_urls[:num_posts_to_scrape] if num_posts_to_scrape else self.post_urls
        filtered_urls = []

        print(f"Filtering {len(urls_to_process)} URLs...")
        print(f"Continuous mode: {continuous}")
        print(f"Found {len(existing_urls)} existing URL slugs")
        print(f"Found {len(scraped_urls)} previously scraped URLs")

        for url in urls_to_process:
            # Use consistent URL slug extraction
            url_slug = self.get_url_slug_from_url(url)
            original_filename = self.get_filename_from_url(url, filetype=".md")

            # In continuous mode, check both scraped URLs and existing files
            if continuous:
                # Check if URL was already scraped (from state file)
                if url in scraped_urls:
                    print(f"  Skipping URL already in scraped_urls: {url}")
                    continue

                # Check if URL slug was already scraped (more reliable for date-prefixed files)
                if url_slug in scraped_slugs:
                    print(f"  Skipping URL slug already in scraped_slugs: {url_slug}")
                    continue

                # Check if file already exists (by URL slug)
                if url_slug in existing_urls:
                    print(f"  Skipping URL with existing file: {url_slug}")
                    continue

                print(f"  ✓ New URL for continuous mode: {url_slug}")

            # In non-continuous mode, check for existing files more thoroughly
            else:
                old_filepath = os.path.join(self.md_save_dir, original_filename)

                # Check for exact filename match (old format)
                if os.path.exists(old_filepath):
                    print(f"  File already exists (old format): {original_filename}")
                    continue

                # Check if URL slug exists in any date-prefixed file
                if url_slug in existing_urls:
                    print(f"  File already exists (date-prefixed): {url_slug}")
                    continue

                print(f"  ✓ New URL for regular mode: {url_slug}")

            filtered_urls.append(url)

        if not filtered_urls:
            print("No new posts to scrape.")
            return

        print(f"Found {len(filtered_urls)} posts to scrape")

        # Process URLs sequentially to avoid concurrent issues
        essays_data = []
        with tqdm(total=len(filtered_urls), desc="Scraping posts") as pbar:
            for url in filtered_urls:
                # Add random delay to be respectful
                delay = random.uniform(self.delay_range[0], self.delay_range[1])
                await asyncio.sleep(delay)

                result = await self.scrape_single_post_with_date(url)

                # In continuous mode, check if the scraped post is older than our latest date
                # This is a final check after scraping to ensure we don't save old posts
                if result and continuous and latest_date:
                    if result["date_str"] <= latest_date:
                        print(f"  Skipping older post after scraping (date: {result['date_str']} <= {latest_date})")
                        pbar.update(1)
                        continue

                if result:
                    essays_data.append(result)
                    scraped_urls.add(result["url"])
                    scraped_slugs.add(
                        self.get_url_slug_from_url(result["url"])
                    )  # Track URL slugs for better matching
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
                    "scraped_slugs": list(
                        scraped_slugs
                    ),  # Include URL slugs for better matching with date-prefixed files
                    "last_update": datetime.now().isoformat(),
                }
                await self.save_scraping_state(new_state)
                print(f"✓ Updated state with {len(scraped_slugs)} URL slugs for continuous mode")

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
        delay_range: tuple[int, int] = (1, 3),
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

        # Navigate to login page
        await self.tab.go_to("https://substack.com/sign-in")
        await asyncio.sleep(2)  # Wait for page load - keeping reasonable timeout

        # Perform the login
        await self.perform_login_on_page()

        # After login, wait and verify - reduced timeout to avoid blocking too long
        await asyncio.sleep(3)  # Reduced from 5s to 3s as per CLAUDE.md guidance

        # Check if we're logged in by looking for common logged-in elements
        current_url = await self.tab.current_url
        print(f"  Current URL after login: {current_url}")

        # Check for various indicators of successful login
        login_success = False

        # Method 1: Check if we're redirected away from sign-in page
        if "sign-in" not in current_url and "substack.com" in current_url:
            login_success = True
            print("  ✓ Redirected away from sign-in page")

        # Method 2: Check for user menu or dashboard elements
        if not login_success:
            user_menu = await self.tab.find(class_name="user-menu", timeout=5, raise_exc=False)
            dashboard_link = await self.tab.find(text="Dashboard", timeout=5, raise_exc=False)
            home_title = await self.tab.find(tag_name="h1", text="Home", timeout=5, raise_exc=False)

            if user_menu or dashboard_link or home_title:
                login_success = True
                print("  ✓ Found logged-in user elements")

        # Check for error messages
        error_container = await self.tab.find(id="error-container", timeout=5, raise_exc=False)
        if error_container:
            error_text = await error_container.text
            raise Exception(f"Login failed: {error_text}")

        if login_success:
            self.is_logged_in = True
            print("✓ Login successful!")
        else:
            # If we're still on sign-in page but no error, might be 2FA or other prompt
            if "sign-in" in current_url:
                print("  Warning: Still on sign-in page. Might require additional authentication.")
                print("  Proceeding anyway, but login might not be complete.")
            self.is_logged_in = True  # Optimistically assume success

    async def perform_login_on_page(self) -> None:
        """Perform the actual login actions on the sign-in page."""
        try:
            password_check = False

            if not password_check:
                # Password field not visible, look for "Sign in with password" element
                print("  Password field not visible, looking for 'Sign in with password' element...")

                # Try multiple selectors to find the "Sign in with password" element
                sign_in_password_element = None

                # Method 1: Find by class and text
                try:
                    sign_in_password_element = await self.tab.find(
                        tag_name="a",
                        class_name="login-option",
                        text="Sign in with password",
                        timeout=3,
                        raise_exc=False,
                    )
                except:
                    pass

                # Method 2: Find by CSS selector
                if not sign_in_password_element:
                    try:
                        elements = await self.tab.query_selector_all("a.login-option.substack-login__login-option")
                        for element in elements:
                            text_content = await element.text_content()
                            if "Sign in with password" in text_content:
                                sign_in_password_element = element
                                break
                    except:
                        pass

                # Method 3: Find by href and text content
                if not sign_in_password_element:
                    try:
                        elements = await self.tab.query_selector_all("a[href='javascript:void(0)']")
                        for element in elements:
                            text_content = await element.text_content()
                            if "Sign in with password" in text_content:
                                sign_in_password_element = element
                                break
                    except:
                        pass

                if sign_in_password_element:
                    print("  Found 'Sign in with password' element, clicking...")
                    await sign_in_password_element.click()
                    await asyncio.sleep(3)  # Wait for the form to update
                    print("  ✓ Clicked 'Sign in with password' element")

                    # Verify password field appeared after clicking
                    password_verify = await self.tab.find(tag_name="input", name="password", timeout=5, raise_exc=False)
                    if password_verify:
                        print("  ✓ Password field is now visible!")
                    else:
                        print("  ⚠️ Password field still not visible after clicking")
                        # Try to debug what's on the page
                        try:
                            form_action = await self.tab.query("form", timeout=2, raise_exc=False)
                            if form_action:
                                action_attr = await form_action.get_attribute("action")
                                print(f"  Debug: Form action is now: {action_attr}")
                        except:
                            pass
                else:
                    print("  ❌ No 'Sign in with password' element found with any method")
                    # Debug: Let's see what elements are actually available
                    try:
                        all_links = await self.tab.query_selector_all("a")
                        print(f"  Debug: Found {len(all_links)} <a> elements on page")
                        for i, link in enumerate(all_links[:5]):  # Show first 5
                            try:
                                text = await link.text_content()
                                href = await link.get_attribute("href")
                                classes = await link.get_attribute("class")
                                print(f"    Link {i + 1}: text='{text}' href='{href}' class='{classes}'")
                            except:
                                pass
                    except Exception as debug_e:
                        print(f"  Debug failed: {debug_e}")
            else:
                print("  ✓ Password field is already visible, proceeding with login...")

            # Find email input using sequential search for reliability
            print("  Finding email input...")

            # Try different email input detection methods sequentially
            email_input = None
            email_methods = [
                ("type_email", lambda: self.tab.find(attrs={"type": "email"}, timeout=3, raise_exc=False)),
                ("name_email", lambda: self.tab.find(attrs={"name": "email"}, timeout=3, raise_exc=False)),
                ("placeholder_email", lambda: self.tab.find(attrs={"placeholder": "Email"}, timeout=3, raise_exc=False)),
                ("css_email", lambda: self.tab.query("input[type='email']", timeout=3, raise_exc=False)),
                ("class_email", lambda: self.tab.query("input.input-ZGrgg4", timeout=3, raise_exc=False)),
                ("form_email", lambda: self.tab.query("form input[name='email']", timeout=3, raise_exc=False)),
            ]

            for method_name, method_func in email_methods:
                try:
                    email_input = await method_func()
                    if email_input:
                        print(f"  ✓ Found email input using {method_name}")
                        break
                except Exception as e:
                    print(f"  Failed {method_name}: {e}")
                    continue

            if email_input:
                # Use insert_text which clears the field and inserts new text
                await email_input.insert_text(SUBSTACK_EMAIL)
                await asyncio.sleep(0.5)
                print("  ✓ Email entered")
            else:
                raise Exception("Could not find email input field")

            # Find password input using sequential search for reliability
            print("  Finding password field...")

            # Try different password input detection methods sequentially
            password_input = None
            password_methods = [
                ("type_password", lambda: self.tab.find(attrs={"type": "password"}, timeout=3, raise_exc=False)),
                ("name_password", lambda: self.tab.find(attrs={"name": "password"}, timeout=3, raise_exc=False)),
                ("css_password", lambda: self.tab.query("input[type='password']", timeout=3, raise_exc=False)),
                ("placeholder_password", lambda: self.tab.find(attrs={"placeholder": "Password"}, timeout=3, raise_exc=False)),
                ("class_password", lambda: self.tab.query("input.input-ZGrgg4[type='password']", timeout=3, raise_exc=False)),
                ("form_password", lambda: self.tab.query("form input[name='password']", timeout=3, raise_exc=False)),
            ]

            for method_name, method_func in password_methods:
                try:
                    password_input = await method_func()
                    if password_input:
                        print(f"  ✓ Found password input using {method_name}")
                        break
                except Exception as e:
                    print(f"  Failed {method_name}: {e}")
                    continue

            if password_input:
                print("  Entering password...")
                # Use insert_text which clears the field and inserts new text
                await password_input.insert_text(SUBSTACK_PASSWORD)
                await asyncio.sleep(0.5)
                print("  ✓ Password entered")
            else:
                print("  Warning: Password field not found, trying to submit with email only...")

            # Find submit button using sequential search for reliability
            print("  Finding submit button...")

            # Try different submit button detection methods sequentially
            submit_button = None
            submit_methods = [
                ("submit_type", lambda: self.tab.find(tag_name="button", attrs={"type": "submit"}, timeout=3, raise_exc=False)),
                ("continue_text", lambda: self.tab.find(tag_name="button", text="Continue", timeout=3, raise_exc=False)),
                ("signin_text", lambda: self.tab.find(tag_name="button", text="Sign in", timeout=3, raise_exc=False)),
                ("form_submit", lambda: self.tab.query("form button[type='submit']", timeout=3, raise_exc=False)),
                ("pencraft_button", lambda: self.tab.query("button.buttonBase-GK1x3M", timeout=3, raise_exc=False)),
            ]

            for method_name, method_func in submit_methods:
                try:
                    submit_button = await method_func()
                    if submit_button:
                        print(f"  ✓ Found submit button using {method_name}")
                        break
                except Exception as e:
                    print(f"  Failed {method_name}: {e}")
                    continue

            if submit_button:
                print("  Clicking submit button...")
                await submit_button.click()
            else:
                # Try pressing Enter in the password field
                if password_input:
                    print("  Pressing Enter in password field...")
                    await password_input.press_keyboard_key(Key.ENTER)
                else:
                    raise Exception("Could not find submit button")

        except Exception as e:
            print(f"  Error during login: {e}")
            raise

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

        # Check for login indicators using sequential search for reliability
        print("  Checking login status...")

        # Try different login verification methods sequentially
        login_methods = [
            ("user_menu", lambda: self.tab.find(class_name="user-menu", timeout=2, raise_exc=False)),
            ("avatar_button", lambda: self.tab.query("button.avatarButton-lZBlGB", timeout=2, raise_exc=False)),
            ("dashboard_button", lambda: self.tab.find(text="Dashboard", timeout=2, raise_exc=False)),
            ("reader_nav", lambda: self.tab.find(class_name="reader-nav-root", timeout=2, raise_exc=False)),
            ("home_title", lambda: self.tab.find(tag_name="h1", text="Home", timeout=2, raise_exc=False)),
            ("subscriber_elem", lambda: self.tab.query("[data-testid='subscriber-only']", timeout=2, raise_exc=False)),
            ("signout_elem", lambda: self.tab.find(text="Sign out", timeout=2, raise_exc=False)),
        ]

        # Check each login indicator
        user_menu = None
        avatar_button = None
        dashboard_button = None
        reader_nav = None
        home_title = None
        subscriber_elem = None
        signout_elem = None

        for method_name, method_func in login_methods:
            try:
                result = await method_func()
                if result:
                    print(f"  ✓ Found login indicator: {method_name}")
                    if method_name == "user_menu":
                        user_menu = result
                    elif method_name == "avatar_button":
                        avatar_button = result
                    elif method_name == "dashboard_button":
                        dashboard_button = result
                    elif method_name == "reader_nav":
                        reader_nav = result
                    elif method_name == "home_title":
                        home_title = result
                    elif method_name == "subscriber_elem":
                        subscriber_elem = result
                    elif method_name == "signout_elem":
                        signout_elem = result
            except Exception as e:
                print(f"  Failed {method_name}: {e}")
                continue

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

    async def handle_sign_in_button(self) -> bool:
        """Check for and click the Sign in button if present. Returns True if handled.

        Following CLAUDE.md guidance: Don't block too long with page fully loaded detection mechanism.
        """
        try:
            # Look for the sign in button with reduced timeouts to avoid blocking too long
            # Try multiple selectors to find the sign in button
            sign_in_button = None

            # Method 1: Find button with specific text and native attribute
            buttons = await self.tab.find(
                tag_name="button", find_all=True, timeout=5, raise_exc=False
            )  # Reduced from 10s to 5s
            if buttons:
                for button in buttons:
                    try:
                        text = await button.text
                        if text and "Sign in" in text:
                            # Check if it has native attribute
                            native_attr = await button.get_attribute("native")
                            if native_attr == "true":
                                sign_in_button = button
                                break
                    except Exception:
                        # Skip this button if we can't get its attributes
                        continue

            # Method 2: Try CSS selector if first method fails
            if not sign_in_button:
                sign_in_button = await self.tab.query(
                    "button[native='true']:has-text('Sign in')",
                    timeout=5,
                    raise_exc=False,  # Reduced from 10s to 5s
                )

            # Method 3: Look for button with data-href attribute containing sign-in
            if not sign_in_button:
                buttons = await self.tab.find(
                    tag_name="button", find_all=True, timeout=5, raise_exc=False
                )  # Reduced from 10s to 5s
                if buttons:
                    for button in buttons:
                        try:
                            data_href = await button.get_attribute("data-href")
                            if data_href and "sign-in" in str(data_href):
                                sign_in_button = button
                                break
                        except Exception:
                            # Skip this button if we can't get its attributes
                            continue

            if sign_in_button:
                print("  Found 'Sign in' button, clicking...")
                await sign_in_button.click()
                await asyncio.sleep(2)  # Reduced from 3s to 2s to avoid blocking too long

                # Now perform login
                await self.perform_login_on_page()
                return True

        except Exception as e:
            print(f"  Error handling sign in button: {e}")

        return False

    async def check_login_status_via_analytics(self) -> bool:
        """Check if user is logged in by examining the analytics config."""
        try:
            # Get page source and check for analytics config
            page_source = await self.tab.page_source
            if page_source and 'is_subscribed":true' in page_source:
                return True

        except Exception as e:
            print(f"  Error checking analytics config: {e}")

        return False

    async def check_paywall_via_analytics(self) -> bool:
        """Check if content is paywalled by examining the analytics config."""
        try:
            # Get page source and check for analytics config
            page_source = await self.tab.page_source
            if page_source and 'is_subscribed":false' in page_source:
                return True

        except Exception as e:
            print(f"  Error checking analytics config for paywall: {e}")

        return False

    async def check_paywall_after_login(self) -> bool:
        """Check if paywall is still present after login using multiple methods."""
        try:
            # Check for paywall using sequential search for reliability
            paywall_methods = [
                ("testid_paywall", lambda: self.tab.find(attrs={"data-testid": "paywall"}, timeout=2, raise_exc=False)),
                ("class_paywall", lambda: self.tab.find(class_name="paywall", timeout=2, raise_exc=False)),
                ("analytics_paywall", lambda: self.check_paywall_via_analytics()),
            ]

            for method_name, method_func in paywall_methods:
                try:
                    result = await method_func()
                    if result:
                        print(f"  ⚠️ Paywall still present after login (detected via: {method_name})")
                        return True
                except Exception as e:
                    print(f"  Failed {method_name}: {e}")
                    continue

            return False

        except Exception as e:
            print(f"  Error checking paywall after login: {e}")
            return True  # Assume paywall still present on error

    async def handle_paywall(self, url: str) -> bool:
        """
        Handle paywall by attempting to log in.
        Returns True if paywall was successfully bypassed, False otherwise.
        If paywall cannot be removed by login, warns user and returns False.
        """
        print(f"🔒 Checking paywall status for: {url}")

        try:
            # First, check if user is already logged in by examining analytics config
            print("  Checking login status via analytics config...")
            is_logged_in = await self.check_login_status_via_analytics()

            if is_logged_in:
                print("  ✅ User is already logged in")
                return True

            # Check for paywall using sequential detection for reliability
            print("  Detecting paywall...")

            # Try different paywall detection methods sequentially
            paywall_methods = [
                ("testid_paywall", lambda: self.tab.find(attrs={"data-testid": "paywall"}, timeout=2, raise_exc=False)),
                ("title_paywall", lambda: self.tab.find(tag_name="h2", class_name="paywall-title", timeout=2, raise_exc=False)),
                ("class_paywall", lambda: self.tab.find(class_name="paywall", timeout=2, raise_exc=False)),
                ("analytics_paywall", lambda: self.check_paywall_via_analytics()),
            ]

            paywall_detected = False
            for method_name, method_func in paywall_methods:
                try:
                    result = await method_func()
                    if result:
                        paywall_detected = True
                        print(f"  ✓ Paywall detected via: {method_name}")
                        break
                except Exception as e:
                    print(f"  Failed {method_name}: {e}")
                    continue

            if not paywall_detected:
                print("  ✅ No paywall detected - content is accessible")
                return True

            # If we have credentials, try to log in
            if SUBSTACK_EMAIL and SUBSTACK_PASSWORD:
                print("  🔑 Attempting to log in to bypass paywall...")

                # First try to click the "Sign in" button on the current page (following CLAUDE.md guidance)
                print("  Trying to click 'Sign in' button on current page...")
                sign_in_clicked = await self.handle_sign_in_button()

                login_success = False
                if sign_in_clicked:
                    print("  ✅ Clicked 'Sign in' button, checking if login was successful...")
                    await asyncio.sleep(3)  # Wait for login to complete

                    # Check if we're now logged in
                    login_success = await self.check_login_status_via_analytics()
                    if login_success:
                        print("  ✅ Login successful via 'Sign in' button!")
                    else:
                        print("  ⚠️ 'Sign in' button clicked but login status unclear, checking paywall...")
                        # We'll check paywall status below regardless
                        login_success = True  # Assume success and let paywall check determine outcome

                # # If clicking the sign in button didn't work, fall back to navigating to login page
                # if not sign_in_clicked:
                #     print("  No 'Sign in' button found on page, navigating to login page...")

                #     input("  Please log in manually and press Enter to continue...")

                if login_success:
                    print("  ✅ Login successful, checking if paywall is bypassed...")
                    await asyncio.sleep(3)  # Wait for page to update after login

                    # Check if paywall is still present after login using multiple methods
                    paywall_still_present = await self.check_paywall_after_login()

                    if not paywall_still_present:
                        print("  ✅ Paywall successfully bypassed!")
                        return True
                    else:
                        print("  ❌ Paywall still present after login - article requires paid subscription")
                        print(f"  ⚠️  WARNING: Cannot access paywalled content: {url}")
                        print("  ⚠️  This article will be skipped and not saved.")
                        return False
                else:
                    print("  ❌ Login failed")
                    print(f"  ⚠️  WARNING: Cannot access paywalled content due to login failure: {url}")
                    print("  ⚠️  This article will be skipped and not saved.")
                    return False
            else:
                print("  ❌ No credentials provided for login")
                print(f"  ⚠️  WARNING: Cannot access paywalled content (no credentials): {url}")
                print("  ⚠️  This article will be skipped and not saved.")
                return False

        except Exception as e:
            print(f"  ❌ Error handling paywall: {e}")
            print(f"  ⚠️  WARNING: Cannot access content due to error: {url}")
            print("  ⚠️  This article will be skipped and not saved.")
            return False

    async def check_browser_health(self) -> bool:
        """Check if browser connection is still alive."""
        if self.browser is None or self.tab is None:
            return False

        try:
            # Try a simple operation to test connection
            await self.tab.current_url
            return True
        except Exception:
            return False

    async def ensure_browser_initialized(self) -> None:
        """Ensure browser is initialized and healthy, reconnect if needed."""
        if not await self.check_browser_health():
            print("  Browser connection lost, reinitializing...")
            # Clean up old browser if exists
            if self.browser:
                try:
                    await self.browser.stop()
                except Exception:
                    pass

            # Reinitialize
            await self.initialize_browser()

            # Re-login if we were logged in before
            if self.is_logged_in and (USE_PREMIUM or (SUBSTACK_EMAIL and SUBSTACK_PASSWORD) or self.manual_login):
                print("  Re-establishing login session...")
                if self.manual_login:
                    print("  Manual login was used previously. You may need to login again if prompted.")
                    self.is_logged_in = True  # Assume still logged in for manual mode
                else:
                    await self.login()

    async def get_url_soup(self, url: str) -> BeautifulSoup | None:
        """Get BeautifulSoup from URL using Pydoll."""
        # Ensure browser is healthy before proceeding
        await self.ensure_browser_initialized()

        if self.tab is None:
            raise RuntimeError("Browser not initialized. Call initialize_browser() first.")

        try:
            # Enable Cloudflare bypass if needed
            async with self.tab.expect_and_bypass_cloudflare_captcha():
                await self.tab.go_to(url)

            # Wait for initial page load - reduced timeout to avoid blocking too long
            print("  Waiting for page to load (reduced timeout to avoid blocking)...")
            await asyncio.sleep(3)  # Reduced from 5s to 3s as per CLAUDE.md guidance

            # Check for sign in button on the page (for non-logged in users)
            if not self.is_logged_in and (SUBSTACK_EMAIL and SUBSTACK_PASSWORD):
                # First check if we need to sign in on this page
                sign_in_handled = await self.handle_sign_in_button()

                # If we just logged in, we might need to navigate back to the article
                if sign_in_handled:
                    await asyncio.sleep(2)  # Reduced from 3s to avoid blocking too long
                    # Check current URL - if we're not on the article page, go back
                    current_url = await self.tab.current_url
                    if url not in current_url:
                        await self.tab.go_to(url)
                        await asyncio.sleep(3)  # Reduced from 5s to 3s

            # Check for paywall and attempt to bypass it
            paywall_bypassed = await self.handle_paywall(url)
            if not paywall_bypassed:
                # Paywall could not be bypassed - return None to skip this article
                print(f"  ❌ Skipping paywalled article: {url}")
                return None

            # Wait for content to load with reduced timeouts to avoid blocking too long
            content_loaded = False
            print("  Looking for content elements (with reduced timeouts)...")

            # Try to find the body markup which contains the actual content
            body_markup = await self.tab.query(
                "div.body.markup", timeout=15, raise_exc=False
            )  # Reduced from 30s to 15s
            if body_markup:
                content_loaded = True
                print("  ✓ Found div.body.markup")
                await asyncio.sleep(1)  # Reduced wait time to avoid blocking too long
            else:
                # Try other selectors sequentially for reliability
                print("  Trying multiple content selectors...")

                # Try different content selectors sequentially
                selectors = ["available-content", "article", "post-content"]
                for selector in selectors:
                    try:
                        content_elem = await self.tab.find(class_name=selector, timeout=3, raise_exc=False)
                        if content_elem:
                            content_loaded = True
                            print(f"  ✓ Found {selector}")
                            break
                    except Exception as e:
                        print(f"  Failed {selector}: {e}")
                        continue

            # Additional wait for dynamic content if needed - with sequential fallback search
            if not content_loaded:
                print("  Trying fallback content selectors...")

                # Try fallback selectors sequentially
                fallback_selectors = [
                    ("article", lambda: self.tab.find(tag_name="article", timeout=3, raise_exc=False)),
                    ("main", lambda: self.tab.find(tag_name="main", timeout=3, raise_exc=False)),
                    ("content", lambda: self.tab.find(class_name="content", timeout=3, raise_exc=False)),
                    ("post", lambda: self.tab.find(class_name="post", timeout=3, raise_exc=False)),
                ]

                for selector_name, selector_func in fallback_selectors:
                    try:
                        element = await selector_func()
                        if element:
                            content_loaded = True
                            print(f"  ✓ Found {selector_name} (fallback)")
                            await asyncio.sleep(1)  # Brief wait for content to stabilize
                            break
                    except Exception as e:
                        print(f"  Failed {selector_name}: {e}")
                        continue

                if not content_loaded:
                    print("  ⚠️ Warning: Could not find expected content selectors")
                    await asyncio.sleep(2)  # Reduced wait time

            # Final check for paywall (after potential login) using sequential search
            print("  Checking for paywall...")

            # Try paywall detection methods sequentially
            final_paywall = None
            paywall_final_methods = [
                ("class_paywall", lambda: self.tab.find(class_name="paywall", timeout=2, raise_exc=False)),
                ("testid_paywall", lambda: self.tab.find(attrs={"data-testid": "paywall"}, timeout=2, raise_exc=False)),
            ]

            for method_name, method_func in paywall_final_methods:
                try:
                    result = await method_func()
                    if result:
                        final_paywall = result
                        print(f"  ✓ Paywall detected via {method_name}")
                        break
                except Exception as e:
                    print(f"  Failed {method_name}: {e}")
                    continue

            if final_paywall and not self.is_logged_in:
                print(f"  Skipping premium article (login required): {url}")
                return None

            # Get page source
            page_source = await self.tab.page_source
            return BeautifulSoup(page_source, "html.parser")

        except Exception as e:
            error_msg = str(e)
            if "Connect call failed" in error_msg and "9263" in error_msg:
                # Browser connection lost
                print(f"  Browser connection lost while fetching {url}")
                print("  Attempting to reconnect...")
                await self.ensure_browser_initialized()
                # Try once more
                try:
                    await self.tab.go_to(url)
                    await asyncio.sleep(3)
                    page_source = await self.tab.page_source
                    return BeautifulSoup(page_source, "html.parser")
                except Exception as retry_e:
                    print(f"  Retry failed: {retry_e}")
                    return None
            else:
                print(f"Error fetching page {url}: {e}")
                return None

    async def scrape_posts(
        self, num_posts_to_scrape: int = 0, continuous: bool = False, skip_browser_init: bool = False
    ) -> None:
        """Override to handle browser lifecycle."""
        try:
            if not skip_browser_init:
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
            # Don't stop the browser if it's shared
            if self.browser and not skip_browser_init:
                await self.browser.stop()



    async def scrape_single_post(self, url: str) -> dict[str, Any] | None:
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



  # Custom delay between requests (1-5 seconds)
  pydoll-substack2md https://example.substack.com --delay-min 1 --delay-max 5

  # Continuous mode - only fetch new posts since last run
  pydoll-substack2md https://example.substack.com --continuous

  # Scrape multiple Substacks
  pydoll-substack2md https://example1.substack.com https://example2.substack.com

  # Scrape from a file containing URLs
  pydoll-substack2md --urls-file substacks.txt

  # Continuous mode with interval (re-run every 30 minutes)
  pydoll-substack2md --urls-file substacks.txt --continuous --interval 30

  # Pipe URLs from another command
  cat substacks.txt | pydoll-substack2md --continuous
""",
    )

    parser.add_argument(
        "urls",
        nargs="*",
        type=str,
        help="One or more Substack URLs to scrape (can also be provided via stdin)",
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
    parser.add_argument(
        "--interval",
        type=int,
        default=0,
        help="Re-run interval in minutes for continuous mode (0 = run once)",
    )
    parser.add_argument(
        "--urls-file",
        type=str,
        help="File containing Substack URLs (one per line)",
    )

    return parser.parse_args()


async def scrape_single_url(
    url: str,
    args,
    use_login: bool,
    use_manual_login: bool,
    shared_browser=None,
    shared_tab=None,
    shared_login_status=False,
) -> tuple:
    """Scrape a single Substack URL, optionally using a shared browser session.

    Returns: (browser, tab, is_logged_in) tuple for reuse
    """
    print(f"\n{'=' * 60}")
    print(f"Scraping: {url}")
    print(f"Login enabled: {use_login}")
    print(f"Manual login mode: {use_manual_login}")
    print(f"Headless mode: {args.headless or HEADLESS}")
    print(f"Delay range: {args.delay_min}-{args.delay_max} seconds")
    print(f"{'=' * 60}\n")

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

    # Use shared browser if provided
    if shared_browser and shared_tab:
        print("🔄 Reusing existing browser session")
        scraper.browser = shared_browser
        scraper.tab = shared_tab
        scraper.is_logged_in = shared_login_status

        # Check browser health
        if not await scraper.check_browser_health():
            print("⚠️  Shared browser session is dead, creating new session...")
            shared_browser = None
            shared_tab = None
            scraper.browser = None
            scraper.tab = None
            scraper.is_logged_in = False

    await scraper.scrape_posts(
        num_posts_to_scrape=args.number or NUM_POSTS_TO_SCRAPE,
        continuous=args.continuous,
        skip_browser_init=bool(shared_browser),
    )

    # Return browser, tab, and login status for reuse
    return scraper.browser, scraper.tab, scraper.is_logged_in


def get_urls_from_file(filepath: str) -> list[str]:
    """Read URLs from a file (one per line)."""
    urls = []
    try:
        with open(filepath) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#"):
                    urls.append(line)
    except FileNotFoundError:
        print(f"Error: URLs file '{filepath}' not found")
        sys.exit(1)
    return urls


def get_urls_from_stdin() -> list[str]:
    """Read URLs from stdin if available."""
    urls = []
    if not sys.stdin.isatty():
        for line in sys.stdin:
            line = line.strip()
            if line and not line.startswith("#"):
                urls.append(line)
    return urls


async def main():
    """Main entry point."""
    args = parse_args()

    # Collect URLs from various sources
    urls = []

    # From command line arguments
    if args.urls:
        urls.extend(args.urls)

    # From file
    if args.urls_file:
        urls.extend(get_urls_from_file(args.urls_file))

    # From stdin
    stdin_urls = get_urls_from_stdin()
    if stdin_urls:
        urls.extend(stdin_urls)

    # From environment variable as fallback
    if not urls and BASE_SUBSTACK_URL:
        urls.append(BASE_SUBSTACK_URL)

    # Remove duplicates while preserving order
    seen = set()
    unique_urls = []
    for url in urls:
        if url not in seen:
            seen.add(url)
            unique_urls.append(url)

    if not unique_urls:
        print("Error: No Substack URLs provided. Use -h for help.")
        print("\nProvide URLs via:")
        print("  - Command line: pydoll-substack2md URL1 URL2 ...")
        print("  - File: pydoll-substack2md --urls-file urls.txt")
        print("  - Stdin: echo 'URL' | pydoll-substack2md")
        print("  - Environment: Set BASE_SUBSTACK_URL in .env")
        sys.exit(1)

    # Determine if we should use premium scraping
    use_login = bool(args.login or USE_PREMIUM or (SUBSTACK_EMAIL and SUBSTACK_PASSWORD))
    use_manual_login = bool(args.manual_login)

    # Validate manual login with headless mode
    if use_manual_login and (args.headless or HEADLESS):
        print("Error: Manual login mode cannot be used with headless mode")
        print("Either remove --manual-login or remove --headless")
        sys.exit(1)

    # Validate delay parameters
    if args.delay_min > args.delay_max:
        print("Error: --delay-min cannot be greater than --delay-max")
        sys.exit(1)

    print(f"\n🎯 Starting scraper for {len(unique_urls)} Substack(s)")
    if args.continuous and args.interval > 0:
        print(f"📅 Continuous mode: Will re-run every {args.interval} minutes")

    # Main scraping loop
    shared_browser = None
    shared_tab = None
    shared_login_status = False

    try:
        while True:
            start_time = time.time()

            # Scrape all URLs
            for i, url in enumerate(unique_urls, 1):
                print(f"\n📍 Processing {i}/{len(unique_urls)}: {url}")
                try:
                    # Reuse browser session across URLs
                    shared_browser, shared_tab, shared_login_status = await scrape_single_url(
                        url, args, use_login, use_manual_login, shared_browser, shared_tab, shared_login_status
                    )
                    print(f"✅ Completed: {url}")
                except Exception as e:
                    print(f"❌ Error scraping {url}: {e}")
                    if args.continuous:
                        print("   Continuing with next URL...")
                        continue
                    else:
                        raise

            # Check if we should continue
            if not args.continuous or args.interval <= 0:
                break

            # Calculate time until next run
            elapsed = time.time() - start_time
            wait_time = max(0, args.interval * 60 - elapsed)

            if wait_time > 0:
                print(f"\n⏰ Waiting {wait_time / 60:.1f} minutes until next run...")
                print("   Press Ctrl+C to stop")
                try:
                    await asyncio.sleep(wait_time)
                except KeyboardInterrupt:
                    print("\n👋 Stopping continuous mode")
                    break

        print("\n✨ All scraping completed!")

    finally:
        # Clean up the shared browser session when done
        if shared_browser:
            print("\n🔧 Closing browser session...")
            await shared_browser.stop()


def run():
    """Entry point for command line execution."""
    asyncio.run(main())


if __name__ == "__main__":
    run()
