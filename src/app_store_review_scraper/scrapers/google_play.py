"""Google Play Store review scraper using Playwright.

Based on: https://serpapi.com/blog/scrape-all-google-play-app-reviews-in-python/
"""

import hashlib
import logging
import re
import time
from datetime import datetime, timedelta

from parsel import Selector
from playwright.sync_api import sync_playwright

from ..config import GooglePlayConfig
from ..models import Review

logger = logging.getLogger(__name__)


def parse_relative_date(date_str: str) -> datetime:
    date_str = date_str.lower().strip()
    now = datetime.now()

    date_formats = [
        "%B %d, %Y",  # January 15, 2026
        "%d %B %Y",  # 15 January 2026
        "%b %d, %Y",  # Jan 15, 2026
        "%d %b %Y",  # 15 Jan 2026
    ]

    for fmt in date_formats:
        try:
            return datetime.strptime(date_str, fmt)
        except ValueError:
            continue

    if "just now" in date_str or "now" in date_str:
        return now

    match = re.search(r"(\d+)\s*(second|minute|hour|day|week|month|year)s?\s*ago", date_str)
    if match:
        value = int(match.group(1))
        unit = match.group(2)

        if unit == "second":
            return now - timedelta(seconds=value)
        elif unit == "minute":
            return now - timedelta(minutes=value)
        elif unit == "hour":
            return now - timedelta(hours=value)
        elif unit == "day":
            return now - timedelta(days=value)
        elif unit == "week":
            return now - timedelta(weeks=value)
        elif unit == "month":
            return now - timedelta(days=value * 30)
        elif unit == "year":
            return now - timedelta(days=value * 365)

    logger.warning(f"Could not parse date: {date_str}, using current time")
    return now


class GooglePlayScraper:
    def __init__(self, config: GooglePlayConfig):
        self.config = config
        self.base_url = f"https://play.google.com/store/apps/details?id={config.package_id}&hl={config.language}&gl={config.country}"

    def fetch_reviews(self, max_reviews: int = 50) -> list[Review]:
        """Fetch reviews from Google Play Store.

        Args:
            max_reviews: Maximum number of reviews to fetch.

        Returns:
            List of Review objects.
        """
        logger.info(
            f"Fetching Google Play reviews for {self.config.package_id} "
            f"(country: {self.config.country})"
        )

        reviews = []
        seen_ids: set[str] = set()

        try:
            with sync_playwright() as playwright:
                browser = playwright.chromium.launch(headless=True)
                context = browser.new_context(
                    user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
                )
                page = context.new_page()
                page.goto(self.base_url, wait_until="networkidle")

                app_name = self.config.package_id
                try:
                    app_name_element = page.query_selector("h1[itemprop='name']")
                    if app_name_element:
                        app_name = app_name_element.inner_text()
                except Exception:
                    pass

                see_all_button = page.query_selector(".Jwxk6d .u4ICaf button")
                if see_all_button:
                    logger.info("Clicking 'See all reviews' button")
                    see_all_button.click(force=True)
                    time.sleep(3)

                scroll_container = ".fysCi"
                scroll_count = 0
                max_scrolls = max(1, max_reviews // 10)

                if page.query_selector(scroll_container):
                    last_height = page.evaluate(
                        f'() => document.querySelector("{scroll_container}").scrollTop'
                    )

                    while scroll_count < max_scrolls:
                        logger.debug(f"Scrolling... ({scroll_count + 1}/{max_scrolls})")
                        page.keyboard.press("End")
                        time.sleep(2)

                        new_height = page.evaluate(
                            f'() => document.querySelector("{scroll_container}").scrollTop'
                        )

                        if new_height == last_height:
                            break

                        last_height = new_height
                        scroll_count += 1

                selector = Selector(text=page.content())

                for idx, comment in enumerate(selector.css(".RHo1pe")):
                    if idx >= max_reviews:
                        break

                    user_name = comment.css(".X5PpBb::text").get() or "Unknown"
                    user_comment = comment.css(".h3YV2d::text").get() or ""
                    comment_date_str = comment.css(".bp9Aid::text").get() or ""

                    rating_text = comment.css(".iXRFPc::attr(aria-label)").get() or ""
                    rating_match = re.search(r"\d+", rating_text)
                    rating = int(rating_match.group()) if rating_match else 0

                    review_date = parse_relative_date(comment_date_str)

                    normalized_date = review_date.replace(hour=0, minute=0, second=0, microsecond=0)
                    content_hash = hashlib.md5(
                        f"{self.config.package_id}_{user_name}_{rating}_{user_comment}_{normalized_date.isoformat()}".encode()
                    ).hexdigest()[:16]
                    review_id = f"googleplay_{self.config.package_id}_{content_hash}"
                    
                    if review_id in seen_ids:
                        logger.debug(f"Skipping duplicate review ID within fetch: {review_id}")
                        continue
                    seen_ids.add(review_id)

                    reviews.append(
                        Review(
                            id=review_id,
                            store="Google Play",
                            app_name=app_name,
                            app_id=self.config.package_id,
                            user_name=user_name,
                            rating=rating,
                            title=None,
                            content=user_comment,
                            date=review_date,
                        )
                    )

                browser.close()

            logger.info(f"Fetched {len(reviews)} reviews from Google Play")

        except Exception as e:
            logger.error(f"Error fetching Google Play reviews: {e}")

        return reviews
