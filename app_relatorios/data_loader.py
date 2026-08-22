"""Coleta única e cacheada das fontes usadas por todas as páginas."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from datetime import datetime

import streamlit as st

from config.regras import (
    CONSULTORES_IGNORADOS,
    INSCRICAO_ATTRIBUTES,
    INSCRICAO_RENAME,
    LEAD_ATTRIBUTES,
    LEAD_RENAME,
    PLANILHA_ABAS,
    PROPRIETARIO_PARA_CONSULTOR,
)
from services.crm_api import CrmClient
from services.planilha_matriculas import carregar_planilha
from services.relatorios import Relatorios, gerar_relatorios
from settings import AppSettings


def _carregar_fontes(settings: AppSettings):
    """Carrega cada fonte em uma thread, preservando sua lógica interna sequencial."""
    cliente_leads = CrmClient(settings.crm)
    cliente_inscricoes = CrmClient(settings.crm)

    with ThreadPoolExecutor(
        max_workers=3,
        thread_name_prefix="carregamento-fonte",
    ) as executor:
        leads_future = executor.submit(
            cliente_leads.fetch_entity,
            "lead",
            LEAD_ATTRIBUTES,
            LEAD_RENAME,
        )
        inscricoes_future = executor.submit(
            cliente_inscricoes.fetch_entity,
            "cad_inscricaocandidato",
            INSCRICAO_ATTRIBUTES,
            INSCRICAO_RENAME,
            text_attributes={"cad_clientepotencialid"},
        )
        planilha_future = executor.submit(
            carregar_planilha,
            settings.matriculas_url,
            PLANILHA_ABAS,
        )

        return (
            leads_future.result(),
            inscricoes_future.result(),
            planilha_future.result(),
        )


@st.cache_data(ttl=900, show_spinner="Consultando CRM e planilha operacional...")
def carregar_dados(settings: AppSettings) -> tuple[Relatorios, datetime]:
    leads, inscricoes, planilha = _carregar_fontes(settings)
    relatorios = gerar_relatorios(
        leads,
        inscricoes,
        planilha,
        PROPRIETARIO_PARA_CONSULTOR,
        CONSULTORES_IGNORADOS,
    )
    return relatorios, datetime.now().astimezone()

