#!/usr/bin/env python3
"""Test script to verify login functionality for pydoll-substack2md."""

import asyncio
import os

from dotenv import load_dotenv

from pydoll_substack2md.pydoll_scraper import PydollSubstackScraper

# Load environment variables
load_dotenv()

SUBSTACK_EMAIL = os.getenv("SUBSTACK_EMAIL", "")
SUBSTACK_PASSWORD = os.getenv("SUBSTACK_PASSWORD", "")


async def test_login():
    """Test the login functionality."""
    print("Testing pydoll-substack2md login functionality")
    print("=" * 60)

    if not SUBSTACK_EMAIL or not SUBSTACK_PASSWORD:
        print("❌ Error: SUBSTACK_EMAIL and SUBSTACK_PASSWORD must be set in .env file")
        return

    # Test URL with premium content
    test_url = "https://www.research.hangukquant.com/"

    print(f"Email: {SUBSTACK_EMAIL}")
    print(f"Test URL: {test_url}")
    print("=" * 60)

    scraper = PydollSubstackScraper(
        base_substack_url=test_url,
        md_save_dir="test_output",
        html_save_dir="test_html",
        headless=False,  # Run with GUI for debugging
        manual_login=False,
    )

    try:
        # Initialize browser
        print("\n1. Initializing browser...")
        await scraper.initialize_browser()

        # Test login
        print("\n2. Testing login...")
        await scraper.login()

        print(f"\n3. Login status: {'✅ Logged in' if scraper.is_logged_in else '❌ Not logged in'}")

        # Test navigating to a post with sign-in button
        print("\n4. Testing navigation to a post...")
        test_post_url = "https://www.research.hangukquant.com/p/relative-volume-curve-and-confidence"

        soup = await scraper.get_url_soup(test_post_url)

        if soup:
            print("✅ Successfully fetched page content")

            # Check for paywall
            paywall = soup.find("div", class_="paywall")
            if paywall:
                print("❌ Paywall still detected after login")
            else:
                print("✅ No paywall detected - content accessible")

            # Check for content
            content = soup.find("div", class_="body markup")
            if content:
                print("✅ Found article content")
                print(f"   Content length: {len(str(content))} characters")
            else:
                print("❌ Could not find article content")
        else:
            print("❌ Failed to fetch page content")

    except Exception as e:
        print(f"\n❌ Error during test: {e}")
        import traceback

        traceback.print_exc()

    finally:
        # Clean up
        print("\n5. Cleaning up...")
        if scraper.browser:
            await scraper.browser.stop()
        print("✅ Test complete")


if __name__ == "__main__":
    asyncio.run(test_login())
