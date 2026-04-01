import uuid as uuid_mod
from contextlib import contextmanager
from datetime import datetime, timezone

import click

import config
from db.models import CityRun, EmailDraft, TriggeredBy
from pipeline.tasks import scrape_city_task


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


@click.group()
def cli():
    """LavenderHealth pipeline CLI."""
    pass


@cli.command()
@click.option("--city", required=True, help="City name (e.g. Houston)")
@click.option("--state", required=True, help="2-letter state code (e.g. TX)")
@click.option("--max-reviews", default=200, show_default=True, help="Max reviews per clinic")
def scrape(city: str, state: str, max_reviews: int):
    """Trigger a new city scrape + filter + enrich + draft pipeline run."""
    with SessionLocal() as db:
        run = CityRun(
            city=city,
            state=state.upper(),
            max_reviews=max_reviews,
            triggered_by=TriggeredBy.CLI,
        )
        db.add(run)
        db.commit()
        run_id = str(run.id)

    scrape_city_task.delay(run_id)
    click.echo(f"Run started for {city}, {state}.")
    click.echo(f"Run ID: {run_id}")
    click.echo("Monitor progress with: python cli/run.py status --run-id " + run_id)


@cli.command()
@click.option("--run-id", required=True, help="UUID of the city run")
def status(run_id: str):
    """Check the status of a pipeline run."""
    with SessionLocal() as db:
        run = db.query(CityRun).filter_by(id=run_id).first()
        if not run:
            click.echo(f"Run {run_id} not found.")
            return

        click.echo(f"City:           {run.city}, {run.state}")
        click.echo(f"Status:         {run.status.value}")
        click.echo(f"Triggered by:   {run.triggered_by.value}")
        click.echo(f"Created at:     {run.created_at.strftime('%Y-%m-%d %H:%M UTC')}")
        if run.completed_at:
            click.echo(f"Completed at:   {run.completed_at.strftime('%Y-%m-%d %H:%M UTC')}")
        click.echo(f"Clinics found:  {run.total_clinics_found}")
        click.echo(f"Qualified:      {run.total_qualified}")
        click.echo(f"Enriched:       {run.total_enriched}")
        click.echo(f"Drafted:        {run.total_drafted}")


@cli.command()
@click.option("--run-id", required=True, help="UUID of the city run")
@click.option("--format", "fmt", default="pdf", type=click.Choice(["html", "pdf"]), show_default=True)
@click.option("--output-dir", default="./exports", show_default=True)
def export(run_id: str, fmt: str, output_dir: str):
    """Export all approved email drafts for a run."""
    import os
    from api.export import render_draft_html, render_draft_pdf

    os.makedirs(output_dir, exist_ok=True)

    with SessionLocal() as db:
        run = db.query(CityRun).filter_by(id=run_id).first()
        if not run:
            click.echo(f"Run {run_id} not found.")
            return

        drafts = (
            db.query(EmailDraft)
            .join(EmailDraft.clinic)
            .filter(EmailDraft.status == "approved")
            .all()
        )

        if not drafts:
            click.echo("No approved drafts found for this run.")
            return

        count = 0
        for draft in drafts:
            clinic_name = draft.clinic.name if draft.clinic else "Clinic"
            html = render_draft_html(
                clinic_name=clinic_name,
                subject=draft.subject,
                body=draft.body,
            )
            filename = f"draft_{draft.id}.{fmt}"
            filepath = os.path.join(output_dir, filename)

            if fmt == "pdf":
                content = render_draft_pdf(html)
                with open(filepath, "wb") as f:
                    f.write(content)
            else:
                with open(filepath, "w") as f:
                    f.write(html)

            draft.exported_at = datetime.now(timezone.utc)
            draft.export_format = fmt
            count += 1

        click.echo(f"Exported {count} drafts to {output_dir}/")


if __name__ == "__main__":
    cli()
