from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

_scheduler = BackgroundScheduler(timezone="UTC")


def start_scheduler() -> None:
    if not _scheduler.running:
        _scheduler.start()


def stop_scheduler() -> None:
    if _scheduler.running:
        _scheduler.shutdown(wait=False)


def add_city_schedule(city: str, state: str, cron: str, max_reviews: int = 0) -> str:
    job_id = f"{city.lower()}_{state.lower()}"

    def run_pipeline():
        import config
        from sqlalchemy import create_engine
        from sqlalchemy.orm import sessionmaker
        from db.models import CityRun, TriggeredBy
        from pipeline.tasks import scrape_city_task
        engine = create_engine(config.DATABASE_URL)
        Session = sessionmaker(bind=engine)
        with Session() as db:
            run = CityRun(city=city, state=state, max_reviews=max_reviews, triggered_by=TriggeredBy.SCHEDULER)
            db.add(run)
            db.commit()
            scrape_city_task.delay(str(run.id))

    parts = cron.split()
    trigger = CronTrigger(minute=parts[0], hour=parts[1], day=parts[2], month=parts[3], day_of_week=parts[4])
    _scheduler.add_job(run_pipeline, trigger=trigger, id=job_id, replace_existing=True)
    return job_id


def remove_schedule(job_id: str) -> None:
    if _scheduler.get_job(job_id):
        _scheduler.remove_job(job_id)


def list_schedules() -> list[dict]:
    return [
        {"job_id": j.id, "next_run": str(j.next_run_time) if j.next_run_time else None, "trigger": str(j.trigger)}
        for j in _scheduler.get_jobs()
    ]
