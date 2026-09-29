from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

from api.schemas.inscricao import NormalizedInscricaoEvent
from database.connection import get_session
from database.models import Inscricao, Lead, WebhookEvent
from database.retention import current_day_utc_bounds, is_from_current_day


def save_event_and_inscricao(event: NormalizedInscricaoEvent) -> bool:
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
        return True

    try:
        with get_session() as session, session.begin():
            if session.get(Lead, event.lead_id) is None:
                raise ValueError(
                    f"Lead {event.lead_id} não encontrado para a inscrição"
                )

            inscricao = session.get(Inscricao, event.numero_inscricao)
            values = {
                "lead_id": event.lead_id,
                "cad_situacao": event.cad_situacao,
                "curso": event.curso,
                "forma_ingresso": event.forma_ingresso,
                "unidade": event.unidade,
                "created_at": event.created_at,
                "modified_at": event.modified_at,
                "updated_at": now,
                "received_at": now,
                "payload": event.payload,
            }
            if inscricao is None:
                session.add(
                    Inscricao(numero_inscricao=event.numero_inscricao, **values)
                )
            else:
                for key, value in values.items():
                    if value is not None:
                        setattr(inscricao, key, value)

            stored_event = session.scalar(
                select(WebhookEvent).where(WebhookEvent.event_id == event.event_id)
            )
            stored_event.status = "processed"
            stored_event.processed_at = now
            stored_event.error_message = None
    except (SQLAlchemyError, ValueError) as exc:
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
        pass


def list_recent_inscricoes(limit: int = 50) -> list[dict[str, Any]]:
    day_start, day_end = current_day_utc_bounds()
    with get_session() as session:
        rows = session.scalars(
            select(Inscricao)
            .where(
                is_from_current_day(
                    Inscricao.created_at,
                    Inscricao.received_at,
                    day_start,
                    day_end,
                )
            )
            .order_by(Inscricao.received_at.desc())
            .limit(limit)
        ).all()
        return [
            {
                "numero_inscricao": row.numero_inscricao,
                "lead_id": row.lead_id,
                "cad_situacao": row.cad_situacao,
                "curso": row.curso,
                "forma_ingresso": row.forma_ingresso,
                "unidade": row.unidade,
                "created_at": row.created_at.isoformat() if row.created_at else None,
                "modified_at": row.modified_at.isoformat() if row.modified_at else None,
                "received_at": row.received_at.isoformat(),
            }
            for row in rows
        ]
