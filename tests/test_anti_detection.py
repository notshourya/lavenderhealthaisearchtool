import pytest
from scraper.anti_detection import get_random_user_agent, get_random_delay, get_browser_launch_args


def test_user_agent_rotates():
    agents = {get_random_user_agent() for _ in range(20)}
    assert len(agents) > 1, "Expected multiple different user agents"


def test_user_agent_looks_real():
    agent = get_random_user_agent()
    assert "Mozilla" in agent
    assert "Chrome" in agent or "Firefox" in agent or "Safari" in agent


def test_delay_within_range():
    for _ in range(50):
        delay = get_random_delay(min_seconds=2.0, max_seconds=5.0)
        assert 2.0 <= delay <= 5.0


def test_delay_default_range():
    delay = get_random_delay()
    assert 2.0 <= delay <= 5.0


def test_browser_launch_args_returns_list():
    args = get_browser_launch_args(proxy_url=None)
    assert isinstance(args, list)
    assert "--no-sandbox" in args


def test_browser_launch_args_with_proxy():
    args = get_browser_launch_args(proxy_url="http://proxy:8080")
    assert any("proxy" in arg for arg in args)
