"""Página de reconciliação das matrículas."""

import streamlit as st

from ui import (
    filtrar_por_unidade_lead,
    iniciar_pagina,
    mostrar_atualizacao,
    mostrar_metricas,
    mostrar_tabela,
)


relatorios, atualizado_em = iniciar_pagina("Comparação de matrículas", "🔄")

st.title("Comparação de matrículas")
st.write(
    "Reconciliação por número de inscrição único e normalizado, considerando somente "
    "matriculados e excluindo Medicina."
)
mostrar_atualizacao(atualizado_em)

unidades_disponiveis = sorted(
    {
        str(unidade)
        for dataframe in (relatorios.matriculas_crm, relatorios.matriculas_planilha)
        if "Unidade Lead" in dataframe
        for unidade in dataframe["Unidade Lead"].dropna()
        if str(unidade).strip()
    }
)
unidades_selecionadas = st.multiselect(
    "Unidade Lead",
    unidades_disponiveis,
    placeholder="Todas as unidades",
)

matriculas_crm = filtrar_por_unidade_lead(
    relatorios.matriculas_crm, unidades_selecionadas
)
matriculas_planilha = filtrar_por_unidade_lead(
    relatorios.matriculas_planilha, unidades_selecionadas
)
somente_crm = filtrar_por_unidade_lead(relatorios.somente_crm, unidades_selecionadas)
somente_planilha = filtrar_por_unidade_lead(
    relatorios.somente_planilha, unidades_selecionadas
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
    mostrar_tabela(somente_crm, "somente_crm")
with aba_planilha:
    mostrar_tabela(somente_planilha, "somente_planilha")
with aba_qualidade:
    st.subheader("Duplicidades no CRM")
    mostrar_tabela(relatorios.duplicidades_crm, "duplicidades_crm")
    st.subheader("Duplicidades na planilha")
    mostrar_tabela(relatorios.duplicidades_planilha, "duplicidades_planilha")

