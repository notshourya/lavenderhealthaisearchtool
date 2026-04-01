import os
import pytest


@pytest.fixture(autouse=True)
def cleanup_dotenv_before_each_test(monkeypatch):
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
