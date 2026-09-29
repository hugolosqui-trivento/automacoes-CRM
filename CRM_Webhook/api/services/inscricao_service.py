import hashlib
import json
from typing import Any

from api.schemas.inscricao import InscricaoWebhook, NormalizedInscricaoEvent
from database.repositories.inscricoes import save_event_and_inscricao

UNIT_PREFIX = "Faculdade Serra Dourada"


def _clean_unit(value: str | None) -> str | None:
    if not value:
        return None
    return value.replace(UNIT_PREFIX, "", 1).strip(" -–—") or None


def build_inscricao_event(
    inscricao: InscricaoWebhook,
    payload: dict[str, Any],
    header_event_id: str | None = None,
) -> NormalizedInscricaoEvent:
    lead_id = (
        inscricao.cad_clientepotencialid.id
        if inscricao.cad_clientepotencialid
        else None
    )
    if not lead_id:
        raise ValueError("Inscrição sem lead id válido")
    if not inscricao.cad_numeroinscricao:
        raise ValueError("Inscrição sem número válido")

    raw_situacao = inscricao.cad_situacao.value if inscricao.cad_situacao else None
    try:
        situacao = int(raw_situacao)
    except (TypeError, ValueError) as exc:
        raise ValueError("Inscrição sem cad_situacao válido") from exc
    if situacao not in range(1, 7):
        raise ValueError("cad_situacao deve estar entre 1 e 6")

    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)
    payload_hash = hashlib.sha256(canonical.encode()).hexdigest()
    external_event_id = header_event_id or inscricao.event_id
    # Alguns emissores reutilizam o identificador da entidade em todas as
    # atualizações. Combinar esse identificador com o conteúdo mantém a
    # idempotência para reenvios iguais sem descartar mudanças de Situação.
    event_id = (
        f"{str(external_event_id)[:190]}:{payload_hash}"
        if external_event_id
        else payload_hash
    )

    return NormalizedInscricaoEvent(
        event_id=str(event_id),
        event_type=inscricao.event_type,
        source=inscricao.source,
        lead_id=str(lead_id),
        numero_inscricao=inscricao.cad_numeroinscricao,
        cad_situacao=situacao,
        curso=inscricao.cad_ofertaid.name if inscricao.cad_ofertaid else None,
        forma_ingresso=(
            inscricao.crmeduc_linha_de_negocios.name
            if inscricao.crmeduc_linha_de_negocios
            else None
        ),
        unidade=_clean_unit(
            inscricao.trivento_unidadedeensinotrivento.name
            if inscricao.trivento_unidadedeensinotrivento
            else None
        ),
        created_at=inscricao.createdon,
        modified_at=inscricao.modifiedon,
        payload=payload,
    )


def process_inscricao_event(event: NormalizedInscricaoEvent) -> bool:
    return save_event_and_inscricao(event)
