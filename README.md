# App Store Review scraper

Automatically scrape App Store (iOS) and Google Play reviews and post new ones to Slack.

## Quick Start

### Prerequisites

- Python 3.11+
- [uv](https://docs.astral.sh/uv/) package manager
- Slack webhook URL

### Installation

```bash
# Install dependencies with uv
uv sync

# Install Playwright browsers (for Google Play scraping)
uv run playwright install chromium
```

### Configuration

Set the following environment variables:

```bash
# Required: Slack webhook URL
export SLACK_WEBHOOK_URL="https://hooks.slack.com/services/xxx/yyy/zzz"

# App Store apps (format: app_name:app_id:country,...)
# app_id is optional - will be looked up automatically
export APP_STORE_APPS="minecraft:479516143:us,spotify::gb"

# Google Play apps (format: package_id:country:language,...)
export GOOGLE_PLAY_APPS="com.spotify.music:us:en,com.netflix.mediaclient:gb:en"

# Optional: Maximum reviews to fetch per app (default: 50)
export MAX_REVIEWS_PER_RUN="50"

# Optional: Cache file location (default: reviews_cache.json)
export REVIEWS_CACHE_FILE="reviews_cache.json"
```

### Running Locally

```bash
# Run the review checker
uv run review-notifier

# Dry run (don't post to Slack)
uv run review-notifier --dry-run

# Clear cache and start fresh
uv run review-notifier --clear-cache

# Verbose output
uv run review-notifier -v

# Skip summary message
uv run review-notifier --no-summary
```

### 2. Schedule

The workflow runs automatically every hour. You can also trigger it manually from the **Actions** tab with options for dry-run and cache clearing.

## App Configuration Format

### App Store Apps

```
APP_STORE_APPS="app_name:app_id:country"
```

- `app_name` (required): Name of the app
- `app_id` (optional): Numeric App Store ID. If not provided, it will be searched automatically
- `country` (optional, default: `us`): Two-letter country code (ISO 3166-1 alpha-2)

**Examples:**

```bash
# Full specification
APP_STORE_APPS="minecraft:479516143:us"

# Without app_id (will be looked up)
APP_STORE_APPS="spotify::gb"

# Multiple apps
APP_STORE_APPS="minecraft:479516143:us,spotify::gb,netflix:363590051:us"
```

### Google Play Apps

```
GOOGLE_PLAY_APPS="package_id:country:language"
```

- `package_id` (required): Android package ID (e.g., `com.spotify.music`)
- `country` (optional, default: `us`): Two-letter country code
- `language` (optional, default: `en`): Two-letter language code

**Examples:**

```bash
# Full specification
GOOGLE_PLAY_APPS="com.spotify.music:us:en"

# Multiple apps
GOOGLE_PLAY_APPS="com.spotify.music:us:en,com.netflix.mediaclient:gb:en"
```

## Development

```bash
# Install dev dependencies
uv sync --dev

# Run linting
uv run ruff check .

# Run formatting
uv run ruff format .

# Run type checking
uv run mypy src/app_store_review_scraper

# Run tests
uv run pytest
```

### Pre-commit Hooks

This project uses [pre-commit](https://pre-commit.com/) to run linting and type checking before each commit.

```bash
# Install the git hooks
uv run pre-commit install

# Run hooks on all files (optional)
uv run pre-commit run --all-files
```

The following hooks are configured:

- **ruff** - Linting with auto-fix and formatting
- **mypy** - Type checking
- **pre-commit-hooks** - Trailing whitespace, end-of-file fixer, YAML validation

## License

MIT
