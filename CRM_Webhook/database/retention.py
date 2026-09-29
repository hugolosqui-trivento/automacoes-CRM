from datetime import UTC, datetime, time, timedelta
from zoneinfo import ZoneInfo

from sqlalchemy import and_, delete, func, or_, select
from sqlalchemy.sql.elements import ColumnElement

from database.connection import get_session
from database.models import Inscricao, Lead, WebhookEvent

BUSINESS_TIMEZONE = ZoneInfo("America/Sao_Paulo")


def current_day_utc_bounds(
    now: datetime | None = None,
) -> tuple[datetime, datetime]:
    reference = now or datetime.now(UTC)
    if reference.tzinfo is None:
        raise ValueError("now deve conter informação de fuso horário")

    local_now = reference.astimezone(BUSINESS_TIMEZONE)
    local_start = datetime.combine(local_now.date(), time.min, BUSINESS_TIMEZONE)
    return (
        local_start.astimezone(UTC),
        (local_start + timedelta(days=1)).astimezone(UTC),
    )


def is_from_current_day(
    created_at: object,
    received_at: object,
    day_start: datetime,
    day_end: datetime,
) -> ColumnElement[bool]:
    effective_at = func.coalesce(created_at, received_at)
    return and_(effective_at >= day_start, effective_at < day_end)


def purge_records_outside_current_day(
    now: datetime | None = None,
) -> dict[str, int]:
    """Remove dados fora do dia corrente de São Paulo em uma transação."""
    day_start, day_end = current_day_utc_bounds(now)
    lead_is_old = ~is_from_current_day(
        Lead.created_at, Lead.received_at, day_start, day_end
    )
    inscricao_is_old = or_(
        ~is_from_current_day(
            Inscricao.created_at, Inscricao.received_at, day_start, day_end
        ),
        Inscricao.lead_id.in_(select(Lead.lead_id).where(lead_is_old)),
    )
    event_is_old = or_(
        WebhookEvent.received_at < day_start,
        WebhookEvent.received_at >= day_end,
    )

    with get_session() as session, session.begin():
        inscricoes = session.execute(
            delete(Inscricao)
            .where(inscricao_is_old)
            .execution_options(synchronize_session=False)
        )
        leads = session.execute(
            delete(Lead)
            .where(lead_is_old)
            .execution_options(synchronize_session=False)
        )
        events = session.execute(
            delete(WebhookEvent)
            .where(event_is_old)
            .execution_options(synchronize_session=False)
        )

    return {
        "inscricoes": int(inscricoes.rowcount or 0),
        "leads": int(leads.rowcount or 0),
        "events": int(events.rowcount or 0),
    }
