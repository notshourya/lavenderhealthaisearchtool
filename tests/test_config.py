import pytest
import os


def test_env_example_has_required_keys():
    """Ensure .env.example documents all required variables."""
    with open(".env.example") as f:
        content = f.read()
    for key in ["DATABASE_URL", "REDIS_URL", "APOLLO_API_KEY", "GEMINI_API_KEY"]:
        assert key in content, f"Missing {key} in .env.example"


def test_config_loads_database_url(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "postgresql://test:test@localhost/testdb")
    monkeypatch.setenv("APOLLO_API_KEY", "test_apollo")
    monkeypatch.setenv("GEMINI_API_KEY", "test_gemini")

    import sys
    import importlib
    sys.modules.pop("config", None)
    config = importlib.import_module("config")

    assert config.DATABASE_URL == "postgresql://test:test@localhost/testdb"


def test_config_defaults(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "postgresql://x:x@localhost/x")
    monkeypatch.setenv("APOLLO_API_KEY", "x")
    monkeypatch.setenv("GEMINI_API_KEY", "x")
    monkeypatch.delenv("REDIS_URL", raising=False)
    monkeypatch.delenv("MAX_REVIEWS_DEFAULT", raising=False)
    monkeypatch.delenv("PROXY_URL", raising=False)
    monkeypatch.delenv("DISCOVERY_NEWEST_SAMPLE_REVIEWS", raising=False)
    monkeypatch.delenv("DISCOVERY_LOWEST_SAMPLE_REVIEWS", raising=False)
    monkeypatch.delenv("DISCOVERY_LOWEST_SAMPLE_THRESHOLD", raising=False)
    monkeypatch.delenv("DISCOVERY_MAX_SEARCH_CELLS", raising=False)
    monkeypatch.delenv("DISCOVERY_CELL_SIZE_DEGREES", raising=False)
    monkeypatch.delenv("DISCOVERY_CELL_ZOOM", raising=False)
    monkeypatch.delenv("DEEP_SCRAPE_STAGE_ONE_REVIEWS", raising=False)
    monkeypatch.delenv("DEEP_SCRAPE_STAGE_TWO_REVIEWS", raising=False)
    monkeypatch.delenv("DEEP_SCRAPE_STAGE_ONE_MIN_KEYWORD_REVIEWS", raising=False)
    monkeypatch.delenv("DEEP_SCRAPE_STAGE_TWO_MIN_KEYWORD_REVIEWS", raising=False)
    monkeypatch.delenv("RECENT_REVIEW_WINDOW_DAYS", raising=False)
    monkeypatch.delenv("RECENT_REVIEW_MIN_INSURER_COMPLAINTS", raising=False)
    monkeypatch.delenv("MIN_UNIQUE_INSURER_REVIEWERS", raising=False)
    monkeypatch.delenv("MIN_DOMINANT_ISSUE_CATEGORY_REVIEWS", raising=False)
    monkeypatch.delenv("RECENT_CLUSTER_MIN_MONTH_BUCKET_REVIEWS", raising=False)
    monkeypatch.delenv("SCRAPER_REVIEW_TAB_TIMEOUT_MS", raising=False)
    monkeypatch.delenv("SCRAPER_REVIEW_METADATA_TIMEOUT_MS", raising=False)
    monkeypatch.delenv("SCRAPER_PAGE_GOTO_TIMEOUT_MS", raising=False)
    monkeypatch.delenv("SCRAPER_RESULTS_FEED_WAIT_TIMEOUT_MS", raising=False)
    monkeypatch.delenv("LLM_REVIEW_BATCH_SIZE", raising=False)
    monkeypatch.delenv("QUALIFICATION_PROFILE", raising=False)
    monkeypatch.delenv("SCORE_THRESHOLD_STRICT", raising=False)
    monkeypatch.delenv("SCORE_THRESHOLD_BALANCED", raising=False)
    monkeypatch.delenv("SCORE_THRESHOLD_RECALL", raising=False)
    monkeypatch.delenv("SCORE_WEIGHT_INSURER", raising=False)
    monkeypatch.delenv("SCORE_WEIGHT_RATE", raising=False)
    monkeypatch.delenv("SCORE_WEIGHT_RECENCY", raising=False)
    monkeypatch.delenv("SCORE_WEIGHT_UNIQUENESS", raising=False)
    monkeypatch.delenv("SHARED_REVIEW_WEIGHT", raising=False)
    monkeypatch.delenv("EFFECTIVE_SIGNAL_CAP", raising=False)
    monkeypatch.delenv("RATE_SCORE_CAP_MULTIPLIER", raising=False)
    monkeypatch.delenv("CONFIDENCE_EVIDENCE_LOG_CAP", raising=False)
    monkeypatch.delenv("CONFIDENCE_EVIDENCE_WEIGHT", raising=False)
    monkeypatch.delenv("CONFIDENCE_VOLUME_WEIGHT", raising=False)
    monkeypatch.delenv("FINAL_SCORE_DAMP_BASE", raising=False)
    monkeypatch.delenv("FINAL_SCORE_DAMP_SCALE", raising=False)
    monkeypatch.delenv("ENABLE_GRAY_ZONE_VALIDATION", raising=False)
    monkeypatch.delenv("GRAY_ZONE_VALIDATION_BAND", raising=False)

    import sys
    import importlib
    sys.modules.pop("config", None)
    config = importlib.import_module("config")

    assert config.REDIS_URL == "redis://localhost:6379/0"
    assert config.MAX_REVIEWS_DEFAULT == 0
    assert config.DISCOVERY_NEWEST_SAMPLE_REVIEWS == 8
    assert config.DISCOVERY_LOWEST_SAMPLE_REVIEWS == 8
    assert config.DISCOVERY_LOWEST_SAMPLE_THRESHOLD == 75
    assert config.DISCOVERY_MAX_SEARCH_CELLS == 40
    assert config.DISCOVERY_CELL_SIZE_DEGREES == 0.05
    assert config.DISCOVERY_CELL_ZOOM == 12
    assert config.DEEP_SCRAPE_STAGE_ONE_REVIEWS == 25
    assert config.DEEP_SCRAPE_STAGE_TWO_REVIEWS == 100
    assert config.DEEP_SCRAPE_STAGE_ONE_MIN_KEYWORD_REVIEWS == 1
    assert config.DEEP_SCRAPE_STAGE_TWO_MIN_KEYWORD_REVIEWS == 2
    assert config.RECENT_REVIEW_WINDOW_DAYS == 180
    assert config.RECENT_REVIEW_MIN_INSURER_COMPLAINTS == 2
    assert config.MIN_UNIQUE_INSURER_REVIEWERS == 1
    assert config.MIN_DOMINANT_ISSUE_CATEGORY_REVIEWS == 1
    assert config.RECENT_CLUSTER_MIN_MONTH_BUCKET_REVIEWS == 1
    assert config.SCRAPER_REVIEW_TAB_TIMEOUT_MS == 8000
    assert config.SCRAPER_REVIEW_METADATA_TIMEOUT_MS == 5000
    assert config.SCRAPER_PAGE_GOTO_TIMEOUT_MS == 30000
    assert config.SCRAPER_RESULTS_FEED_WAIT_TIMEOUT_MS == 12000
    assert config.MIN_CONFIRMED_COMPLAINTS == 1
    assert config.RATE_GUARD_MIN_REVIEWS == 80
    assert config.COMPLAINT_RATE_THRESHOLD == 0.01
    assert config.LLM_REVIEW_BATCH_SIZE == 8
    assert config.QUALIFICATION_PROFILE == "balanced"
    assert config.SCORE_THRESHOLD_STRICT == 0.72
    assert config.SCORE_THRESHOLD_BALANCED == 0.55
    assert config.SCORE_THRESHOLD_RECALL == 0.38
    assert config.SCORE_WEIGHT_INSURER == 0.35
    assert config.SCORE_WEIGHT_RATE == 0.25
    assert config.SCORE_WEIGHT_RECENCY == 0.25
    assert config.SCORE_WEIGHT_UNIQUENESS == 0.15
    assert config.SHARED_REVIEW_WEIGHT == 0.5
    assert config.EFFECTIVE_SIGNAL_CAP == 6
    assert config.RATE_SCORE_CAP_MULTIPLIER == 4
    assert config.CONFIDENCE_EVIDENCE_LOG_CAP == 15
    assert config.CONFIDENCE_EVIDENCE_WEIGHT == 0.7
    assert config.CONFIDENCE_VOLUME_WEIGHT == 0.3
    assert config.FINAL_SCORE_DAMP_BASE == 0.6
    assert config.FINAL_SCORE_DAMP_SCALE == 0.4
    assert config.ENABLE_GRAY_ZONE_VALIDATION is True
    assert config.GRAY_ZONE_VALIDATION_BAND == 0.08
    assert config.PROXY_URL is None


def test_config_raises_if_database_url_missing(monkeypatch):
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.setenv("APOLLO_API_KEY", "x")
    monkeypatch.setenv("GEMINI_API_KEY", "x")

    import sys
    import importlib

    # Remove cached module so import_module triggers fresh execution
    sys.modules.pop("config", None)

    with pytest.raises(KeyError):
        importlib.import_module("config")
