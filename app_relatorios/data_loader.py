"""Coleta única e cacheada das fontes usadas por todas as páginas."""

from __future__ import annotations

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


@st.cache_data(ttl=900, show_spinner="Consultando CRM e planilha operacional...")
def carregar_dados(settings: AppSettings) -> tuple[Relatorios, datetime]:
    cliente = CrmClient(settings.crm)
    leads = cliente.fetch_entity("lead", LEAD_ATTRIBUTES, LEAD_RENAME)
    inscricoes = cliente.fetch_entity(
        "cad_inscricaocandidato",
        INSCRICAO_ATTRIBUTES,
        INSCRICAO_RENAME,
        text_attributes={"cad_clientepotencialid"},
    )
    planilha = carregar_planilha(settings.matriculas_url, PLANILHA_ABAS)
    relatorios = gerar_relatorios(
        leads,
        inscricoes,
        planilha,
        PROPRIETARIO_PARA_CONSULTOR,
        CONSULTORES_IGNORADOS,
    )
    return relatorios, datetime.now().astimezone()

