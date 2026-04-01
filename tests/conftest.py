import sys
import os
import pytest


@pytest.fixture(autouse=True)
def clear_config_module():
    """Remove config from sys.modules after each test to prevent caching."""
    yield
    sys.modules.pop("config", None)
    sys.modules.pop("db.session", None)


@pytest.fixture(autouse=True)
def required_env_vars(monkeypatch):
    """Ensure required env vars are always set so config/db.session can be imported."""
    monkeypatch.setenv("DATABASE_URL", os.environ.get(
        "DATABASE_URL", "postgresql://lavender:lavender@localhost:5432/lavenderhealth"
    ))
    monkeypatch.setenv("APOLLO_API_KEY", os.environ.get("APOLLO_API_KEY", "test"))
    monkeypatch.setenv("ANTHROPIC_API_KEY", os.environ.get("ANTHROPIC_API_KEY", "test"))


@pytest.fixture(autouse=True)
def hide_env_file():
    """Temporarily hide .env file during tests to allow testing missing env vars."""
    env_path = os.path.join(os.path.dirname(__file__), "..", ".env")
    env_backup_path = env_path + ".test_backup"

    # Backup .env if it exists
    if os.path.exists(env_path):
        os.rename(env_path, env_backup_path)

    yield

    # Restore .env after test
    if os.path.exists(env_backup_path):
        os.rename(env_backup_path, env_path)
