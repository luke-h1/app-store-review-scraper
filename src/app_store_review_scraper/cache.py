import json
import logging
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .models import Review

logger = logging.getLogger(__name__)


class ReviewCache:
    def __init__(self, cache_file: str | Path):
        self.cache_file = Path(cache_file)
        self._seen_ids: set[str] = set()
        self._load()

    def _load(self) -> None:
        if self.cache_file.exists():
            try:
                with open(self.cache_file) as f:
                    data = json.load(f)
                    self._seen_ids = set(data.get("seen_ids", []))
                logger.info(f"Loaded {len(self._seen_ids)} cached review IDs")
            except (json.JSONDecodeError, OSError) as e:
                logger.warning(f"Could not load cache file: {e}")
                self._seen_ids = set()
        else:
            logger.info("No cache file found, starting fresh")

    def save(self) -> None:
        try:
            # Ensure parent directory exists
            self.cache_file.parent.mkdir(parents=True, exist_ok=True)

            with open(self.cache_file, "w") as f:
                json.dump({"seen_ids": list(self._seen_ids)}, f, indent=2)
            logger.info(f"Saved {len(self._seen_ids)} review IDs to cache")
        except OSError as e:
            logger.error(f"Could not save cache file: {e}")

    def is_new(self, review: "Review") -> bool:
        """Check if a review is new (not seen before).

        Args:
            review: Review to check.

        Returns:
            True if the review is new, False if already seen.
        """
        is_new = review.id not in self._seen_ids
        if not is_new:
            logger.debug(f"Review {review.id} already in cache (user: {review.user_name}, date: {review.date})")
        return is_new

    def mark_seen(self, review: "Review") -> None:
        """Mark a review as seen.

        Args:
            review: Review to mark as seen.
        """
        if review.id in self._seen_ids:
            logger.warning(f"Review {review.id} was already marked as seen, but marking again")
        self._seen_ids.add(review.id)
        logger.debug(f"Marked review {review.id} as seen (total cached: {len(self._seen_ids)})")

    def filter_new(self, reviews: list["Review"]) -> list["Review"]:
        """Filter a list of reviews to only include new ones.

        Args:
            reviews: List of reviews to filter.

        Returns:
            List of reviews that haven't been seen before.
        """
        return [r for r in reviews if self.is_new(r)]

    def mark_all_seen(self, reviews: list["Review"]) -> None:
        """Mark all reviews in a list as seen.

        Args:
            reviews: List of reviews to mark as seen.
        """
        for review in reviews:
            self.mark_seen(review)

    def clear(self) -> None:
        self._seen_ids = set()
        logger.info("Cache cleared")

    @property
    def size(self) -> int:
        return len(self._seen_ids)
