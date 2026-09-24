"""Página de consulta e correção das redações entregues."""

import streamlit as st

from data_loader import carregar_redacoes
from services.redacoes import corrigir_redacoes, dataframe_para_excel
from ui import mostrar_cabecalho, preparar_pagina


settings, aberto_em = preparar_pagina("Corrigir redações", "✍️")

st.session_state.setdefault("redacoes_entregues", None)
st.session_state.setdefault("redacoes_corrigidas", None)
st.session_state.setdefault("redacoes_consultadas_em", None)

consultado_em = st.session_state.redacoes_consultadas_em or aberto_em
mostrar_cabecalho(
    "Corrigir redações",
    "Busca as redações entregues no CRM, atribui notas de 1 a 10 com IA e prepara o resultado para download.",
    consultado_em,
)

if not settings.openrouter_key:
    st.error("Configuração incompleta: OPENROUTER_KEY (ou OPENROUTER_API).")
    st.stop()

st.info(
    "A correção avalia coerência temática, abrangência do conteúdo, correção gramatical e qualidade geral da escrita."
)

if st.button(
    "Buscar redações entregues",
    type="primary",
    icon=":material/search:",
    width="stretch",
):
    try:
        with st.spinner("Consultando as redações no CRM..."):
            carregar_redacoes.clear()
            redacoes, instante = carregar_redacoes(settings.crm)
        st.session_state.redacoes_entregues = redacoes
        st.session_state.redacoes_corrigidas = None
        st.session_state.redacoes_consultadas_em = instante
    except Exception as exc:
        st.error(f"Não foi possível buscar as redações: {exc}")

redacoes = st.session_state.redacoes_entregues
if redacoes is None:
    st.caption("Busque as redações para iniciar a correção.")
    st.stop()

st.metric("Redações entregues", len(redacoes))
st.dataframe(redacoes, hide_index=True, key="redacoes_entregues_tabela")

if redacoes.empty:
    st.warning("Nenhuma redação com situação Entregue foi encontrada.")
    st.stop()

st.caption(
    f"Modelo configurado: {settings.openrouter_model}. Cada redação gera uma chamada à API do OpenRouter."
)

if st.button(
    "Corrigir redações com IA",
    type="primary",
    icon=":material/auto_awesome:",
    width="stretch",
):
    barra = st.progress(0, text="Preparando a correção...")

    def atualizar_progresso(concluidas: int, total: int) -> None:
        barra.progress(
            concluidas / total,
            text=f"Corrigindo redações: {concluidas} de {total}",
        )

    try:
        resultado = corrigir_redacoes(
            redacoes,
            settings.openrouter_key,
            settings.openrouter_model,
            ao_corrigir=atualizar_progresso,
        )
        st.session_state.redacoes_corrigidas = resultado
        barra.empty()
        st.success(f"{len(resultado)} redação(ões) corrigida(s) com sucesso.")
    except Exception as exc:
        barra.empty()
        st.error(f"A correção foi interrompida: {exc}")

resultado = st.session_state.redacoes_corrigidas
if resultado is not None:
    st.subheader("Resultado final")
    st.dataframe(
        resultado,
        hide_index=True,
        key="redacoes_corrigidas_tabela",
        column_config={
            "Nota": st.column_config.NumberColumn("Nota", min_value=1, max_value=10),
        },
    )
    st.download_button(
        "Baixar resultado em Excel",
        data=dataframe_para_excel(resultado),
        file_name="redacoes_corrigidas.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        icon=":material/download:",
        on_click="ignore",
        width="stretch",
    )
