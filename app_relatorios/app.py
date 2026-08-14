"""Página inicial do dashboard executivo."""

import streamlit as st

from ui import iniciar_pagina, mostrar_atualizacao, mostrar_metricas


relatorios, atualizado_em = iniciar_pagina("Visão executiva")

st.title("Visão executiva")
st.write(
    "Acompanhamento da atribuição dos leads e da consistência das matrículas "
    "entre o CRM Educacional e a planilha operacional."
)
mostrar_atualizacao(atualizado_em)
mostrar_metricas(relatorios.metricas)

st.subheader("Pontos para decisão")
coluna_a, coluna_b = st.columns(2)
coluna_a.info(
    f"{len(relatorios.casos_acionaveis)} caso(s) têm consultor identificado e podem "
    "receber proprietário no CRM."
)
coluna_b.warning(
    f"{len(relatorios.somente_crm)} matrícula(s) estão somente no CRM e "
    f"{len(relatorios.somente_planilha)} somente na planilha."
)

sem_lead = relatorios.sem_proprietario.get("Motivo")
if sem_lead is not None:
    distribuicao = sem_lead.value_counts().rename_axis("Motivo").reset_index(name="Quantidade")
    st.subheader("Por que o proprietário não foi identificado")
    st.dataframe(distribuicao, use_container_width=True, hide_index=True)

with st.expander("Qualidade e cobertura dos dados"):
    st.write(
        f"Duplicidades antes da consolidação: {len(relatorios.duplicidades_crm)} linha(s) "
        f"no CRM e {len(relatorios.duplicidades_planilha)} na planilha."
    )
    st.write(
        f"Proprietários ainda não cadastrados no mapeamento: "
        f"{len(relatorios.proprietarios_nao_mapeados)}."
    )


