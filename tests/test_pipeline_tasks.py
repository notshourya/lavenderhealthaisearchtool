import pytest
from unittest.mock import MagicMock, patch, AsyncMock
import uuid

from db.models import CityRunStatus, ClinicStatus


def make_db_run(session):
    from db.models import CityRun, TriggeredBy
    run = CityRun(city="Houston", state="TX", triggered_by=TriggeredBy.CLI, max_reviews=200)
    session.add(run)
    session.commit()
    return run


@pytest.fixture
def db_session():
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    from db.models import Base
    engine = create_engine("postgresql://lavender:lavender@localhost:5433/lavenderhealth_test")
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.rollback()
    session.close()


def test_scrape_city_task_updates_run_status(db_session):
    from pipeline.tasks import scrape_city_task
    run = make_db_run(db_session)

    mock_clinic = MagicMock()
    mock_clinic.name = "Test Dental"
    mock_clinic.address = "123 Main"
    mock_clinic.city = "Houston"
    mock_clinic.state = "TX"
    mock_clinic.zip = None
    mock_clinic.phone = None
    mock_clinic.website = None
    mock_clinic.google_maps_url = "https://maps.google.com/test"
    mock_clinic.place_id = f"ChIJ_TASK_TEST_{uuid.uuid4().hex[:8]}"
    mock_clinic.overall_rating = 3.5
    mock_clinic.total_reviews = 42
    mock_clinic.reviews = []

    with patch("scraper.playwright_scraper.scrape_city", new_callable=MagicMock, return_value=[mock_clinic]):
        with patch("pipeline.tasks.asyncio.run", side_effect=lambda value: value):
            with patch("pipeline.tasks.SessionLocal") as mock_sl:
                mock_sl.return_value.__enter__ = MagicMock(return_value=db_session)
                mock_sl.return_value.__exit__ = MagicMock(side_effect=lambda *args: db_session.commit(), return_value=False)
                scrape_city_task(str(run.id))

    db_session.refresh(run)
    assert run.total_clinics_found == 1


def test_filter_clinics_task_marks_qualified(db_session):
    from pipeline.tasks import filter_clinics_task
    from db.models import CityRun, Clinic, Review, TriggeredBy
    from scraper.playwright_scraper import ClinicReviewScrapeResult, ReviewData

    run = CityRun(city="Houston", state="TX", triggered_by=TriggeredBy.CLI)
    db_session.add(run)
    db_session.flush()

    clinic = Clinic(
        city_run_id=run.id,
        name="Complaint Dental",
        city="Houston",
        state="TX",
        google_maps_url="https://maps.google.com/c",
        place_id=f"ChIJ_FILTER_{uuid.uuid4().hex[:8]}",
        total_reviews=25,
    )
    db_session.add(clinic)
    db_session.flush()

    # Strong enough to qualify without clinic-level Gemini.
    db_session.add(Review(clinic_id=clinic.id, author="Jane", text="Insurance claim was denied after 6 months."))
    db_session.add(Review(clinic_id=clinic.id, author="Bob", text="They refused my reimbursement request."))
    db_session.add(Review(clinic_id=clinic.id, author="Chris", text="Another insurance claim was denied."))
    db_session.commit()

    with patch("pipeline.tasks.classify_reviews") as mock_classify:
        mock_verdict = MagicMock()
        from filter.llm_filter import ReviewVerdict
        mock_verdict.verdict = ReviewVerdict.CONFIRMED
        mock_verdict.confidence = 0.95
        mock_verdict.reasoning = "Clear insurance complaint."
        mock_classify.return_value = [mock_verdict, mock_verdict, mock_verdict]

        deep_result = ClinicReviewScrapeResult(
            overall_rating=4.1,
            total_reviews=25,
            reviews=[
                ReviewData(author="Jane", rating=1, text="Insurance claim was denied after 6 months.", date=None),
                ReviewData(author="Bob", rating=1, text="They refused my reimbursement request.", date=None),
                ReviewData(author="Chris", rating=1, text="Another insurance claim was denied.", date=None),
            ],
        )

        with patch("pipeline.tasks._scrape_clinic_reviews_sync", return_value=deep_result):
            with patch("pipeline.tasks.SessionLocal") as mock_sl:
                mock_sl.return_value.__enter__ = MagicMock(return_value=db_session)
                mock_sl.return_value.__exit__ = MagicMock(return_value=False)
                filter_clinics_task(str(run.id))

    db_session.refresh(clinic)
    assert clinic.status == ClinicStatus.QUALIFIED


def test_filter_clinics_task_filters_low_complaint_rate_clinic(db_session):
    from pipeline.tasks import filter_clinics_task
    from filter.llm_filter import ReviewVerdict
    from db.models import CityRun, Clinic, Review, TriggeredBy
    from scraper.playwright_scraper import ClinicReviewScrapeResult, ReviewData

    run = CityRun(city="Houston", state="TX", triggered_by=TriggeredBy.CLI)
    db_session.add(run)
    db_session.flush()

    clinic = Clinic(
        city_run_id=run.id,
        name="Large Practice Dental",
        city="Houston",
        state="TX",
        google_maps_url="https://maps.google.com/c",
        place_id=f"ChIJ_FILTER_LOW_{uuid.uuid4().hex[:8]}",
        total_reviews=200,
    )
    db_session.add(clinic)
    db_session.flush()

    db_session.add(Review(clinic_id=clinic.id, text="Insurance claim was denied after 6 months."))
    db_session.add(Review(clinic_id=clinic.id, text="They refused my reimbursement request."))
    db_session.commit()

    with patch("pipeline.tasks.classify_reviews") as mock_classify:
        mock_verdict = MagicMock()
        mock_verdict.verdict = ReviewVerdict.CONFIRMED
        mock_verdict.confidence = 0.92
        mock_verdict.reasoning = "Clear insurance complaint."
        mock_classify.return_value = [mock_verdict, mock_verdict]

        deep_result = ClinicReviewScrapeResult(
            overall_rating=4.6,
            total_reviews=200,
            reviews=[
                ReviewData(author=None, rating=1, text="Insurance claim was denied after 6 months.", date=None),
                ReviewData(author=None, rating=1, text="They refused my reimbursement request.", date=None),
            ],
        )

        with patch("pipeline.tasks._scrape_clinic_reviews_sync", return_value=deep_result):
            with patch("pipeline.tasks.SessionLocal") as mock_sl:
                mock_sl.return_value.__enter__ = MagicMock(return_value=db_session)
                mock_sl.return_value.__exit__ = MagicMock(return_value=False)
                with patch("pipeline.tasks_enrichment.enrich_clinics_task.delay") as mock_enrich_delay:
                    filter_clinics_task(str(run.id))
                    mock_enrich_delay.assert_called_once()

    db_session.refresh(clinic)
    assert clinic.status == ClinicStatus.FILTERED_OUT


def test_filter_clinics_task_uses_heuristic_shortcut_for_obvious_target(db_session):
    from pipeline.tasks import filter_clinics_task
    from filter.llm_filter import ReviewVerdict
    from db.models import CityRun, Clinic, Review, TriggeredBy
    from scraper.playwright_scraper import ClinicReviewScrapeResult, ReviewData

    run = CityRun(city="Houston", state="TX", triggered_by=TriggeredBy.CLI)
    db_session.add(run)
    db_session.flush()

    clinic = Clinic(
        city_run_id=run.id,
        name="Obvious Target Dental",
        city="Houston",
        state="TX",
        google_maps_url="https://maps.google.com/c",
        place_id=f"ChIJ_FILTER_OBVIOUS_{uuid.uuid4().hex[:8]}",
        total_reviews=40,
    )
    db_session.add(clinic)
    db_session.flush()

    db_session.add(Review(clinic_id=clinic.id, author="Jane", text="Insurance claim was denied after months."))
    db_session.add(Review(clinic_id=clinic.id, author="Bob", text="My reimbursement never arrived."))
    db_session.add(Review(clinic_id=clinic.id, author="Chris", text="Another claim denied by insurance."))
    db_session.commit()

    with patch("pipeline.tasks.classify_reviews") as mock_classify:
        mock_verdict = MagicMock()
        mock_verdict.verdict = ReviewVerdict.CONFIRMED
        mock_verdict.confidence = 0.95
        mock_verdict.reasoning = "Clear insurance complaint."
        mock_classify.return_value = [mock_verdict, mock_verdict, mock_verdict]

        deep_result = ClinicReviewScrapeResult(
            overall_rating=4.2,
            total_reviews=40,
            reviews=[
                ReviewData(author="Jane", rating=1, text="Insurance claim was denied after months.", date=None),
                ReviewData(author="Bob", rating=1, text="My reimbursement never arrived.", date=None),
                ReviewData(author="Chris", rating=1, text="Another claim denied by insurance.", date=None),
            ],
        )

        with patch("pipeline.tasks._scrape_clinic_reviews_sync", return_value=deep_result):
            with patch("pipeline.tasks.analyze_clinic") as mock_analyze:
                with patch("pipeline.tasks.SessionLocal") as mock_sl:
                    mock_sl.return_value.__enter__ = MagicMock(return_value=db_session)
                    mock_sl.return_value.__exit__ = MagicMock(return_value=False)
                    filter_clinics_task(str(run.id))

    db_session.refresh(clinic)
    assert clinic.status == ClinicStatus.QUALIFIED
    mock_analyze.assert_not_called()


def test_filter_clinics_task_handles_quota_exhaustion_without_crashing(db_session):
    from pipeline.tasks import filter_clinics_task
    from db.models import CityRun, Clinic, Review, TriggeredBy
    from scraper.playwright_scraper import ClinicReviewScrapeResult, ReviewData

    run = CityRun(city="Houston", state="TX", triggered_by=TriggeredBy.CLI)
    db_session.add(run)
    db_session.flush()

    clinic = Clinic(
        city_run_id=run.id,
        name="Quota Limited Dental",
        city="Houston",
        state="TX",
        google_maps_url="https://maps.google.com/c",
        place_id=f"ChIJ_FILTER_QUOTA_{uuid.uuid4().hex[:8]}",
        total_reviews=20,
    )
    db_session.add(clinic)
    db_session.flush()

    db_session.add(Review(clinic_id=clinic.id, text="Insurance claim denied after treatment."))
    db_session.add(Review(clinic_id=clinic.id, text="Reimbursement never arrived from insurance."))
    db_session.commit()

    deep_result = ClinicReviewScrapeResult(
        overall_rating=4.0,
        total_reviews=20,
        reviews=[
            ReviewData(author="A", rating=1, text="Insurance claim denied after treatment.", date=None),
            ReviewData(author="B", rating=1, text="Reimbursement never arrived from insurance.", date=None),
        ],
    )

    with patch("pipeline.tasks.classify_reviews", side_effect=Exception("429 RESOURCE_EXHAUSTED")):
        with patch("pipeline.tasks._scrape_clinic_reviews_sync", return_value=deep_result):
            with patch("pipeline.tasks.SessionLocal") as mock_sl:
                mock_sl.return_value.__enter__ = MagicMock(return_value=db_session)
                mock_sl.return_value.__exit__ = MagicMock(return_value=False)
                filter_clinics_task(str(run.id))

    db_session.refresh(clinic)
    assert clinic.status == ClinicStatus.FILTERED_OUT


def test_filter_clinics_task_skips_stage1_quota_exhaustion_without_retry(db_session):
    from pipeline.tasks import filter_clinics_task
    from db.models import CityRun, Clinic, Review, TriggeredBy

    run = CityRun(city="Houston", state="TX", triggered_by=TriggeredBy.CLI)
    db_session.add(run)
    db_session.flush()

    clinic = Clinic(
        city_run_id=run.id,
        name="Stage One Quota Dental",
        city="Houston",
        state="TX",
        google_maps_url="https://maps.google.com/c",
        place_id=f"ChIJ_FILTER_STAGE1_{uuid.uuid4().hex[:8]}",
        total_reviews=18,
    )
    db_session.add(clinic)
    db_session.flush()

    db_session.add(Review(clinic_id=clinic.id, text="Friendly staff and clean office."))
    db_session.add(Review(clinic_id=clinic.id, text="Great cleaning and quick service."))
    db_session.commit()

    with patch("pipeline.tasks.qualifies_for_llm", return_value=False):
        with patch("pipeline.tasks.classify_reviews", side_effect=Exception("429 RESOURCE_EXHAUSTED")):
            with patch("pipeline.tasks._scrape_clinic_reviews_sync") as mock_deep_scrape:
                with patch("pipeline.tasks.filter_clinics_task.retry") as mock_retry:
                    with patch("pipeline.tasks.SessionLocal") as mock_sl:
                        mock_sl.return_value.__enter__ = MagicMock(return_value=db_session)
                        mock_sl.return_value.__exit__ = MagicMock(return_value=False)
                        filter_clinics_task(str(run.id))

    db_session.refresh(clinic)
    assert clinic.status == ClinicStatus.FILTERED_OUT
    mock_deep_scrape.assert_not_called()
    mock_retry.assert_not_called()


def test_filter_clinics_task_keeps_screening_promoted_reviews_without_keyword_hits(db_session):
    from pipeline.tasks import filter_clinics_task
    from filter.llm_filter import ReviewVerdict
    from db.models import CityRun, Clinic, Review, TriggeredBy
    from scraper.playwright_scraper import ClinicReviewScrapeResult, ReviewData

    run = CityRun(city="Houston", state="TX", triggered_by=TriggeredBy.CLI)
    db_session.add(run)
    db_session.flush()

    clinic = Clinic(
        city_run_id=run.id,
        name="Paraphrase Dental",
        city="Houston",
        state="TX",
        google_maps_url="https://maps.google.com/c",
        place_id=f"ChIJ_FILTER_PARAPHRASE_{uuid.uuid4().hex[:8]}",
        total_reviews=20,
    )
    db_session.add(clinic)
    db_session.flush()

    # Intentionally avoid direct keyword phrases used in keyword_filter.py.
    db_session.add(Review(clinic_id=clinic.id, author="Jane", text="My payer kept bouncing the paperwork and nothing got reimbursed."))
    db_session.add(Review(clinic_id=clinic.id, author="Bob", text="Coverage rules changed and we were billed anyway."))
    db_session.add(Review(clinic_id=clinic.id, author="Chris", text="The carrier said benefits were restricted this month."))
    db_session.commit()

    deep_result = ClinicReviewScrapeResult(
        overall_rating=4.1,
        total_reviews=20,
        reviews=[
            ReviewData(author="Jane", rating=1, text="My payer kept bouncing the paperwork and nothing got reimbursed.", date=None),
            ReviewData(author="Bob", rating=1, text="Coverage rules changed and we were billed anyway.", date=None),
            ReviewData(author="Chris", rating=1, text="The carrier said benefits were restricted this month.", date=None),
        ],
    )

    screening_verdict = MagicMock()
    screening_verdict.verdict = ReviewVerdict.INSURER
    screening_verdict.confidence = 0.8
    screening_verdict.reasoning = "Likely insurer-friction complaint."

    with patch("pipeline.tasks.qualifies_for_llm", return_value=False):
        with patch("pipeline.tasks.classify_reviews", side_effect=[[screening_verdict] * 3, [screening_verdict] * 3]):
            with patch("pipeline.tasks._scrape_clinic_reviews_sync", return_value=deep_result):
                with patch("pipeline.tasks.analyze_clinic") as mock_analyze:
                    mock_analyze.return_value = MagicMock(is_target=True, confidence=0.9, severity="MEDIUM", pattern="pattern")
                    with patch("pipeline.tasks.SessionLocal") as mock_sl:
                        mock_sl.return_value.__enter__ = MagicMock(return_value=db_session)
                        mock_sl.return_value.__exit__ = MagicMock(return_value=False)
                        filter_clinics_task(str(run.id))

    db_session.refresh(clinic)
    assert clinic.status == ClinicStatus.QUALIFIED
