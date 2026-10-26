import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Depends
from sqlalchemy.orm import Session
from fastapi.middleware.cors import CORSMiddleware

from db.db import engine, get_db, Base, SessionLocal
from db.models import Test
from routers import disasters, alerts, reports, history, facilities, dashboard, auth, predictions
from services.auth import seed_default_users
from services.prediction_scheduler import start_scheduler, stop_scheduler

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup / shutdown lifecycle for the FastAPI app."""
    # -- Startup --
    logger.info("Starting background prediction scheduler ...")
    try:
        start_scheduler()
    except Exception as exc:
        logger.warning("Could not start prediction scheduler: %s", exc)

    yield  # App is running

    # -- Shutdown --
    logger.info("Stopping background prediction scheduler ...")
    stop_scheduler()


app = FastAPI(
    title="Weather Watch - Disaster Response Backend",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

Base.metadata.create_all(bind=engine)

# Seed initial default users if not present
try:
    with SessionLocal() as db_session:
        seed_default_users(db_session)
except Exception as e:
    print("Default user seeding note:", e)

app.include_router(auth.router)
app.include_router(disasters.router)
app.include_router(alerts.router)
app.include_router(reports.router)
app.include_router(history.router)
app.include_router(facilities.router)
app.include_router(dashboard.router)
app.include_router(predictions.router)

@app.post("/test")
def add_test(name: str, db: Session = Depends(get_db)):
    data = Test(name=name)

    db.add(data)
    db.commit()
    db.refresh(data)

    return data

@app.get("/test")
def get_test(db: Session = Depends(get_db)):
    return db.query(Test).all()
