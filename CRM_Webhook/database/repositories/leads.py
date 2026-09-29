from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

from api.schemas.lead import NormalizedEvent
from database.connection import get_session
from database.models import Lead, WebhookEvent
from database.retention import current_day_utc_bounds, is_from_current_day


def save_event_and_lead(event: NormalizedEvent) -> bool:
    now = datetime.now(UTC)
    try:
        with get_session() as session, session.begin():
            existing = session.scalar(
                select(WebhookEvent).where(WebhookEvent.event_id == event.event_id)
            )
            if existing and existing.status == "processed":
                return True
            if existing is None:
                session.add(
                    WebhookEvent(
                        event_id=event.event_id,
                        event_type=event.event_type,
                        source=event.source,
                        lead_id=event.lead_id,
                        payload=event.payload,
                        received_at=now,
                        status="received",
                    )
                )
    except IntegrityError:
        # Outra requisição gravou o mesmo event_id simultaneamente.
        return True

    try:
        with get_session() as session, session.begin():
            lead = session.get(Lead, event.lead_id)
            values = {
                "nome": event.nome,
                "email": event.email,
                "telefone": event.telefone,
                "unidade": event.unidade,
                "origem": event.origem,
                "curso": event.curso,
                "forma_ingresso": event.forma_ingresso,
                "status": event.lead_status,
                "created_at": event.created_at,
                "updated_at": now,
                "received_at": now,
                "payload": event.payload,
            }
            if lead is None:
                session.add(Lead(lead_id=event.lead_id, **values))
            else:
                for key, value in values.items():
                    setattr(lead, key, value)

            stored_event = session.scalar(
                select(WebhookEvent).where(WebhookEvent.event_id == event.event_id)
            )
            stored_event.status = "processed"
            stored_event.processed_at = now
            stored_event.error_message = None
    except SQLAlchemyError as exc:
        _mark_event_as_error(event.event_id, str(exc))
        raise
    return False


def _mark_event_as_error(event_id: str, message: str) -> None:
    try:
        with get_session() as session, session.begin():
            stored_event = session.scalar(
                select(WebhookEvent).where(WebhookEvent.event_id == event_id)
            )
            if stored_event:
                stored_event.status = "error"
                stored_event.error_message = message[:1000]
    except SQLAlchemyError:
        # A exceção original é mais útil e será registrada pela camada HTTP.
        pass


def list_recent_leads(limit: int = 50) -> list[dict[str, Any]]:
    day_start, day_end = current_day_utc_bounds()
    with get_session() as session:
        rows = session.scalars(
            select(Lead)
            .where(
                is_from_current_day(
                    Lead.created_at, Lead.received_at, day_start, day_end
                )
            )
            .order_by(Lead.received_at.desc())
            .limit(limit)
        ).all()
        return [
            {
                "leadid": row.lead_id,
                "lead_id": row.lead_id,
                "nome": row.nome,
                "email": row.email,
                "telefone": row.telefone,
                "celular": row.telefone,
                "unidade": row.unidade,
                "origem": row.origem,
                "curso": row.curso,
                "concurso": row.curso,
                "forma_ingresso": row.forma_ingresso,
                "status": row.status,
                "situacao_funil": row.status,
                "created_at": row.created_at.isoformat() if row.created_at else None,
                "received_at": row.received_at.isoformat(),
                "payload": row.payload,
            }
            for row in rows
        ]
