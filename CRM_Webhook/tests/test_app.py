import os
import tempfile
from datetime import UTC, datetime
from pathlib import Path

import pytest
from sqlalchemy import func, select
from sqlalchemy.exc import SQLAlchemyError

TEST_DB = Path(tempfile.gettempdir()) / "crm_webhook_test.db"
os.environ["DATABASE_URL"] = f"sqlite:///{TEST_DB.as_posix()}"

from api.main import app
from database.connection import get_engine, get_session
from database.models import Base, Inscricao, Lead, WebhookEvent
from database.repositories.dashboard import (
    load_daily_funnel,
    load_leads_at_funnel_stage,
)
from database.retention import purge_records_outside_current_day
from fastapi.testclient import TestClient


@pytest.fixture
def client():
    Base.metadata.drop_all(get_engine())
    Base.metadata.create_all(get_engine())
    with TestClient(app) as test_client:
        yield test_client


def test_health(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_valid_payload_is_persisted_with_optional_fields_absent(client):
    response = client.post(
        "/webhook",
        json={"leadid": "lead-123", "firstname": "Arthur", "lastname": "Teste"},
    )
    assert response.status_code == 202
    assert response.json() == {"status": "received", "duplicate": False}

    result = client.get("/webhook/leads")
    assert result.status_code == 200
    assert result.json()["total"] == 1
    assert result.json()["leads"][0]["nome"] == "Arthur Teste"


def test_real_crm_payload_fields_are_normalized(client):
    payload = {
        "leadid": "733ae44b-9a45-445a-b369-05075d47aa6d",
        "fullname": "Arthur Teste",
        "emailaddress1": "teste@novo.com",
        "mobilephone": "(11)33333-3333",
        "cad_concursoatual": {
            "Id": "08ede592-39b8-f111-aaae-00224836b90d",
            "LogicalName": "cad_concurso",
            "Name": "Vestibular Escolas Parceiras Lorena 27.1",
        },
        "cad_situacaofunil": {"Value": 1, "ExtensionData": {}},
        "createdon": "2026-09-27T03:20:14Z",
    }

    response = client.post("/webhook", json=payload)

    assert response.status_code == 202
    result = client.get("/webhook/leads").json()["leads"][0]
    assert result["leadid"] == payload["leadid"]
    assert result["nome"] == "Arthur Teste"
    assert result["email"] == "teste@novo.com"
    assert result["celular"] == "(11)33333-3333"
    assert result["concurso"] == "Vestibular Escolas Parceiras Lorena 27.1"
    assert result["situacao_funil"] == "1"
    assert result["created_at"] == "2026-09-27T03:20:14"


def test_malformed_json_is_rejected(client):
    response = client.post(
        "/webhook", content="{", headers={"content-type": "application/json"}
    )
    assert response.status_code == 400


def test_payload_without_identifier_is_rejected(client):
    response = client.post("/webhook", json={"nome": "Sem identificador"})
    assert response.status_code == 422


def test_duplicate_event_is_idempotent(client):
    payload = {"event_id": "evt-1", "leadid": "lead-123", "nome": "Primeiro"}
    first = client.post("/webhook", json=payload)
    second = client.post("/webhook", json=payload)

    assert first.json()["duplicate"] is False
    assert second.json()["duplicate"] is True
    with get_session() as session:
        assert session.scalar(select(func.count()).select_from(WebhookEvent)) == 1


def _create_lead(client, lead_id="lead-inscricao", situacao=2):
    return client.post(
        "/webhook",
        json={
            "event_id": f"lead-event-{lead_id}",
            "leadid": lead_id,
            "fullname": "Lead da inscrição",
            "cad_situacaofunil": {"Value": situacao},
            "createdon": datetime.now(UTC).isoformat(),
        },
    )


def _inscricao_payload(lead_id="lead-inscricao", situacao=6):
    return {
        "event_id": f"inscricao-event-{lead_id}-{situacao}",
        "cad_clientepotencialid": {"Id": lead_id, "Name": "Lead da inscrição"},
        "cad_numeroinscricao": f"CAN-007291-{lead_id}",
        "cad_situacao": {"Value": situacao},
        "cad_ofertaid": {"Name": "Farmácia"},
        "crmeduc_linha_de_negocios": {"Name": "Histórico do Ensino Médio Canaã"},
        "trivento_unidadedeensinotrivento": {
            "Name": "Faculdade Serra Dourada de Canaã dos Carajás"
        },
        "createdon": "2026-09-27T04:01:39Z",
        "modifiedon": "2026-09-27T04:13:26Z",
    }


def test_inscricao_payload_is_normalized_and_related_to_lead(client):
    assert _create_lead(client).status_code == 202

    response = client.post("/webhook/inscricao", json=_inscricao_payload())

    assert response.status_code == 202
    assert response.json() == {"status": "received", "duplicate": False}
    result = client.get("/webhook/inscricoes").json()["inscricoes"][0]
    assert result["lead_id"] == "lead-inscricao"
    assert result["numero_inscricao"] == "CAN-007291-lead-inscricao"
    assert result["cad_situacao"] == 6
    assert result["curso"] == "Farmácia"
    assert result["forma_ingresso"] == "Histórico do Ensino Médio Canaã"
    assert result["unidade"] == "de Canaã dos Carajás"

    with get_session() as session:
        stored = session.get(Inscricao, "CAN-007291-lead-inscricao")
        assert stored is not None
        assert stored.lead_id == "lead-inscricao"


def test_generic_webhook_detects_inscricao_and_is_idempotent(client):
    _create_lead(client)
    payload = _inscricao_payload()

    first = client.post("/webhook", json=payload)
    second = client.post("/webhook", json=payload)

    assert first.status_code == 202
    assert first.json()["duplicate"] is False
    assert second.json()["duplicate"] is True
    assert client.get("/webhook/inscricoes").json()["total"] == 1


def test_inscricao_update_with_reused_event_id_advances_situacao(client):
    _create_lead(client, situacao=1)
    first_payload = _inscricao_payload(situacao=1)
    first_payload["event_id"] = "stable-inscricao-id"
    updated_payload = _inscricao_payload(situacao=3)
    updated_payload["event_id"] = "stable-inscricao-id"

    first = client.post("/webhook/inscricao", json=first_payload)
    updated = client.post("/webhook/inscricao", json=updated_payload)

    assert first.json()["duplicate"] is False
    assert updated.json()["duplicate"] is False
    result = client.get("/webhook/inscricoes").json()["inscricoes"][0]
    assert result["cad_situacao"] == 3

    funnel = load_daily_funnel()
    assert [stage["count"] for stage in funnel["stages"]] == [1, 1, 1, 0]


def test_inscricao_rejects_situacao_outside_funnel(client):
    _create_lead(client)
    response = client.post("/webhook/inscricao", json=_inscricao_payload(situacao=7))

    assert response.status_code == 422
    assert response.json()["detail"] == "cad_situacao deve estar entre 1 e 6"


def test_daily_funnel_combines_lead_and_inscricao_situations(client):
    _create_lead(client, situacao=2)
    response = client.post("/webhook/inscricao", json=_inscricao_payload(situacao=6))
    assert response.status_code == 202

    funnel = load_daily_funnel()

    assert funnel["total"] == 1
    assert [stage["label"] for stage in funnel["stages"]] == [
        "Lead",
        "Inscrito",
        "Aprovado",
        "Matriculado",
    ]
    assert [stage["count"] for stage in funnel["stages"]] == [1, 1, 1, 1]


def test_leads_without_inscricao_remain_only_in_lead_stage(client):
    _create_lead(client, lead_id="lead-stage-1", situacao=1)
    _create_lead(client, lead_id="lead-stage-3", situacao=3)

    funnel = load_daily_funnel()

    assert funnel["total"] == 2
    assert funnel["leads_only"] == 2
    assert [stage["count"] for stage in funnel["stages"]] == [2, 0, 0, 0]


def test_latest_inscricao_situation_overrides_higher_lead_status(client):
    _create_lead(client, situacao=6)
    response = client.post("/webhook/inscricao", json=_inscricao_payload(situacao=2))
    assert response.status_code == 202

    funnel = load_daily_funnel()

    assert [stage["count"] for stage in funnel["stages"]] == [1, 1, 1, 0]


@pytest.mark.parametrize(
    ("situacao", "expected_counts"),
    [
        (1, [1, 1, 0, 0]),
        (2, [1, 1, 1, 0]),
        (3, [1, 1, 1, 0]),
        (4, [1, 1, 0, 0]),
        (5, [1, 1, 1, 0]),
        (6, [1, 1, 1, 1]),
    ],
)
def test_all_situacoes_are_mapped_to_institutional_funnel(
    client, situacao, expected_counts
):
    _create_lead(client, situacao=6)
    response = client.post(
        "/webhook/inscricao", json=_inscricao_payload(situacao=situacao)
    )
    assert response.status_code == 202

    funnel = load_daily_funnel()

    assert [stage["count"] for stage in funnel["stages"]] == expected_counts


def test_funnel_stage_details_only_show_leads_that_have_not_advanced(client):
    _create_lead(client, lead_id="lead-only")

    for lead_id, situacao in (
        ("lead-inscrito", 1),
        ("lead-aprovado", 2),
        ("lead-matriculado", 6),
    ):
        _create_lead(client, lead_id=lead_id)
        response = client.post(
            "/webhook/inscricao",
            json=_inscricao_payload(lead_id=lead_id, situacao=situacao),
        )
        assert response.status_code == 202

    assert [
        stage["stalled_count"] for stage in load_daily_funnel()["stages"]
    ] == [1, 1, 1, 1]
    assert [row["Lead ID"] for row in load_leads_at_funnel_stage(0)] == [
        "lead-only"
    ]
    assert [row["Lead ID"] for row in load_leads_at_funnel_stage(1)] == [
        "lead-inscrito"
    ]
    assert [row["Lead ID"] for row in load_leads_at_funnel_stage(2)] == [
        "lead-aprovado"
    ]
    assert [row["Lead ID"] for row in load_leads_at_funnel_stage(3)] == [
        "lead-matriculado"
    ]
    assert load_leads_at_funnel_stage(2)[0]["Situação no CRM"] == "Aprovado"


def test_database_failure_returns_500(client, monkeypatch):
    from api.routes import webhook

    def fail(_event):
        raise SQLAlchemyError("database unavailable")

    monkeypatch.setattr(webhook, "process_event", fail)
    response = client.post("/webhook", json={"leadid": "lead-123"})
    assert response.status_code == 500


def test_daily_cleanup_removes_old_records_and_keeps_current_day(client):
    now = datetime(2026, 9, 27, 15, tzinfo=UTC)
    old_at = datetime(2026, 9, 27, 2, 59, tzinfo=UTC)
    today_at = datetime(2026, 9, 27, 3, 0, tzinfo=UTC)

    with get_session() as session, session.begin():
        session.add_all(
            [
                Lead(
                    lead_id="old-lead",
                    created_at=old_at,
                    received_at=old_at,
                    updated_at=old_at,
                    payload={},
                ),
                Lead(
                    lead_id="today-lead",
                    created_at=today_at,
                    received_at=today_at,
                    updated_at=today_at,
                    payload={},
                ),
                Lead(
                    lead_id="today-without-created-at",
                    created_at=None,
                    received_at=today_at,
                    updated_at=today_at,
                    payload={},
                ),
                Inscricao(
                    numero_inscricao="old-inscricao",
                    lead_id="old-lead",
                    cad_situacao=1,
                    created_at=old_at,
                    received_at=old_at,
                    updated_at=old_at,
                    payload={},
                ),
                Inscricao(
                    numero_inscricao="today-inscricao",
                    lead_id="today-lead",
                    cad_situacao=2,
                    created_at=today_at,
                    received_at=today_at,
                    updated_at=today_at,
                    payload={},
                ),
                WebhookEvent(
                    event_id="old-event",
                    event_type="lead.updated",
                    source="test",
                    lead_id="old-lead",
                    payload={},
                    received_at=old_at,
                    status="processed",
                ),
                WebhookEvent(
                    event_id="today-event",
                    event_type="lead.updated",
                    source="test",
                    lead_id="today-lead",
                    payload={},
                    received_at=today_at,
                    status="processed",
                ),
            ]
        )

    removed = purge_records_outside_current_day(now)

    assert removed == {"inscricoes": 1, "leads": 1, "events": 1}
    with get_session() as session:
        assert set(session.scalars(select(Lead.lead_id))) == {
            "today-lead",
            "today-without-created-at",
        }
        assert list(session.scalars(select(Inscricao.numero_inscricao))) == [
            "today-inscricao"
        ]
        assert list(session.scalars(select(WebhookEvent.event_id))) == [
            "today-event"
        ]
