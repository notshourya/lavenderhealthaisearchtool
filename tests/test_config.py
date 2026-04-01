import pytest
import os


def test_env_example_has_required_keys():
    """Ensure .env.example documents all required variables."""
    with open(".env.example") as f:
        content = f.read()
    for key in ["DATABASE_URL", "REDIS_URL", "APOLLO_API_KEY", "ANTHROPIC_API_KEY"]:
        assert key in content, f"Missing {key} in .env.example"


def test_config_loads_database_url(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "postgresql://test:test@localhost/testdb")
    monkeypatch.setenv("APOLLO_API_KEY", "test_apollo")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test_anthropic")

    import sys
    import importlib
    sys.modules.pop("config", None)
    config = importlib.import_module("config")

    assert config.DATABASE_URL == "postgresql://test:test@localhost/testdb"


def test_config_defaults(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "postgresql://x:x@localhost/x")
    monkeypatch.setenv("APOLLO_API_KEY", "x")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "x")
    monkeypatch.delenv("REDIS_URL", raising=False)
    monkeypatch.delenv("MAX_REVIEWS_DEFAULT", raising=False)
    monkeypatch.delenv("PROXY_URL", raising=False)

    import sys
    import importlib
    sys.modules.pop("config", None)
    config = importlib.import_module("config")

    assert config.REDIS_URL == "redis://localhost:6379/0"
    assert config.MAX_REVIEWS_DEFAULT == 200
    assert config.PROXY_URL is None


def test_config_raises_if_database_url_missing(monkeypatch):
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.setenv("APOLLO_API_KEY", "x")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "x")

    import sys
    import importlib

    # Remove cached module so import_module triggers fresh execution
    sys.modules.pop("config", None)

    with pytest.raises(KeyError):
        importlib.import_module("config")
