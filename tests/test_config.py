import pytest

from app_store_review_scraper.config import AppStoreConfig, Config, GooglePlayConfig


class TestAppStoreConfig:
    def test_default_country(self):
        config = AppStoreConfig(app_name="test-app")
        assert config.country == "us"
        assert config.app_id is None

    def test_with_app_id(self):
        config = AppStoreConfig(app_name="test-app", app_id=123456789, country="gb")
        assert config.app_name == "test-app"
        assert config.app_id == 123456789
        assert config.country == "gb"


class TestGooglePlayConfig:
    def test_default_values(self):
        config = GooglePlayConfig(package_id="com.example.app")
        assert config.country == "us"
        assert config.language == "en"

    def test_with_all_values(self):
        config = GooglePlayConfig(package_id="com.example.app", country="de", language="de")
        assert config.package_id == "com.example.app"
        assert config.country == "de"
        assert config.language == "de"


class TestConfig:
    def test_from_env_missing_slack_url(self, monkeypatch):
        monkeypatch.delenv("SLACK_WEBHOOK_URL", raising=False)
        with pytest.raises(ValueError, match="SLACK_WEBHOOK_URL"):
            Config.from_env()

    def test_from_env_with_slack_url(self, monkeypatch):
        monkeypatch.setenv("SLACK_WEBHOOK_URL", "https://hooks.slack.com/test")
        monkeypatch.delenv("APP_STORE_APPS", raising=False)
        monkeypatch.delenv("GOOGLE_PLAY_APPS", raising=False)

        config = Config.from_env()
        assert config.slack_webhook_url == "https://hooks.slack.com/test"
        assert config.app_store_apps == []
        assert config.google_play_apps == []

    def test_from_env_parse_app_store_apps(self, monkeypatch):
        monkeypatch.setenv("SLACK_WEBHOOK_URL", "https://hooks.slack.com/test")
        monkeypatch.setenv("APP_STORE_APPS", "myapp:123456:gb,otherapp::us")

        config = Config.from_env()
        assert len(config.app_store_apps) == 2

        assert config.app_store_apps[0].app_name == "myapp"
        assert config.app_store_apps[0].app_id == 123456
        assert config.app_store_apps[0].country == "gb"

        assert config.app_store_apps[1].app_name == "otherapp"
        assert config.app_store_apps[1].app_id is None
        assert config.app_store_apps[1].country == "us"

    def test_from_env_parse_google_play_apps(self, monkeypatch):
        monkeypatch.setenv("SLACK_WEBHOOK_URL", "https://hooks.slack.com/test")
        monkeypatch.setenv("GOOGLE_PLAY_APPS", "com.example.app:de:de,com.other.app::fr")

        config = Config.from_env()
        assert len(config.google_play_apps) == 2

        assert config.google_play_apps[0].package_id == "com.example.app"
        assert config.google_play_apps[0].country == "de"
        assert config.google_play_apps[0].language == "de"

        assert config.google_play_apps[1].package_id == "com.other.app"
        assert config.google_play_apps[1].country == "us"
        assert config.google_play_apps[1].language == "fr"
