import argparse
import logging
import sys
import time
from pathlib import Path

from dotenv import load_dotenv

from .cache import ReviewCache
from .config import Config
from .scrapers.app_store import AppStoreScraper
from .scrapers.google_play import GooglePlayScraper
from .slack import SlackNotifier

logger = logging.getLogger(__name__)


def setup_logging(verbose: bool = False) -> None:
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] %(name)s - %(message)s",
        handlers=[logging.StreamHandler(sys.stdout)],
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="Fetch app reviews and post new ones to Slack")
    parser.add_argument("-v", "--verbose", action="store_true", help="Enable verbose logging")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Fetch reviews but don't post to Slack or update cache",
    )
    parser.add_argument(
        "--clear-cache",
        action="store_true",
        help="Clear the review cache before running",
    )
    parser.add_argument(
        "--no-summary",
        action="store_true",
        help="Don't post a summary message to Slack",
    )
    args = parser.parse_args()

    setup_logging(args.verbose)

    # Load .env file if present
    env_file = Path(".env")
    if env_file.exists():
        load_dotenv(env_file)
        logger.info("Loaded environment variables from .env file")

    try:
        config = Config.from_env()
    except ValueError as e:
        logger.error(f"Configuration error: {e}")
        return 1

    if not config.app_store_apps and not config.google_play_apps:
        logger.warning(
            "No apps configured. Set APP_STORE_APPS and/or GOOGLE_PLAY_APPS environment variables."
        )
        return 0

    cache = ReviewCache(config.reviews_cache_file)
    notifier = SlackNotifier(config.slack_webhook_url)

    if args.clear_cache:
        cache.clear()

    all_reviews = []
    total_apps = len(config.app_store_apps) + len(config.google_play_apps)

    for app_config in config.app_store_apps:
        logger.info(f"Processing App Store app: {app_config.app_name}")
        scraper = AppStoreScraper(app_config)
        reviews = scraper.fetch_reviews(max_reviews=config.max_reviews_per_run)
        all_reviews.extend(reviews)
        time.sleep(1)

    for gp_config in config.google_play_apps:
        logger.info(f"Processing Google Play app: {gp_config.package_id}")
        gp_scraper = GooglePlayScraper(gp_config)
        reviews = gp_scraper.fetch_reviews(max_reviews=config.max_reviews_per_run)
        all_reviews.extend(reviews)
        time.sleep(1)

    new_reviews = cache.filter_new(all_reviews)
    logger.info(f"Found {len(new_reviews)} new reviews out of {len(all_reviews)} total")

    new_reviews.sort(key=lambda r: r.date, reverse=True)

    posted_count = 0
    for review in new_reviews:
        if args.dry_run:
            logger.info(
                f"[DRY RUN] Would post review from {review.user_name} "
                f"({review.store}, {review.rating}⭐): {review.content[:100]}..."
            )
            posted_count += 1
        else:
            if notifier.send_review(review):
                cache.mark_seen(review)
                posted_count += 1
                time.sleep(0.5)

    if not args.no_summary and not args.dry_run:
        notifier.send_summary(posted_count, total_apps)

    if not args.dry_run:
        cache.save()

    logger.info(f"Completed. Posted {posted_count} new reviews.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
