from collections.abc import Mapping
from datetime import UTC, datetime, timedelta
from typing import Any
import unicodedata

from sqlalchemy import and_, func, select

from database.connection import get_session
from database.models import Inscricao, Lead, WebhookEvent
from database.retention import (
    BUSINESS_TIMEZONE,
    current_day_utc_bounds,
    is_from_current_day,
)

SITUACAO_LABELS = {
    1: "Inscrito",
    2: "Aprovado",
    3: "Classificado",
    4: "Desclassificado",
    5: "Desistente",
    6: "Matriculado",
}
FUNNEL_STAGE_LABELS = {
    0: "Lead",
    1: "Inscrito",
    2: "Aprovado",
    3: "Matriculado",
}
# Cada Situação é traduzida para o último marco institucional alcançado.
SITUACAO_TO_FUNNEL_STAGE = {
    1: 1,  # Inscrito
    2: 2,  # Aprovado
    3: 2,  # Classificado: já atingiu aprovação
    4: 1,  # Desclassificado: chegou a se inscrever
    5: 2,  # Desistente: aprovado, mas não matriculado
    6: 3,  # Matriculado
}
FUNNEL_STAGES = tuple(FUNNEL_STAGE_LABELS)
MATRICULA_UNITS = ("Altamira", "Canaã", "Itabirito", "Lorena")


def _crm_field_value(value: object, *keys: str) -> object:
    if not isinstance(value, Mapping):
        return value
    for key in keys:
        if key in value:
            return value[key]
    return None


def _matricula_unit(value: object) -> str | None:
    raw_name = _crm_field_value(value, "Name", "name")
    if raw_name is None:
        return None

    normalized = "".join(
        character
        for character in unicodedata.normalize("NFKD", str(raw_name))
        if not unicodedata.combining(character)
    ).casefold()
    aliases = (
        ("altamira", "Altamira"),
        ("canaa", "Canaã"),
        ("itabirito", "Itabirito"),
        ("alis", "Itabirito"),
        ("lorena", "Lorena"),
    )
    return next((unit for alias, unit in aliases if alias in normalized), None)


def load_daily_matriculas(now: datetime | None = None) -> dict[str, Any]:
    """Count unique enrollments that reached ``cad_situacao = 6`` today."""
    day_start, day_end = current_day_utc_bounds(now)
    with get_session() as session:
        rows = session.execute(
            select(WebhookEvent.payload, WebhookEvent.received_at)
            .where(
                WebhookEvent.received_at >= day_start,
                WebhookEvent.received_at < day_end,
                WebhookEvent.status == "processed",
            )
            .order_by(WebhookEvent.received_at)
        ).all()

    unit_by_inscricao: dict[str, str | None] = {}
    last_received_at: datetime | None = None
    for payload, received_at in rows:
        if not isinstance(payload, Mapping):
            continue

        numero_inscricao = payload.get("cad_numeroinscricao")
        raw_situacao = _crm_field_value(payload.get("cad_situacao"), "Value", "value")
        try:
            situacao = int(raw_situacao)  # type: ignore[arg-type]
        except (TypeError, ValueError):
            continue
        if situacao != 6 or not numero_inscricao:
            continue

        registration_key = str(numero_inscricao).strip()
        if not registration_key:
            continue

        unit = _matricula_unit(payload.get("trivento_unidadedeensinotrivento"))
        if unit is not None or registration_key not in unit_by_inscricao:
            unit_by_inscricao[registration_key] = unit
        if last_received_at is None or received_at > last_received_at:
            last_received_at = received_at

    counts = {
        unit: sum(stored_unit == unit for stored_unit in unit_by_inscricao.values())
        for unit in MATRICULA_UNITS
    }
    return {
        "total": len(unit_by_inscricao),
        "units": counts,
        "unmapped": sum(unit is None for unit in unit_by_inscricao.values()),
        "last_received_at": last_received_at,
    }


def load_metrics() -> dict[str, Any]:
    now = datetime.now(UTC)
    day_start, day_end = current_day_utc_bounds(now)
    lead_is_today = is_from_current_day(
        Lead.created_at, Lead.received_at, day_start, day_end
    )
    event_is_today = and_(
        WebhookEvent.received_at >= day_start,
        WebhookEvent.received_at < day_end,
    )

    with get_session() as session:
        return {
            "today": session.scalar(select(func.count()).where(lead_is_today)) or 0,
            "last_hour": session.scalar(
                select(func.count()).where(
                    lead_is_today,
                    Lead.received_at >= now - timedelta(hours=1),
                )
            ) or 0,
            "last_five_minutes": session.scalar(
                select(func.count()).where(
                    lead_is_today,
                    Lead.received_at >= now - timedelta(minutes=5),
                )
            ) or 0,
            "errors": session.scalar(
                select(func.count()).where(
                    event_is_today,
                    WebhookEvent.status == "error",
                )
            ) or 0,
            "last_webhook": session.scalar(
                select(func.max(WebhookEvent.received_at)).where(event_is_today)
            ),
        }


def load_recent_leads(limit: int = 50) -> list[dict[str, Any]]:
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
                "Horário": row.received_at,
                "Lead ID": row.lead_id,
                "Nome": row.nome,
                "Email": row.email,
                "Celular": row.telefone,
                "Concurso": row.curso,
                "Situação no funil": row.status,
            }
            for row in rows
        ]


def load_daily_funnel() -> dict[str, Any]:
    now = datetime.now(UTC)
    progress_by_lead = _load_daily_lead_progress(now)
    current_stage_by_lead = {
        lead_id: progress["stage"] for lead_id, progress in progress_by_lead.items()
    }

    total = len(current_stage_by_lead)
    stages = [
        {
            "stage": stage,
            "label": FUNNEL_STAGE_LABELS[stage],
            "count": sum(
                1 for current in current_stage_by_lead.values() if current >= stage
            ),
            "stalled_count": sum(
                1 for current in current_stage_by_lead.values() if current == stage
            ),
        }
        for stage in FUNNEL_STAGES
    ]
    for item in stages:
        item["percentage"] = round(item["count"] / total * 100, 1) if total else 0.0

    return {
        "cohort_date": now.astimezone(BUSINESS_TIMEZONE).date(),
        "total": total,
        "leads_only": sum(stage == 0 for stage in current_stage_by_lead.values()),
        "stages": stages,
    }


def load_leads_at_funnel_stage(
    stage: int, limit: int = 100
) -> list[dict[str, Any]]:
    """Return today's leads whose latest enrollment is exactly at ``stage``."""
    if stage not in FUNNEL_STAGE_LABELS:
        raise ValueError(f"Etapa de funil inválida: {stage}")
    if limit < 1:
        return []

    progress = [
        item
        for item in _load_daily_lead_progress().values()
        if item["stage"] == stage
    ]
    progress.sort(key=lambda item: item["last_activity_at"], reverse=True)

    return [
        {
            "Nome": item["nome"],
            "Email": item["email"],
            "Celular": item["telefone"],
            "Curso": item["curso"],
            "Forma de ingresso": item["forma_ingresso"],
            "Unidade": item["unidade"],
            "Situação no CRM": item["situacao_label"],
            "Última movimentação": item["last_activity_at"],
            "Lead ID": item["lead_id"],
        }
        for item in progress[:limit]
    ]


def _load_daily_lead_progress(
    now: datetime | None = None,
) -> dict[str, dict[str, Any]]:
    """Resolve the exact current funnel stage from each lead's latest enrollment."""
    day_start, day_end = current_day_utc_bounds(now)
    lead_is_today = is_from_current_day(
        Lead.created_at, Lead.received_at, day_start, day_end
    )

    with get_session() as session:
        rows = session.execute(
            select(
                Lead.lead_id,
                Lead.nome,
                Lead.email,
                Lead.telefone,
                Lead.curso,
                Lead.forma_ingresso,
                Lead.unidade,
                Lead.received_at.label("lead_received_at"),
                Inscricao.numero_inscricao,
                Inscricao.cad_situacao,
                Inscricao.curso.label("inscricao_curso"),
                Inscricao.forma_ingresso.label("inscricao_forma_ingresso"),
                Inscricao.unidade.label("inscricao_unidade"),
                Inscricao.received_at.label("inscricao_received_at"),
            )
            .outerjoin(Inscricao, Inscricao.lead_id == Lead.lead_id)
            .where(lead_is_today)
        ).all()

    progress_by_lead: dict[str, dict[str, Any]] = {}
    latest_inscricao_key_by_lead: dict[str, tuple[datetime, str]] = {}
    for row in rows:
        progress_by_lead.setdefault(
            row.lead_id,
            {
                "lead_id": row.lead_id,
                "nome": row.nome,
                "email": row.email,
                "telefone": row.telefone,
                "curso": row.curso,
                "forma_ingresso": row.forma_ingresso,
                "unidade": row.unidade,
                "stage": 0,
                "situacao_label": "Sem inscrição",
                "last_activity_at": row.lead_received_at,
            },
        )

        funnel_stage = _funnel_stage_for_situacao(row.cad_situacao)
        if funnel_stage is None or row.inscricao_received_at is None:
            continue

        inscricao_key = (row.inscricao_received_at, row.numero_inscricao or "")
        latest_inscricao_key = latest_inscricao_key_by_lead.get(row.lead_id)
        if latest_inscricao_key is not None and inscricao_key <= latest_inscricao_key:
            continue

        latest_inscricao_key_by_lead[row.lead_id] = inscricao_key
        progress_by_lead[row.lead_id].update(
            {
                "curso": row.inscricao_curso or row.curso,
                "forma_ingresso": (
                    row.inscricao_forma_ingresso or row.forma_ingresso
                ),
                "unidade": row.inscricao_unidade or row.unidade,
                "stage": funnel_stage,
                "situacao_label": SITUACAO_LABELS.get(
                    row.cad_situacao, str(row.cad_situacao)
                ),
                "last_activity_at": row.inscricao_received_at,
            }
        )

    return progress_by_lead


def load_recent_inscricoes(limit: int = 50) -> list[dict[str, Any]]:
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
                "Horário": row.received_at,
                "Número da inscrição": row.numero_inscricao,
                "Lead ID": row.lead_id,
                "Situação": SITUACAO_LABELS.get(
                    row.cad_situacao, str(row.cad_situacao)
                ),
                "Curso": row.curso,
                "Forma de ingresso": row.forma_ingresso,
                "Unidade": row.unidade,
            }
            for row in rows
        ]


def _funnel_stage_for_situacao(value: object) -> int | None:
    try:
        situacao = int(value)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return None
    return SITUACAO_TO_FUNNEL_STAGE.get(situacao)
