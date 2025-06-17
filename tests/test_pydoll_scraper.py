import os
from unittest.mock import AsyncMock, patch

import pytest
from bs4 import BeautifulSoup

from pydoll_substack2md.pydoll_scraper import (
    BaseSubstackScraper,
    PydollSubstackScraper,
    extract_main_part,
)


class TestExtractMainPart:
    """Test the extract_main_part function."""

    def test_extract_main_part_with_www(self):
        url = "https://www.example.substack.com"
        assert extract_main_part(url) == "example"

    def test_extract_main_part_without_www(self):
        url = "https://example.substack.com"
        assert extract_main_part(url) == "example"

    def test_extract_main_part_complex_subdomain(self):
        url = "https://complex.example.substack.com"
        assert extract_main_part(url) == "complex"


class TestBaseSubstackScraper:
    """Test the BaseSubstackScraper abstract base class."""

    @pytest.fixture
    def scraper(self, tmp_path):
        """Create a concrete implementation for testing."""

        class TestScraper(BaseSubstackScraper):
            async def get_url_soup(self, url):
                return BeautifulSoup("<html></html>", "html.parser")

        return TestScraper("https://test.substack.com", str(tmp_path / "md"), str(tmp_path / "html"))

    def test_initialization(self, scraper):
        assert scraper.base_substack_url == "https://test.substack.com/"
        assert scraper.writer_name == "test"
        assert "about" in scraper.keywords
        assert "archive" in scraper.keywords
        assert "podcast" in scraper.keywords

    def test_filter_urls(self):
        urls = [
            "https://test.substack.com/p/post1",
            "https://test.substack.com/p/post2",
            "https://test.substack.com/about",
            "https://test.substack.com/archive",
            "https://test.substack.com/podcast/episode1",
        ]
        keywords = ["about", "archive", "podcast"]

        filtered = BaseSubstackScraper.filter_urls(urls, keywords)
        assert len(filtered) == 2
        assert "https://test.substack.com/p/post1" in filtered
        assert "https://test.substack.com/p/post2" in filtered

    def test_html_to_md(self):
        html = "<h1>Title</h1><p>This is a <strong>test</strong> paragraph.</p>"
        md = BaseSubstackScraper.html_to_md(html)

        assert "# Title" in md
        assert "**test**" in md

    def test_get_filename_from_url(self):
        url = "https://test.substack.com/p/my-post-title"

        assert BaseSubstackScraper.get_filename_from_url(url) == "my-post-title.md"
        assert BaseSubstackScraper.get_filename_from_url(url, ".html") == "my-post-title.html"

    def test_combine_metadata_and_content(self):
        result = BaseSubstackScraper.combine_metadata_and_content(
            "Test Title", "Test Subtitle", "2024-01-01", "42", "Test content"
        )

        assert "# Test Title" in result
        assert "## Test Subtitle" in result
        assert "**2024-01-01**" in result
        assert "**Likes:** 42" in result
        assert "Test content" in result


class TestPydollSubstackScraper:
    """Test the PydollSubstackScraper implementation."""

    @pytest.fixture
    def scraper(self, tmp_path):
        return PydollSubstackScraper(
            "https://test.substack.com", str(tmp_path / "md"), str(tmp_path / "html"), headless=True
        )

    @pytest.mark.asyncio
    async def test_initialize_browser(self, scraper):
        """Test browser initialization."""
        with patch("pydoll_substack2md.pydoll_scraper.Chrome") as MockChrome:
            mock_browser = AsyncMock()
            mock_tab = AsyncMock()
            MockChrome.return_value = mock_browser
            mock_browser.start.return_value = mock_tab

            await scraper.initialize_browser()

            assert scraper.browser == mock_browser
            assert scraper.tab == mock_tab
            mock_tab.enable_network_events.assert_called_once()

    # Resource blocking test removed - feature temporarily disabled
    # @pytest.mark.asyncio
    # async def test_setup_resource_blocking(self, scraper):
    #     \"\"\"Test resource blocking setup.\"\"\"
    #     pass

    @pytest.mark.asyncio
    async def test_login_without_credentials(self, scraper):
        """Test login when no credentials are provided."""
        with patch.dict(os.environ, {"SUBSTACK_EMAIL": "", "SUBSTACK_PASSWORD": ""}):
            # Should return early without attempting login
            await scraper.login()
            assert not scraper.is_logged_in

    @pytest.mark.asyncio
    async def test_get_url_soup_success(self, scraper):
        """Test successful URL scraping."""
        scraper.tab = AsyncMock()
        scraper.tab.page_source = "<html><body><h1>Test</h1></body></html>"
        scraper.tab.find.return_value = None  # No paywall

        soup = await scraper.get_url_soup("https://test.substack.com/p/test")

        assert soup is not None
        assert soup.find("h1").text == "Test"

    @pytest.mark.asyncio
    async def test_get_url_soup_paywall(self, scraper):
        """Test URL scraping when hitting a paywall."""
        scraper.tab = AsyncMock()
        mock_paywall = AsyncMock()
        scraper.tab.find.return_value = mock_paywall
        scraper.is_logged_in = False

        soup = await scraper.get_url_soup("https://test.substack.com/p/premium")

        assert soup is None

    @pytest.mark.asyncio
    async def test_scrape_single_post(self, scraper, tmp_path):
        """Test scraping a single post."""
        scraper.browser = AsyncMock()
        mock_tab = AsyncMock()
        scraper.browser.new_tab.return_value = mock_tab

        # Mock page source
        mock_tab.page_source = """
        <html>
            <body>
                <h1 class="post-title">Test Post</h1>
                <div class="available-content">
                    <p>Test content</p>
                </div>
            </body>
        </html>
        """
        mock_tab.find.return_value = None  # No paywall

        result = await scraper.scrape_single_post("https://test.substack.com/p/test-post")

        assert result is not None
        assert result["title"] == "Test Post"
        assert "Test content" in result["file_link"]
        mock_tab.close.assert_called_once()


@pytest.mark.asyncio
async def test_html_to_markdown_conversion():
    """Test the html-to-markdown conversion."""
    html = """
    <article>
        <h1>Welcome to Substack</h1>
        <p>This is a <strong>sample</strong> post with a <a href="https://example.com">link</a>.</p>
        <ul>
            <li>Item 1</li>
            <li>Item 2</li>
        </ul>
        <pre><code class="language-python">
def hello():
    print("Hello, World!")
        </code></pre>
    </article>
    """

    markdown = BaseSubstackScraper.html_to_md(html)

    assert "# Welcome to Substack" in markdown
    assert "**sample**" in markdown
    assert "[link](https://example.com)" in markdown
    assert "* Item 1" in markdown
    assert "* Item 2" in markdown
    assert "```python" in markdown or "def hello():" in markdown


@pytest.mark.asyncio
async def test_concurrent_scraping():
    """Test concurrent post scraping."""
    scraper = PydollSubstackScraper("https://test.substack.com", "/tmp/md", "/tmp/html", headless=True)

    # Mock the scraper methods using patch
    with patch.object(scraper, "initialize_browser", new_callable=AsyncMock):
        with patch.object(scraper, "scrape_single_post", new_callable=AsyncMock) as mock_scrape:
            mock_scrape.return_value = {"title": "Test"}
            with patch.object(scraper, "save_essays_data_to_json", new_callable=AsyncMock):
                scraper.browser = AsyncMock()
                scraper.post_urls = ["url1", "url2", "url3"]

                with patch("pydoll_substack2md.pydoll_scraper.generate_html_file", new_callable=AsyncMock):
                    await scraper.scrape_posts_concurrently(max_concurrent=2)

                # Should have called scrape_single_post for each URL
                assert mock_scrape.call_count == 3
                scraper.browser.stop.assert_called_once()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
