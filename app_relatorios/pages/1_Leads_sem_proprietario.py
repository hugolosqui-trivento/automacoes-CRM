"""Página de atribuição e divergência dos leads."""

import streamlit as st

from ui import iniciar_pagina, mostrar_cabecalho, mostrar_metricas, mostrar_tabela


relatorios, atualizado_em = iniciar_pagina("Leads sem proprietário", "👤")

mostrar_cabecalho(
    "Leads sem proprietário",
    "Separa leads realmente sem proprietário de inscrições que não encontraram "
    "um lead correspondente, e confronta proprietário com consultor.",
    atualizado_em,
)
mostrar_metricas(
    {
        "Sem proprietário": len(relatorios.sem_proprietario),
        "Casos acionáveis": len(relatorios.casos_acionaveis),
        "Divergências": len(relatorios.divergencias),
        "Proprietários não mapeados": len(relatorios.proprietarios_nao_mapeados),
    }
)

aba_acao, aba_todos, aba_divergencias, aba_mapeamento = st.tabs(
    ["Casos acionáveis", "Todos sem proprietário", "Divergências", "Não mapeados"]
)
with aba_acao:
    mostrar_tabela(relatorios.casos_acionaveis, "acionaveis")
with aba_todos:
    mostrar_tabela(relatorios.sem_proprietario, "sem_proprietario")
with aba_divergencias:
    mostrar_tabela(relatorios.divergencias, "divergencias")
with aba_mapeamento:
    st.info(
        "Estes registros não entram no cálculo de divergência até que o proprietário "
        "seja associado a um consultor em config/regras.py."
    )
    mostrar_tabela(relatorios.proprietarios_nao_mapeados, "nao_mapeados")

