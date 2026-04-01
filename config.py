import os
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL: str = os.environ["DATABASE_URL"]
REDIS_URL: str = os.getenv("REDIS_URL", "redis://localhost:6379/0")
APOLLO_API_KEY: str = os.environ["APOLLO_API_KEY"]
GEMINI_API_KEY: str = os.environ["GEMINI_API_KEY"]
PROXY_URL: str | None = os.getenv("PROXY_URL") or None
MAX_REVIEWS_DEFAULT: int = int(os.getenv("MAX_REVIEWS_DEFAULT", "200"))
