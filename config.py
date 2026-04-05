import os
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL: str = os.environ["DATABASE_URL"]
REDIS_URL: str = os.getenv("REDIS_URL", "redis://localhost:6379/0")
APOLLO_API_KEY: str = os.environ["APOLLO_API_KEY"]
GEMINI_API_KEY: str = os.environ["GEMINI_API_KEY"]
PROXY_URL: str | None = os.getenv("PROXY_URL") or None
# 0 means uncapped review scraping.
MAX_REVIEWS_DEFAULT: int = int(os.getenv("MAX_REVIEWS_DEFAULT", "0"))
POLICY_VERSION: str = os.getenv("POLICY_VERSION", "v1")
DISCOVERY_NEWEST_SAMPLE_REVIEWS: int = int(os.getenv("DISCOVERY_NEWEST_SAMPLE_REVIEWS", "8"))
DISCOVERY_LOWEST_SAMPLE_REVIEWS: int = int(os.getenv("DISCOVERY_LOWEST_SAMPLE_REVIEWS", "8"))
DISCOVERY_LOWEST_SAMPLE_THRESHOLD: int = int(os.getenv("DISCOVERY_LOWEST_SAMPLE_THRESHOLD", "75"))
DISCOVERY_MAX_SEARCH_CELLS: int = int(os.getenv("DISCOVERY_MAX_SEARCH_CELLS", "40"))
DISCOVERY_CELL_SIZE_DEGREES: float = float(os.getenv("DISCOVERY_CELL_SIZE_DEGREES", "0.05"))
DISCOVERY_CELL_ZOOM: int = int(os.getenv("DISCOVERY_CELL_ZOOM", "12"))
DEEP_SCRAPE_STAGE_ONE_REVIEWS: int = int(os.getenv("DEEP_SCRAPE_STAGE_ONE_REVIEWS", "25"))
DEEP_SCRAPE_STAGE_TWO_REVIEWS: int = int(os.getenv("DEEP_SCRAPE_STAGE_TWO_REVIEWS", "100"))
DEEP_SCRAPE_STAGE_ONE_MIN_KEYWORD_REVIEWS: int = int(os.getenv("DEEP_SCRAPE_STAGE_ONE_MIN_KEYWORD_REVIEWS", "1"))
DEEP_SCRAPE_STAGE_TWO_MIN_KEYWORD_REVIEWS: int = int(os.getenv("DEEP_SCRAPE_STAGE_TWO_MIN_KEYWORD_REVIEWS", "2"))
RECENT_REVIEW_WINDOW_DAYS: int = int(os.getenv("RECENT_REVIEW_WINDOW_DAYS", "180"))
RECENT_REVIEW_MIN_INSURER_COMPLAINTS: int = int(os.getenv("RECENT_REVIEW_MIN_INSURER_COMPLAINTS", "2"))
MIN_UNIQUE_INSURER_REVIEWERS: int = int(os.getenv("MIN_UNIQUE_INSURER_REVIEWERS", "1"))
MIN_DOMINANT_ISSUE_CATEGORY_REVIEWS: int = int(os.getenv("MIN_DOMINANT_ISSUE_CATEGORY_REVIEWS", "1"))
RECENT_CLUSTER_MIN_MONTH_BUCKET_REVIEWS: int = int(os.getenv("RECENT_CLUSTER_MIN_MONTH_BUCKET_REVIEWS", "1"))
SCRAPER_REVIEW_TAB_TIMEOUT_MS: int = int(os.getenv("SCRAPER_REVIEW_TAB_TIMEOUT_MS", "8000"))
SCRAPER_REVIEW_METADATA_TIMEOUT_MS: int = int(os.getenv("SCRAPER_REVIEW_METADATA_TIMEOUT_MS", "5000"))
SCRAPER_PAGE_GOTO_TIMEOUT_MS: int = int(os.getenv("SCRAPER_PAGE_GOTO_TIMEOUT_MS", "30000"))
SCRAPER_RESULTS_FEED_WAIT_TIMEOUT_MS: int = int(os.getenv("SCRAPER_RESULTS_FEED_WAIT_TIMEOUT_MS", "12000"))

# Filter tuning knobs for outreach qualification.
# Intent: avoid flagging largely positive clinics on tiny complaint fractions.
MIN_CONFIRMED_COMPLAINTS: int = int(os.getenv("MIN_CONFIRMED_COMPLAINTS", "1"))
RATE_GUARD_MIN_REVIEWS: int = int(os.getenv("RATE_GUARD_MIN_REVIEWS", "80"))
COMPLAINT_RATE_THRESHOLD: float = float(os.getenv("COMPLAINT_RATE_THRESHOLD", "0.01"))
LLM_REVIEW_BATCH_SIZE: int = int(os.getenv("LLM_REVIEW_BATCH_SIZE", "8"))

# Score-based qualification tuning.
QUALIFICATION_PROFILE: str = os.getenv("QUALIFICATION_PROFILE", "balanced").strip().lower()
SCORE_THRESHOLD_STRICT: float = float(os.getenv("SCORE_THRESHOLD_STRICT", "0.72"))
SCORE_THRESHOLD_BALANCED: float = float(os.getenv("SCORE_THRESHOLD_BALANCED", "0.55"))
SCORE_THRESHOLD_RECALL: float = float(os.getenv("SCORE_THRESHOLD_RECALL", "0.38"))

SCORE_WEIGHT_INSURER: float = float(os.getenv("SCORE_WEIGHT_INSURER", "0.35"))
SCORE_WEIGHT_RATE: float = float(os.getenv("SCORE_WEIGHT_RATE", "0.25"))
SCORE_WEIGHT_RECENCY: float = float(os.getenv("SCORE_WEIGHT_RECENCY", "0.25"))
SCORE_WEIGHT_UNIQUENESS: float = float(os.getenv("SCORE_WEIGHT_UNIQUENESS", "0.15"))

SHARED_REVIEW_WEIGHT: float = float(os.getenv("SHARED_REVIEW_WEIGHT", "0.5"))
EFFECTIVE_SIGNAL_CAP: float = float(os.getenv("EFFECTIVE_SIGNAL_CAP", "6"))
RATE_SCORE_CAP_MULTIPLIER: float = float(os.getenv("RATE_SCORE_CAP_MULTIPLIER", "4"))

CONFIDENCE_EVIDENCE_LOG_CAP: float = float(os.getenv("CONFIDENCE_EVIDENCE_LOG_CAP", "15"))
CONFIDENCE_EVIDENCE_WEIGHT: float = float(os.getenv("CONFIDENCE_EVIDENCE_WEIGHT", "0.7"))
CONFIDENCE_VOLUME_WEIGHT: float = float(os.getenv("CONFIDENCE_VOLUME_WEIGHT", "0.3"))
FINAL_SCORE_DAMP_BASE: float = float(os.getenv("FINAL_SCORE_DAMP_BASE", "0.6"))
FINAL_SCORE_DAMP_SCALE: float = float(os.getenv("FINAL_SCORE_DAMP_SCALE", "0.4"))

# Selective clinic-level Gemini validation for near-threshold decisions.
ENABLE_GRAY_ZONE_VALIDATION: bool = os.getenv("ENABLE_GRAY_ZONE_VALIDATION", "1").strip().lower() in {
	"1", "true", "yes", "on"
}
GRAY_ZONE_VALIDATION_BAND: float = float(os.getenv("GRAY_ZONE_VALIDATION_BAND", "0.08"))
