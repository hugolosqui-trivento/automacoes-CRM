import json
import logging

from fastapi import APIRouter, Header, HTTPException, Request, status
from pydantic import ValidationError
from sqlalchemy.exc import SQLAlchemyError

from api.schemas.inscricao import InscricaoWebhook
from api.schemas.lead import LeadWebhook
from api.services.inscricao_service import (
    build_inscricao_event,
    process_inscricao_event,
)
from api.services.lead_service import build_event, process_event
from database.repositories.inscricoes import list_recent_inscricoes
from database.repositories.leads import list_recent_leads

router = APIRouter()
logger = logging.getLogger(__name__)


async def _read_payload(request: Request) -> dict:
    try:
        payload = await request.json()
    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
        raise HTTPException(status_code=400, detail="Payload JSON inválido") from exc
    if not isinstance(payload, dict):
        raise HTTPException(status_code=400, detail="O payload deve ser um objeto JSON")
    return payload


def _process_lead(
    payload: dict,
    x_event_id: str | None,
) -> dict[str, str | bool]:
    lead = LeadWebhook.model_validate(payload)
    event = build_event(lead, payload, x_event_id)
    duplicate = process_event(event)
    _log_processed_event(event.event_id, event.event_type, event.lead_id, duplicate)
    return {"status": "received", "duplicate": duplicate}


def _process_inscricao(
    payload: dict,
    x_event_id: str | None,
) -> dict[str, str | bool]:
    inscricao = InscricaoWebhook.model_validate(payload)
    event = build_inscricao_event(inscricao, payload, x_event_id)
    duplicate = process_inscricao_event(event)
    _log_processed_event(event.event_id, event.event_type, event.lead_id, duplicate)
    return {"status": "received", "duplicate": duplicate}


def _log_processed_event(
    event_id: str,
    event_type: str,
    lead_id: str,
    duplicate: bool,
) -> None:
    logger.info(
        "Webhook processado event_id=%s event_type=%s lead_id=%s duplicate=%s",
        event_id,
        event_type,
        lead_id,
        duplicate,
    )


async def _receive(
    request: Request,
    x_event_id: str | None,
    expected_type: str | None = None,
) -> dict[str, str | bool]:
    payload = await _read_payload(request)

    try:
        is_inscricao = expected_type == "inscricao" or (
            expected_type is None and "cad_numeroinscricao" in payload
        )
        if is_inscricao:
            return _process_inscricao(payload, x_event_id)
        return _process_lead(payload, x_event_id)
    except ValidationError as exc:
        raise HTTPException(status_code=422, detail=exc.errors()) from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except SQLAlchemyError as exc:
        logger.exception("Falha ao persistir webhook")
        raise HTTPException(status_code=500, detail="Falha ao persistir evento") from exc


@router.post("/webhook", status_code=status.HTTP_202_ACCEPTED)
async def receive_webhook(
    request: Request,
    x_event_id: str | None = Header(default=None),
):
    return await _receive(request, x_event_id)


@router.post("/webhook/lead")
async def receive_legacy_webhook(
    request: Request,
    x_event_id: str | None = Header(default=None),
):
    result = await _receive(request, x_event_id, expected_type="lead")
    return {"status": "recebido", "duplicate": result["duplicate"]}


@router.post("/webhook/inscricao", status_code=status.HTTP_202_ACCEPTED)
async def receive_inscricao_webhook(
    request: Request,
    x_event_id: str | None = Header(default=None),
):
    return await _receive(request, x_event_id, expected_type="inscricao")


@router.get("/webhook/leads")
def get_leads(
    limit: int = 50,
):
    safe_limit = min(max(limit, 1), 100)
    leads = list_recent_leads(safe_limit)
    return {"total": len(leads), "leads": leads}


@router.get("/webhook/inscricoes")
def get_inscricoes(limit: int = 50):
    safe_limit = min(max(limit, 1), 100)
    inscricoes = list_recent_inscricoes(safe_limit)
    return {"total": len(inscricoes), "inscricoes": inscricoes}
