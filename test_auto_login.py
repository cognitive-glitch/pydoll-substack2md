#!/usr/bin/env python3
"""Test auto-login functionality for Substack."""

import asyncio
import os

from dotenv import load_dotenv

from pydoll_substack2md.pydoll_scraper import PydollSubstackScraper

# Load environment variables
load_dotenv()


async def test_auto_login():
    """Test the auto-login functionality."""

    # Check if credentials are available
    email = os.getenv("SUBSTACK_EMAIL")
    password = os.getenv("SUBSTACK_PASSWORD")

    if not email or not password:
        print("❌ Error: SUBSTACK_EMAIL and SUBSTACK_PASSWORD must be set in .env file")
        return

    print(f"Testing auto-login with email: {email}")
    print("=" * 60)

    # Create a scraper instance
    scraper = PydollSubstackScraper(
        base_substack_url="https://example.substack.com",  # Dummy URL
        md_save_dir="test_output",
        html_save_dir="test_output_html",
        headless=False,  # Show browser for debugging
        delay_range=(1, 3),
        manual_login=False,
    )

    try:
        # Initialize browser
        print("\n1. Initializing browser...")
        await scraper.initialize_browser()
        print("✓ Browser initialized")

        # Perform login
        print("\n2. Performing auto-login...")
        await scraper.login()

        # Verify login status
        print(f"\n3. Login status: {'✓ Logged in' if scraper.is_logged_in else '❌ Not logged in'}")

        if scraper.is_logged_in:
            print("\n4. Testing navigation to a Substack publication...")
            # Try navigating to a real Substack to verify login works
            await scraper.tab.go_to("https://astralcodexten.substack.com")
            await asyncio.sleep(3)

            # Check if we can see subscriber-only elements
            subscriber_elem = await scraper.tab.query("[data-testid='subscriber-only']", timeout=5, raise_exc=False)
            if subscriber_elem:
                print("✓ Can see subscriber-only elements - login is working!")
            else:
                print("✓ Navigation successful (no subscriber-only content on this page)")

        # Keep browser open for manual inspection
        print("\n✅ Test completed! Press Enter to close the browser...")
        input()

    except Exception as e:
        print(f"\n❌ Error during test: {e}")
        import traceback

        traceback.print_exc()

    finally:
        # Clean up
        if scraper.browser:
            await scraper.browser.stop()
            print("Browser closed.")


if __name__ == "__main__":
    asyncio.run(test_auto_login())
