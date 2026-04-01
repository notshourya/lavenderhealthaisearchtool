import pytest
import os


def test_env_example_has_required_keys():
    """Ensure .env.example documents all required variables."""
    with open(".env.example") as f:
        content = f.read()
    for key in ["DATABASE_URL", "REDIS_URL", "APOLLO_API_KEY", "ANTHROPIC_API_KEY"]:
        assert key in content, f"Missing {key} in .env.example"
