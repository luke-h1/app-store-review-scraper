import hashlib
import json
import logging
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .models import Review

logger = logging.getLogger(__name__)


def _content_fingerprint(review: "Review") -> str:
    """Generate a fingerprint based on review content (ignoring ID).
    
    This helps detect duplicate reviews that may have different IDs
    but are effectively the same review (same user, content, rating, date).
    """
    # Normalize the date to just the date part (no time)
    date_str = review.date.strftime("%Y-%m-%d") if review.date else ""
    # Create fingerprint from user, content, rating, and date
    content = f"{review.app_id}_{review.user_name}_{review.rating}_{review.content}_{date_str}"
    return hashlib.md5(content.encode()).hexdigest()


class ReviewCache:
    def __init__(self, cache_file: str | Path):
        self.cache_file = Path(cache_file)
        self._seen_ids: set[str] = set()
        self._seen_fingerprints: set[str] = set()  # Content-based fingerprints
        self._load()

    def _load(self) -> None:
        if self.cache_file.exists():
            try:
                with open(self.cache_file) as f:
                    data = json.load(f)
                    self._seen_ids = set(data.get("seen_ids", []))
                    self._seen_fingerprints = set(data.get("seen_fingerprints", []))
                logger.info(
                    f"Loaded {len(self._seen_ids)} cached review IDs and "
                    f"{len(self._seen_fingerprints)} content fingerprints"
                )
            except (json.JSONDecodeError, OSError) as e:
                logger.warning(f"Could not load cache file: {e}")
                self._seen_ids = set()
                self._seen_fingerprints = set()
        else:
            logger.info("No cache file found, starting fresh")

    def save(self) -> None:
        try:
            # Ensure parent directory exists
            self.cache_file.parent.mkdir(parents=True, exist_ok=True)

            with open(self.cache_file, "w") as f:
                json.dump(
                    {
                        "seen_ids": list(self._seen_ids),
                        "seen_fingerprints": list(self._seen_fingerprints),
                    },
                    f,
                    indent=2,
                )
            logger.info(
                f"Saved {len(self._seen_ids)} review IDs and "
                f"{len(self._seen_fingerprints)} fingerprints to cache"
            )
        except OSError as e:
            logger.error(f"Could not save cache file: {e}")

    def is_new(self, review: "Review") -> bool:
        """Check if a review is new (not seen before).

        Checks both the review ID and a content-based fingerprint to catch
        duplicates that may have different IDs but identical content.

        Args:
            review: Review to check.

        Returns:
            True if the review is new, False if already seen.
        """
        # Check by ID first
        if review.id in self._seen_ids:
            logger.debug(
                f"Review {review.id} already in cache by ID "
                f"(user: {review.user_name}, date: {review.date})"
            )
            return False

        # Check by content fingerprint (catches same review with different IDs)
        fingerprint = _content_fingerprint(review)
        if fingerprint in self._seen_fingerprints:
            logger.debug(
                f"Review {review.id} already in cache by content fingerprint "
                f"(user: {review.user_name}, date: {review.date})"
            )
            return False

        return True

    def mark_seen(self, review: "Review") -> None:
        """Mark a review as seen.

        Stores both the review ID and a content fingerprint to prevent
        duplicate reviews with different IDs from being sent.

        Args:
            review: Review to mark as seen.
        """
        if review.id in self._seen_ids:
            logger.warning(f"Review {review.id} was already marked as seen, but marking again")
        
        self._seen_ids.add(review.id)
        fingerprint = _content_fingerprint(review)
        self._seen_fingerprints.add(fingerprint)
        
        logger.debug(
            f"Marked review {review.id} as seen "
            f"(total IDs: {len(self._seen_ids)}, fingerprints: {len(self._seen_fingerprints)})"
        )

    def filter_new(self, reviews: list["Review"]) -> list["Review"]:
        """Filter a list of reviews to only include new ones.

        Also deduplicates within the input list by content fingerprint
        to handle cases where the same review appears multiple times
        with different IDs.

        Args:
            reviews: List of reviews to filter.

        Returns:
            List of reviews that haven't been seen before (deduplicated).
        """
        new_reviews = []
        seen_fingerprints_in_batch: set[str] = set()

        for review in reviews:
            # Skip if already in cache (by ID or fingerprint)
            if not self.is_new(review):
                continue

            # Also deduplicate within this batch by content fingerprint
            fingerprint = _content_fingerprint(review)
            if fingerprint in seen_fingerprints_in_batch:
                logger.debug(
                    f"Skipping duplicate review in batch by fingerprint: {review.id} "
                    f"(user: {review.user_name})"
                )
                continue

            seen_fingerprints_in_batch.add(fingerprint)
            new_reviews.append(review)

        duplicates_in_batch = len(reviews) - len(new_reviews) - sum(
            1 for r in reviews if not self.is_new(r)
        )
        if duplicates_in_batch > 0:
            logger.info(f"Filtered out {duplicates_in_batch} duplicate reviews within batch")

        return new_reviews

    def mark_all_seen(self, reviews: list["Review"]) -> None:
        """Mark all reviews in a list as seen.

        Args:
            reviews: List of reviews to mark as seen.
        """
        for review in reviews:
            self.mark_seen(review)

    def clear(self) -> None:
        self._seen_ids = set()
        self._seen_fingerprints = set()
        logger.info("Cache cleared")

    @property
    def size(self) -> int:
        return len(self._seen_ids)
