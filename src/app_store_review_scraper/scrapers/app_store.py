"""App Store review scraper using iTunes RSS API."""

import hashlib
import logging
import re
from datetime import datetime

import requests

from ..config import AppStoreConfig
from ..models import Review

logger = logging.getLogger(__name__)


class AppStoreScraper:
    """Scraper for iOS App Store reviews using iTunes RSS API."""

    # iTunes RSS API returns up to 50 reviews per page, max 10 pages
    REVIEWS_PER_PAGE = 50
    MAX_PAGES = 10

    def __init__(self, config: AppStoreConfig):
        self.config = config

    def _get_feed_url(self, page: int = 1) -> str:
        """Build the iTunes RSS feed URL for reviews.

        API format: https://itunes.apple.com/{country}/rss/customerreviews/page={page}/id={app_id}/sortBy=mostRecent/json
        """
        return (
            f"https://itunes.apple.com/{self.config.country}/rss/customerreviews/"
            f"page={page}/id={self.config.app_id}/sortBy=mostRecent/json"
        )

    def fetch_reviews(self, max_reviews: int = 50) -> list[Review]:
        """Fetch reviews from the App Store using iTunes RSS API.

        Args:
            max_reviews: Maximum number of reviews to fetch.

        Returns:
            List of Review objects.
        """
        if not self.config.app_id:
            logger.error("App ID is required for iTunes API. Please provide app_id in config.")
            return []

        logger.info(
            f"Fetching App Store reviews for {self.config.app_name} "
            f"(id: {self.config.app_id}, country: {self.config.country})"
        )

        reviews: list[Review] = []
        pages_needed = min((max_reviews // self.REVIEWS_PER_PAGE) + 1, self.MAX_PAGES)

        for page in range(1, pages_needed + 1):
            if len(reviews) >= max_reviews:
                break

            url = self._get_feed_url(page)
            logger.debug(f"Fetching page {page}: {url}")

            try:
                response = requests.get(
                    url,
                    headers={
                        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
                        "Accept": "application/json",
                    },
                    timeout=30,
                )
                response.raise_for_status()
                data = response.json()

            except requests.RequestException as e:
                logger.error(f"Error fetching reviews from iTunes API: {e}")
                break
            except ValueError as e:
                logger.error(f"Error parsing JSON response: {e}")
                break

            # Parse the feed
            feed = data.get("feed", {})
            entries = feed.get("entry", [])

            if not entries:
                logger.debug(f"No more reviews found on page {page}")
                break

            # First entry might be app metadata, skip if so
            if isinstance(entries, dict):
                entries = [entries]

            for entry in entries:
                # Skip app metadata entry (has im:name but no im:rating)
                if "im:rating" not in entry:
                    continue

                if len(reviews) >= max_reviews:
                    break

                try:
                    # Extract review data
                    review_id_raw = entry.get("id", {}).get("label", "")
                    user_name = entry.get("author", {}).get("name", {}).get("label", "Unknown")
                    rating = int(entry.get("im:rating", {}).get("label", 0))
                    title = entry.get("title", {}).get("label", "")
                    content = entry.get("content", {}).get("label", "")

                    date_str = entry.get("updated", {}).get("label", "")
                    try:
                        review_date = datetime.fromisoformat(date_str.replace("Z", "+00:00"))
                        review_date = review_date.replace(tzinfo=None)
                    except ValueError:
                        review_date = datetime.now()

                    # Create unique review ID - use link if available, otherwise use id or hash
                    # iTunes RSS link field is more reliable than id field
                    link = entry.get("link", {}).get("attributes", {}).get("href", "")
                    if link:
                        # Extract ID from link URL (e.g., https://itunes.apple.com/us/reviews/id1234567890)
                        link_id_match = re.search(r"/id(\d+)", link)
                        if link_id_match:
                            review_id = link_id_match.group(1)
                        else:
                            # Use the full link as ID
                            review_id = link
                    elif review_id_raw:
                        # Extract ID from review_id if it's a URL
                        id_match = re.search(r"/id(\d+)", review_id_raw)
                        if id_match:
                            review_id = id_match.group(1)
                        else:
                            review_id = review_id_raw
                    else:
                        # Fallback: create hash-based ID from content + user + date
                        content_hash = hashlib.md5(
                            f"{user_name}{title}{content}{review_date.isoformat()}".encode()
                        ).hexdigest()[:12]
                        review_id = f"hash_{content_hash}"

                    # Create unique review ID with app_id prefix
                    unique_id = f"appstore_{self.config.app_id}_{review_id}"
                    
                    logger.debug(
                        f"Generated review ID: {unique_id} for user {user_name} "
                        f"(raw_id: {review_id_raw[:50] if review_id_raw else 'empty'}, "
                        f"link: {link[:50] if link else 'none'})"
                    )

                    reviews.append(
                        Review(
                            id=unique_id,
                            store="App Store",
                            app_name=self.config.app_name,
                            app_id=str(self.config.app_id),
                            user_name=user_name,
                            rating=rating,
                            title=title if title else None,
                            content=content,
                            date=review_date,
                        )
                    )

                except (KeyError, TypeError, ValueError) as e:
                    logger.warning(f"Error parsing review entry: {e}")
                    continue

            logger.debug(f"Fetched {len(entries)} entries from page {page}")

        logger.info(f"Fetched {len(reviews)} reviews from App Store")
        return reviews
