from functools import lru_cache

from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session

from shared.config import get_settings


@lru_cache
def get_engine() -> Engine:
    url = get_settings().database_url
    kwargs = {"pool_pre_ping": True}
    if url.startswith("sqlite"):
        kwargs["connect_args"] = {"check_same_thread": False}
    return create_engine(url, **kwargs)


def get_session() -> Session:
    return Session(get_engine())


def create_tables() -> None:
    from database.models import Base

    Base.metadata.create_all(get_engine())
