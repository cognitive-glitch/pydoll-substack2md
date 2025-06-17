"""
pydoll-substack2md - A Python scraper that downloads Substack posts and converts them to Markdown.

This package provides tools to scrape Substack newsletters and convert them to Markdown format,
with support for premium content (requires login credentials).

Built with Pydoll for browser automation and html-to-markdown for content conversion.
"""

from .pydoll_scraper import (
    BaseSubstackScraper,
    PydollSubstackScraper,
    main,
    run,
)

__version__ = "0.1.0"
__all__ = [
    "BaseSubstackScraper",
    "PydollSubstackScraper",
    "main",
    "run",
]
