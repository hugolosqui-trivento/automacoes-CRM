"""Página de reconciliação das matrículas de Medicina."""

import streamlit as st

from data_loader import carregar_dados_medicina
from services.relatorios import (
    calcular_exclusivos_matriculas,
    gerar_comparacao_medicina,
)
from settings import carregar_settings
from ui import (
    filtrar_por_unidade_lead,
    iniciar_pagina,
    mostrar_cabecalho,
    mostrar_metricas,
    mostrar_tabela,
)


relatorios, atualizado_em = iniciar_pagina(
    "Comparação de matrículas de Medicina", "🩺"
)
settings = carregar_settings()
if not settings.matriculas_medicina_url:
    st.error("Configuração incompleta: MATRICULAS_MEDICINA_URL")
    st.stop()
try:
    planilha_medicina = carregar_dados_medicina(settings.matriculas_medicina_url)
except Exception as exc:
    st.error(f"Falha ao carregar a planilha de Medicina: {exc}")
    st.info("Confira o secret MATRICULAS_MEDICINA_URL e o acesso à planilha.")
    st.stop()

comparacao = gerar_comparacao_medicina(
    relatorios.inscricoes_crm, planilha_medicina
)

mostrar_cabecalho(
    "Comparação de matrículas de Medicina",
    "Reconciliação das matrículas de Medicina entre o CRM e a planilha exclusiva, "
    "pelo número de inscrição único e normalizado.",
    atualizado_em,
)

unidades_disponiveis = sorted(
    {
        str(unidade)
        for dataframe in (
            comparacao.matriculas_crm,
            comparacao.matriculas_planilha,
        )
        if "Unidade Lead" in dataframe
        for unidade in dataframe["Unidade Lead"].dropna()
        if str(unidade).strip()
    }
)
coluna_filtro, _ = st.columns(2)
with coluna_filtro:
    unidades_selecionadas = st.multiselect(
        "Unidade Lead",
        unidades_disponiveis,
        placeholder="Todas as unidades",
    )

matriculas_crm = filtrar_por_unidade_lead(
    comparacao.matriculas_crm, unidades_selecionadas
)
matriculas_planilha = filtrar_por_unidade_lead(
    comparacao.matriculas_planilha, unidades_selecionadas
)
somente_crm, somente_planilha = calcular_exclusivos_matriculas(
    matriculas_crm,
    matriculas_planilha,
    relatorios.inscricoes_crm,
)

mostrar_metricas(
    {
        "Matrículas únicas no CRM": len(matriculas_crm),
        "Matrículas únicas na planilha": len(matriculas_planilha),
        "Somente no CRM": len(somente_crm),
        "Somente na planilha": len(somente_planilha),
    }
)

aba_crm, aba_planilha, aba_qualidade = st.tabs(
    ["Somente no CRM", "Somente na planilha", "Duplicidades"]
)
with aba_crm:
    mostrar_tabela(somente_crm, "somente_medicina_crm")
with aba_planilha:
    mostrar_tabela(
        somente_planilha, "somente_medicina_planilha"
    )
with aba_qualidade:
    st.subheader("Duplicidades no CRM")
    mostrar_tabela(
        comparacao.duplicidades_crm, "duplicidades_medicina_crm"
    )
    st.subheader("Duplicidades na planilha de Medicina")
    mostrar_tabela(
        comparacao.duplicidades_planilha,
        "duplicidades_medicina_planilha",
    )
