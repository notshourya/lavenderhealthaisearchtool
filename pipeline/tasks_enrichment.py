from contextlib import contextmanager
from datetime import datetime, timezone

from db.models import (
    CityRun, Clinic, Contact, EmailDraft,
    ClinicStatus, DraftStatus, CityRunStatus, FaultParty,
)
from enrichment.apollo_client import find_clinic_contacts
from drafter.email_drafter import draft_outreach_email
from pipeline.celery_app import celery_app
import config


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


@contextmanager
def SessionLocal():
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    engine = create_engine(config.DATABASE_URL, pool_pre_ping=True)
    Session = sessionmaker(bind=engine)
    db = Session()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


@celery_app.task(bind=True, max_retries=5, default_retry_delay=120, rate_limit="30/m")
def enrich_clinics_task(self, city_run_id: str) -> None:
    with SessionLocal() as db:
        clinics = (
            db.query(Clinic)
            .filter_by(city_run_id=city_run_id, status=ClinicStatus.QUALIFIED)
            .all()
        )

        enriched_count = 0
        for clinic in clinics:
            try:
                contacts = find_clinic_contacts(clinic.name, clinic.city, clinic.state, clinic.website)
            except Exception as exc:
                raise self.retry(exc=exc)

            if not contacts:
                continue  # Stay at QUALIFIED — surfaced in dashboard

            for contact_data in contacts[:3]:
                existing_contact = (
                    db.query(Contact)
                    .filter_by(clinic_id=clinic.id, email=contact_data.email)
                    .first()
                )
                if existing_contact:
                    continue

                db.add(Contact(
                    clinic_id=clinic.id,
                    email=contact_data.email,
                    first_name=contact_data.first_name,
                    last_name=contact_data.last_name,
                    title=contact_data.title,
                    confidence_score=contact_data.confidence_score,
                ))
            clinic.status = ClinicStatus.ENRICHED
            enriched_count += 1

        run = db.query(CityRun).filter_by(id=city_run_id).first()
        if run:
            run.total_enriched = enriched_count

    draft_emails_task.delay(city_run_id)


@celery_app.task(bind=True, max_retries=3, default_retry_delay=30)
def draft_emails_task(self, city_run_id: str) -> None:
    with SessionLocal() as db:
        clinics = (
            db.query(Clinic)
            .filter_by(city_run_id=city_run_id, status=ClinicStatus.ENRICHED)
            .all()
        )

        drafted_count = 0
        for clinic in clinics:
            if not clinic.contacts:
                continue

            contact = clinic.contacts[0]
            flagged_excerpts = [
                r.text
                for r in clinic.reviews
                if r.fault_party == FaultParty.INSURER or r.insurance_flag
            ][:3]

            try:
                result = draft_outreach_email(
                    clinic_name=clinic.name,
                    contact_first_name=contact.first_name,
                    flagged_review_excerpts=flagged_excerpts,
                )
            except Exception as exc:
                raise self.retry(exc=exc)

            db.add(EmailDraft(
                clinic_id=clinic.id,
                contact_id=contact.id,
                subject=result.subject,
                body=result.body,
                subject_variants=result.subject_variants,
            ))
            clinic.status = ClinicStatus.DRAFTED
            drafted_count += 1

        run = db.query(CityRun).filter_by(id=city_run_id).first()
        if run:
            run.total_drafted = drafted_count
            run.status = CityRunStatus.COMPLETED
            run.completed_at = utcnow()
