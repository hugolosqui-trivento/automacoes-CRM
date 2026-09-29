import hashlib
import json
from typing import Any

from api.schemas.lead import LeadWebhook, NormalizedEvent
from database.repositories.leads import save_event_and_lead


def build_event(
    lead: LeadWebhook,
    payload: dict[str, Any],
    header_event_id: str | None = None,
) -> NormalizedEvent:
    lead_id = lead.lead_id or lead.leadid or lead.id or lead.emailaddress1 or lead.cad_cpf
    if not lead_id:
        raise ValueError("Lead sem identificador válido")

    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)
    event_id = header_event_id or lead.event_id or hashlib.sha256(canonical.encode()).hexdigest()
    nome = lead.fullname or lead.nome or " ".join(
        part for part in (lead.firstname, lead.lastname) if part
    ) or None
    concurso = (
        lead.cad_concursoatual.name if lead.cad_concursoatual else None
    ) or lead.curso
    situacao_funil = (
        lead.cad_situacaofunil.value if lead.cad_situacaofunil else None
    )

    return NormalizedEvent(
        event_id=str(event_id),
        event_type=lead.event_type,
        source=lead.source,
        lead_id=str(lead_id),
        nome=nome,
        email=lead.email or lead.emailaddress1,
        telefone=lead.telefone or lead.mobilephone,
        unidade=lead.unidade,
        origem=lead.origem,
        curso=concurso,
        forma_ingresso=lead.forma_ingresso,
        lead_status=(
            str(situacao_funil) if situacao_funil is not None else lead.status
        ),
        created_at=lead.createdon or lead.created_at,
        payload=payload,
    )


def process_event(event: NormalizedEvent) -> bool:
    return save_event_and_lead(event)
