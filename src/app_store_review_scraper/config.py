import os
from dataclasses import dataclass, field


@dataclass
class AppStoreConfig:
    app_name: str
    app_id: int | None = None
    country: str = "us"


@dataclass
class GooglePlayConfig:
    package_id: str
    country: str = "us"
    language: str = "en"


@dataclass
class Config:
    slack_webhook_url: str
    app_store_apps: list[AppStoreConfig] = field(default_factory=list)
    google_play_apps: list[GooglePlayConfig] = field(default_factory=list)
    reviews_cache_file: str = "reviews_cache.json"
    max_reviews_per_run: int = 50

    @classmethod
    def from_env(cls) -> "Config":
        slack_webhook_url = os.environ.get("SLACK_WEBHOOK_URL", "")

        if not slack_webhook_url:
            raise ValueError("SLACK_WEBHOOK_URL environment variable is required")

        # Parse App Store apps from env: APP_STORE_APPS="app_name:app_id:country,..."
        app_store_apps = []
        app_store_env = os.environ.get("APP_STORE_APPS", "")
        if app_store_env:
            for app_str in app_store_env.split(","):
                parts = app_str.strip().split(":")
                if len(parts) >= 1:
                    app_name = parts[0]
                    app_id = int(parts[1]) if len(parts) > 1 and parts[1] else None
                    country = parts[2] if len(parts) > 2 else "us"
                    app_store_apps.append(
                        AppStoreConfig(app_name=app_name, app_id=app_id, country=country)
                    )

        # Parse Google Play apps from env: GOOGLE_PLAY_APPS="package_id:country:lang,..."
        google_play_apps = []
        google_play_env = os.environ.get("GOOGLE_PLAY_APPS", "")
        if google_play_env:
            for app_str in google_play_env.split(","):
                parts = app_str.strip().split(":")
                if len(parts) >= 1:
                    package_id = parts[0]
                    country = parts[1] if len(parts) > 1 and parts[1] else "us"
                    language = parts[2] if len(parts) > 2 else "en"
                    google_play_apps.append(
                        GooglePlayConfig(
                            package_id=package_id, country=country, language=language
                        )
                    )

        reviews_cache_file = os.environ.get("REVIEWS_CACHE_FILE", "reviews_cache.json")
        max_reviews = int(os.environ.get("MAX_REVIEWS_PER_RUN", "50"))

        return cls(
            slack_webhook_url=slack_webhook_url,
            app_store_apps=app_store_apps,
            google_play_apps=google_play_apps,
            reviews_cache_file=reviews_cache_file,
            max_reviews_per_run=max_reviews,
        )

