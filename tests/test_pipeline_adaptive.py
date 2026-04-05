from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import patch

from pipeline.tasks import (
    _adaptive_review_limits,
    _effective_insurer_signal,
    _has_intelligence_screening_signal,
    _needs_gray_zone_validation,
    _dominant_issue_category,
    _passes_recent_cluster_override,
    _qualification_scores,
    _qualification_threshold_for_profile,
    _recent_month_cluster_peak,
    _run_adaptive_deep_scrape,
    _select_intelligence_screening_reviews,
    _unique_named_reviewer_count,
)
from filter.llm_filter import ReviewVerdict
from scraper.playwright_scraper import ClinicReviewScrapeResult, ReviewData


def _result(*texts: str) -> ClinicReviewScrapeResult:
    return ClinicReviewScrapeResult(
        overall_rating=4.5,
        total_reviews=500,
        reviews=[ReviewData(author=None, rating=1, text=text, date=None) for text in texts],
    )


def test_adaptive_review_limits_are_unique_and_bounded():
    assert _adaptive_review_limits(20) == [20]
    assert _adaptive_review_limits(80) == [25, 80]
    assert _adaptive_review_limits(200) == [25, 100, 200]
    assert _adaptive_review_limits(0) == [25, 100, 0]


def test_select_intelligence_screening_reviews_prefers_low_rated_recent_reviews():
    now = datetime.now(timezone.utc)
    reviews = [
        SimpleNamespace(rating=5, date=now - timedelta(days=1)),
        SimpleNamespace(rating=2, date=now - timedelta(days=5)),
        SimpleNamespace(rating=2, date=now - timedelta(days=1)),
        SimpleNamespace(rating=1, date=now - timedelta(days=2)),
    ]

    selected = _select_intelligence_screening_reviews(reviews, limit=3)

    assert [review.rating for review in selected] == [1, 2, 2]
    assert selected[0].date == now - timedelta(days=2)


def test_has_intelligence_screening_signal_accepts_clear_insurer_pattern():
    classifications = [
        SimpleNamespace(verdict=ReviewVerdict.INSURER, confidence=0.75),
        SimpleNamespace(verdict=ReviewVerdict.NO, confidence=0.9),
    ]

    assert _has_intelligence_screening_signal(classifications) is True


def test_has_intelligence_screening_signal_rejects_weak_noise():
    classifications = [
        SimpleNamespace(verdict=ReviewVerdict.SHARED, confidence=0.5),
        SimpleNamespace(verdict=ReviewVerdict.NO, confidence=0.8),
    ]

    assert _has_intelligence_screening_signal(classifications) is False


def test_adaptive_deep_scrape_stops_after_stage_one_if_no_signal():
    clinic = SimpleNamespace(id="clinic-1", google_maps_url="https://maps.google.com/test")

    with patch("pipeline.tasks._scrape_clinic_reviews_sync", return_value=_result("Friendly staff and quick cleaning.")) as mock_run:
        result, used_limit, keyword_review_count = _run_adaptive_deep_scrape(clinic, 200)

    assert used_limit == 25
    assert keyword_review_count == 0
    assert len(result.reviews) == 1
    assert mock_run.call_count == 1


def test_adaptive_deep_scrape_stops_after_stage_two_if_signal_is_not_strong_enough():
    clinic = SimpleNamespace(id="clinic-1", google_maps_url="https://maps.google.com/test")

    with patch(
        "pipeline.tasks._scrape_clinic_reviews_sync",
        side_effect=[
            _result("Insurance claim denied."),
            _result("Insurance claim denied.", "Friendly staff."),
        ],
    ) as mock_run:
        result, used_limit, keyword_review_count = _run_adaptive_deep_scrape(clinic, 200)

    assert used_limit == 100
    assert keyword_review_count == 1
    assert len(result.reviews) == 2
    assert mock_run.call_count == 2


def test_adaptive_deep_scrape_reaches_final_stage_when_signal_remains_strong():
    clinic = SimpleNamespace(id="clinic-1", google_maps_url="https://maps.google.com/test")

    with patch(
        "pipeline.tasks._scrape_clinic_reviews_sync",
        side_effect=[
            _result("Insurance claim denied."),
            _result("Insurance claim denied.", "Coverage denied again."),
            _result("Insurance claim denied.", "Coverage denied again.", "Reimbursement never arrived."),
        ],
    ) as mock_run:
        result, used_limit, keyword_review_count = _run_adaptive_deep_scrape(clinic, 200)

    assert used_limit == 200
    assert keyword_review_count == 3
    assert len(result.reviews) == 3
    assert mock_run.call_count == 3


def test_recent_cluster_override_triggers_for_fresh_insurer_reviews():
    now = datetime.now(timezone.utc)
    insurer_reviews = [
        SimpleNamespace(author="Jane", issue_category="claim_denial", date=now - timedelta(days=10)),
        SimpleNamespace(author="Bob", issue_category="claim_denial", date=now - timedelta(days=20)),
        SimpleNamespace(author="Chris", issue_category="claim_denial", date=now - timedelta(days=30)),
    ]
    clinic_fault_reviews = [
        SimpleNamespace(author="Dana", issue_category="billing_error", date=now - timedelta(days=15)),
    ]

    assert _passes_recent_cluster_override(insurer_reviews, clinic_fault_reviews) is True


def test_recent_cluster_override_does_not_trigger_for_old_reviews():
    now = datetime.now(timezone.utc)
    insurer_reviews = [
        SimpleNamespace(date=now - timedelta(days=250)),
        SimpleNamespace(date=now - timedelta(days=260)),
        SimpleNamespace(date=now - timedelta(days=270)),
    ]
    clinic_fault_reviews = []

    assert _passes_recent_cluster_override(insurer_reviews, clinic_fault_reviews) is False


def test_unique_named_reviewer_count_normalizes_names():
    reviews = [
        SimpleNamespace(author="Jane D", issue_category="claim_denial", date=None),
        SimpleNamespace(author="  jane   d ", issue_category="claim_denial", date=None),
        SimpleNamespace(author="Bob", issue_category="claim_denial", date=None),
        SimpleNamespace(author=None, issue_category="claim_denial", date=None),
    ]
    assert _unique_named_reviewer_count(reviews) == 2


def test_dominant_issue_category_picks_most_common():
    reviews = [
        SimpleNamespace(author="a", issue_category="claim_denial", date=None),
        SimpleNamespace(author="b", issue_category="claim_denial", date=None),
        SimpleNamespace(author="c", issue_category="coverage_confusion", date=None),
    ]
    assert _dominant_issue_category(reviews) == ("claim_denial", 2)


def test_recent_month_cluster_peak_counts_dense_month():
    reviews = [
        SimpleNamespace(date=datetime(2026, 4, 1, tzinfo=timezone.utc)),
        SimpleNamespace(date=datetime(2026, 4, 10, tzinfo=timezone.utc)),
        SimpleNamespace(date=datetime(2026, 3, 1, tzinfo=timezone.utc)),
    ]
    assert _recent_month_cluster_peak(reviews, 180, now=datetime(2026, 4, 20, tzinfo=timezone.utc)) == 2


def test_effective_insurer_signal_counts_shared_partially():
    assert _effective_insurer_signal(2, 4) == 4.0


def test_qualification_threshold_profile_fallback_is_balanced():
    assert _qualification_threshold_for_profile("unknown") == _qualification_threshold_for_profile("balanced")


def test_qualification_scores_increase_with_stronger_signal():
    weaker = _qualification_scores(
        insurer_count=1,
        shared_count=1,
        total_known=80,
        complaint_rate=0.0125,
        recent_insurer_count=1,
        recent_cluster_peak=1,
        unique_insurer_reviewers=1,
    )
    stronger = _qualification_scores(
        insurer_count=4,
        shared_count=2,
        total_known=80,
        complaint_rate=0.05,
        recent_insurer_count=3,
        recent_cluster_peak=2,
        unique_insurer_reviewers=3,
    )

    assert stronger["base_score"] > weaker["base_score"]
    assert stronger["final_score"] > weaker["final_score"]


def test_gray_zone_validation_gate_triggers_near_threshold():
    assert _needs_gray_zone_validation(0.57, 0.55) is True
