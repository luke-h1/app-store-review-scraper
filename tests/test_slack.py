from datetime import datetime

import pytest

from app_store_review_scraper.models import Review
from app_store_review_scraper.slack import format_review_for_slack, rating_to_stars


class TestRatingToStars:
    def test_five_stars(self):
        assert rating_to_stars(5) == "⭐⭐⭐⭐⭐"

    def test_one_star(self):
        assert rating_to_stars(1) == "⭐☆☆☆☆"

    def test_three_stars(self):
        assert rating_to_stars(3) == "⭐⭐⭐☆☆"

    def test_zero_stars(self):
        assert rating_to_stars(0) == "☆☆☆☆☆"


class TestFormatReviewForSlack:
    @pytest.fixture
    def sample_review(self):
        return Review(
            id="test_1",
            store="App Store",
            app_name="Test App",
            app_id="123456",
            user_name="TestUser",
            rating=5,
            title="Amazing!",
            content="This app is fantastic.",
            date=datetime(2026, 1, 15, 10, 30),
        )

    def test_format_with_title(self, sample_review):
        message = format_review_for_slack(sample_review)

        assert "attachments" in message
        assert len(message["attachments"]) == 1
        assert message["attachments"][0]["color"] == "#36a64f"  # Green for 5 stars

    def test_format_low_rating(self, sample_review):
        sample_review.rating = 1
        message = format_review_for_slack(sample_review)

        assert message["attachments"][0]["color"] == "#ff0000"  # Red for 1 star

    def test_format_medium_rating(self, sample_review):
        sample_review.rating = 3
        message = format_review_for_slack(sample_review)

        assert message["attachments"][0]["color"] == "#ffcc00"  # Yellow for 3 stars

    def test_format_without_title(self, sample_review):
        sample_review.title = None
        message = format_review_for_slack(sample_review)

        # Should still format without errors
        assert "attachments" in message
