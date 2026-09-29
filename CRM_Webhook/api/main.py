from contextlib import asynccontextmanager
import logging

from fastapi import FastAPI

from api.routes.webhook import router as webhook_router
from database.connection import create_tables
from database.retention import purge_records_outside_current_day
from shared.logging import configure_logging

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(_: FastAPI):
    configure_logging()
    create_tables()
    removed = purge_records_outside_current_day()
    logger.info(
        "Limpeza diária concluída leads=%s inscricoes=%s events=%s",
        removed["leads"],
        removed["inscricoes"],
        removed["events"],
    )
    yield


app = FastAPI(title="CRM Webhook API", version="1.0.0", lifespan=lifespan)
app.include_router(webhook_router)


@app.get("/", include_in_schema=False)
def root() -> dict[str, str]:
    return {"status": "online"}


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
