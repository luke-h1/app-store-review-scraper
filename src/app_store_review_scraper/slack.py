import logging
from typing import TYPE_CHECKING

import requests

if TYPE_CHECKING:
    from .models import Review

logger = logging.getLogger(__name__)


def rating_to_stars(rating: int) -> str:
    filled = "⭐" * rating
    empty = "☆" * (5 - rating)
    return filled + empty


def format_review_for_slack(review: "Review") -> dict:
    """Format a review as a Slack block message.

    Args:
        review: Review object to format.

    Returns:
        Slack block message dictionary.
    """
    stars = rating_to_stars(review.rating)

    if review.rating >= 4:
        color = "#36a64f"  # Green
    elif review.rating == 3:
        color = "#ffcc00"  # Yellow
    else:
        color = "#ff0000"  # Red

    blocks = [
        {
            "type": "header",
            "text": {
                "type": "plain_text",
                "text": f"📱 New {review.store} Review",
                "emoji": True,
            },
        },
        {
            "type": "section",
            "fields": [
                {"type": "mrkdwn", "text": f"*App:*\n{review.app_name}"},
                {"type": "mrkdwn", "text": f"*Rating:*\n{stars}"},
                {"type": "mrkdwn", "text": f"*User:*\n{review.user_name}"},
                {
                    "type": "mrkdwn",
                    "text": f"*Date:*\n{review.date.strftime('%Y-%m-%d %H:%M')}",
                },
            ],
        },
    ]

    if review.title:
        blocks.append(
            {
                "type": "section",
                "text": {"type": "mrkdwn", "text": f"*Title:* {review.title}"},
            }
        )

    content = review.content[:2000] if review.content else "_No review text_"
    blocks.append(
        {
            "type": "section",
            "text": {"type": "mrkdwn", "text": f"*Review:*\n{content}"},
        }
    )

    blocks.append({"type": "divider"})

    return {
        "attachments": [
            {
                "color": color,
                "blocks": blocks,
            }
        ]
    }


class SlackNotifier:
    def __init__(self, webhook_url: str):
        self.webhook_url = webhook_url

    def send_review(self, review: "Review") -> bool:
        """Send a single review to Slack.

        Args:
            review: Review to send.

        Returns:
            True if successful, False otherwise.
        """
        try:
            message = format_review_for_slack(review)
            response = requests.post(
                self.webhook_url,
                json=message,
                headers={"Content-Type": "application/json"},
                timeout=30,
            )
            response.raise_for_status()
            logger.info(f"Posted review from {review.user_name} to Slack")
            return True

        except requests.RequestException as e:
            logger.error(f"Failed to send review to Slack: {e}")
            return False

    def send_summary(self, new_count: int, total_apps: int) -> bool:
        """Send a summary message to Slack.

        Args:
            new_count: Number of new reviews found.
            total_apps: Total number of apps checked.

        Returns:
            True if successful, False otherwise.
        """
        if new_count == 0:
            message = {
                "text": f"✅ Review check complete: No new reviews found across {total_apps} app(s)."
            }
        else:
            message = {
                "text": f"📊 Review check complete: Found {new_count} new review(s) across {total_apps} app(s)."
            }

        try:
            response = requests.post(
                self.webhook_url,
                json=message,
                headers={"Content-Type": "application/json"},
                timeout=30,
            )
            response.raise_for_status()
            return True

        except requests.RequestException as e:
            logger.error(f"Failed to send summary to Slack: {e}")
            return False
