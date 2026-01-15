"""Review scrapers for different app stores."""

from ..models import Review
from .app_store import AppStoreScraper
from .google_play import GooglePlayScraper

__all__ = ["AppStoreScraper", "GooglePlayScraper", "Review"]
