"""Página de reconciliação das matrículas."""

import streamlit as st

from ui import iniciar_pagina, mostrar_atualizacao, mostrar_metricas, mostrar_tabela


relatorios, atualizado_em = iniciar_pagina("Comparação de matrículas", "🔄")

st.title("Comparação de matrículas")
st.write(
    "Reconciliação por número de inscrição único e normalizado, considerando somente "
    "matriculados e excluindo Medicina."
)
mostrar_atualizacao(atualizado_em)
mostrar_metricas(
    {
        "Matrículas únicas no CRM": len(relatorios.matriculas_crm),
        "Matrículas únicas na planilha": len(relatorios.matriculas_planilha),
        "Somente no CRM": len(relatorios.somente_crm),
        "Somente na planilha": len(relatorios.somente_planilha),
    }
)

aba_crm, aba_planilha, aba_qualidade = st.tabs(
    ["Somente no CRM", "Somente na planilha", "Duplicidades"]
)
with aba_crm:
    mostrar_tabela(
        relatorios.somente_crm,
        "somente_crm",
        "matriculas_somente_crm.xlsx",
    )
with aba_planilha:
    mostrar_tabela(
        relatorios.somente_planilha,
        "somente_planilha",
        "matriculas_somente_planilha.xlsx",
    )
with aba_qualidade:
    st.subheader("Duplicidades no CRM")
    mostrar_tabela(
        relatorios.duplicidades_crm,
        "duplicidades_crm",
        "duplicidades_crm.xlsx",
    )
    st.subheader("Duplicidades na planilha")
    mostrar_tabela(
        relatorios.duplicidades_planilha,
        "duplicidades_planilha",
        "duplicidades_planilha.xlsx",
    )

