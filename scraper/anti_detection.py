import asyncio
import random
import time

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:125.0) Gecko/20100101 Firefox/125.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_4_1) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4.1 Safari/605.1.15",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36 Edg/123.0.0.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:124.0) Gecko/20100101 Firefox/124.0",
]


def get_random_user_agent() -> str:
    return random.choice(USER_AGENTS)


def get_random_delay(min_seconds: float = 2.0, max_seconds: float = 5.0) -> float:
    return random.uniform(min_seconds, max_seconds)


def sleep_random(min_seconds: float = 2.0, max_seconds: float = 5.0) -> None:
    time.sleep(get_random_delay(min_seconds, max_seconds))


async def async_sleep_random(min_seconds: float = 2.0, max_seconds: float = 5.0) -> None:
    await asyncio.sleep(get_random_delay(min_seconds, max_seconds))


def get_browser_launch_args(proxy_url: str | None = None) -> list[str]:
    args = [
        "--no-sandbox",
        "--disable-blink-features=AutomationControlled",
        "--disable-infobars",
        "--disable-dev-shm-usage",
        "--disable-extensions",
    ]
    if proxy_url:
        args.append(f"--proxy-server={proxy_url}")
    return args
