import json
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
                user_name="User",
                rating=5,
                title=None,
                content="Content",
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

