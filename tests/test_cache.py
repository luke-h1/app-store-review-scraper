import tempfile
from datetime import datetime
from pathlib import Path

import pytest

from app_store_review_scraper.cache import ReviewCache
from app_store_review_scraper.models import Review


@pytest.fixture
def sample_review():
    return Review(
        id="test_review_1",
        store="App Store",
        app_name="Test App",
        app_id="123456",
        user_name="TestUser",
        rating=5,
        title="Great app!",
        content="This is a test review.",
        date=datetime.now(),
    )


@pytest.fixture
def temp_cache_file():
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        yield Path(f.name)


class TestReviewCache:
    def test_new_cache(self, temp_cache_file):
        cache = ReviewCache(temp_cache_file)
        assert cache.size == 0

    def test_is_new(self, temp_cache_file, sample_review):
        cache = ReviewCache(temp_cache_file)
        assert cache.is_new(sample_review) is True

    def test_mark_seen(self, temp_cache_file, sample_review):
        cache = ReviewCache(temp_cache_file)
        assert cache.is_new(sample_review) is True

        cache.mark_seen(sample_review)
        assert cache.is_new(sample_review) is False

    def test_filter_new(self, temp_cache_file):
        cache = ReviewCache(temp_cache_file)

        reviews = [
            Review(
                id=f"review_{i}",
                store="App Store",
                app_name="Test",
                app_id="123456",
                user_name=f"User{i}",  # Different users to avoid fingerprint match
                rating=5,
                title=None,
                content=f"Content {i}",  # Different content to avoid fingerprint match
                date=datetime.now(),
            )
            for i in range(5)
        ]

        # Mark first two as seen
        cache.mark_seen(reviews[0])
        cache.mark_seen(reviews[1])

        new_reviews = cache.filter_new(reviews)
        assert len(new_reviews) == 3

    def test_save_and_load(self, temp_cache_file, sample_review):
        cache = ReviewCache(temp_cache_file)
        cache.mark_seen(sample_review)
        cache.save()

        # Load in new cache instance
        cache2 = ReviewCache(temp_cache_file)
        assert cache2.is_new(sample_review) is False
        assert cache2.size == 1

    def test_clear(self, temp_cache_file, sample_review):
        cache = ReviewCache(temp_cache_file)
        cache.mark_seen(sample_review)
        assert cache.size == 1

        cache.clear()
        assert cache.size == 0
        assert cache.is_new(sample_review) is True

    def test_duplicate_detection_by_fingerprint(self, temp_cache_file):
        """Test that reviews with different IDs but same content are detected as duplicates."""
        cache = ReviewCache(temp_cache_file)
        
        # Create a review and mark it as seen
        review1 = Review(
            id="review_original",
            store="App Store",
            app_name="Test App",
            app_id="123456",
            user_name="SameUser",
            rating=5,
            title="Title",
            content="Same content here",
            date=datetime(2024, 1, 15, 12, 0, 0),
        )
        cache.mark_seen(review1)
        
        # Create a review with different ID but same content/user/rating/date
        review2 = Review(
            id="review_different_id",  # Different ID
            store="App Store",
            app_name="Test App",
            app_id="123456",  # Same app
            user_name="SameUser",  # Same user
            rating=5,  # Same rating
            title="Different Title",  # Title doesn't matter for fingerprint
            content="Same content here",  # Same content
            date=datetime(2024, 1, 15, 14, 30, 0),  # Same day, different time
        )
        
        # Should be detected as duplicate by fingerprint
        assert cache.is_new(review2) is False

    def test_filter_new_deduplicates_within_batch(self, temp_cache_file):
        """Test that filter_new removes duplicates within the same batch."""
        cache = ReviewCache(temp_cache_file)
        
        # Create multiple reviews with same content but different IDs
        reviews = [
            Review(
                id=f"review_{i}",
                store="App Store",
                app_name="Test App",
                app_id="123456",
                user_name="SameUser",
                rating=5,
                title=f"Title {i}",
                content="Identical content",
                date=datetime(2024, 1, 15),
            )
            for i in range(3)
        ]
        
        # All have the same fingerprint, so only one should remain
        new_reviews = cache.filter_new(reviews)
        assert len(new_reviews) == 1

    def test_different_content_not_deduplicated(self, temp_cache_file):
        """Test that reviews with different content are not treated as duplicates."""
        cache = ReviewCache(temp_cache_file)
        
        reviews = [
            Review(
                id=f"review_{i}",
                store="App Store",
                app_name="Test App",
                app_id="123456",
                user_name="SameUser",
                rating=5,
                title="Title",
                content=f"Different content {i}",  # Different content
                date=datetime(2024, 1, 15),
            )
            for i in range(3)
        ]
        
        new_reviews = cache.filter_new(reviews)
        assert len(new_reviews) == 3

    def test_fingerprints_persisted_on_save(self, temp_cache_file):
        """Test that fingerprints are saved and loaded correctly."""
        cache = ReviewCache(temp_cache_file)
        
        review = Review(
            id="original_id",
            store="App Store",
            app_name="Test App",
            app_id="123456",
            user_name="TestUser",
            rating=4,
            title="Title",
            content="Some unique content",
            date=datetime(2024, 1, 15),
        )
        cache.mark_seen(review)
        cache.save()
        
        # Load in a new cache instance
        cache2 = ReviewCache(temp_cache_file)
        
        # Same content with different ID should be detected as duplicate
        review_with_diff_id = Review(
            id="different_id",
            store="App Store",
            app_name="Test App",
            app_id="123456",
            user_name="TestUser",
            rating=4,
            title="Different Title",
            content="Some unique content",
            date=datetime(2024, 1, 15, 10, 0, 0),  # Same day
        )
        
        assert cache2.is_new(review_with_diff_id) is False
