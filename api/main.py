from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.routers import runs, clinics, drafts, settings as settings_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    from scheduler.scheduler import start_scheduler, stop_scheduler
    start_scheduler()
    yield
    stop_scheduler()


app = FastAPI(title="LavenderHealth Pipeline", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(runs.router)
app.include_router(clinics.router)
app.include_router(drafts.router)
app.include_router(settings_router.router)
