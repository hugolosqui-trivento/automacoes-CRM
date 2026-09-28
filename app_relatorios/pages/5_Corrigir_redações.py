"""Página de consulta e correção das redações entregues."""

import streamlit as st

from data_loader import carregar_leads_redacoes, carregar_redacoes
from services.redacoes import (
    corrigir_redacoes,
    enviar_correcoes_crm,
    vincular_redacoes_a_leads,
)
from ui import mostrar_cabecalho, preparar_pagina


settings, aberto_em = preparar_pagina("Corrigir redações", "✍️")

st.markdown(
    """
    <style>
    button[aria-label="Download as CSV"] {
        display: none !important;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

st.session_state.setdefault("redacoes_entregues", None)
st.session_state.setdefault("redacoes_corrigidas", None)
st.session_state.setdefault("redacoes_consultadas_em", None)
st.session_state.setdefault("redacoes_envio_crm", None)

consultado_em = st.session_state.redacoes_consultadas_em or aberto_em
mostrar_cabecalho(
    "Corrigir redações",
    "Busca as redações e os leads no CRM, corrige os textos com IA e envia o resultado ao cadastro do lead.",
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
        with st.spinner("Consultando as redações e os leads no CRM..."):
            carregar_redacoes.clear()
            carregar_leads_redacoes.clear()
            redacoes, instante = carregar_redacoes(settings.crm)
            leads = carregar_leads_redacoes(settings.crm)
            redacoes = vincular_redacoes_a_leads(redacoes, leads)
        st.session_state.redacoes_entregues = redacoes
        st.session_state.redacoes_corrigidas = None
        st.session_state.redacoes_envio_crm = None
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

sem_cpf = redacoes["CPF Lead"].isna().sum()
if sem_cpf:
    st.warning(
        f"{sem_cpf} redação(ões) não possui(em) um lead com CPF e Inscrição Atual correspondente. "
        "Esses registros poderão ser corrigidos, mas não serão enviados ao CRM."
    )

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
    st.session_state.redacoes_corrigidas = None
    st.session_state.redacoes_envio_crm = None

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
    else:
        barra_envio = st.progress(0, text="Preparando o envio ao CRM...")

        def atualizar_envio(concluidas: int, total: int) -> None:
            barra_envio.progress(
                concluidas / total,
                text=f"Enviando correções: {concluidas} de {total}",
            )

        try:
            envio = enviar_correcoes_crm(
                resultado,
                settings.crm,
                ao_enviar=atualizar_envio,
            )
            st.session_state.redacoes_envio_crm = envio
        except Exception as exc:
            st.error(f"Não foi possível enviar as correções ao CRM: {exc}")
        finally:
            barra_envio.empty()

resultado = st.session_state.redacoes_corrigidas
if resultado is not None:
    st.subheader("Resultado final")
    st.dataframe(
        resultado,
        hide_index=True,
        key="redacoes_corrigidas_tabela",
        column_config={
            "Nota": st.column_config.NumberColumn("Nota", min_value=0, max_value=100),
        },
    )

    envio = st.session_state.redacoes_envio_crm
    if envio is not None:
        enviados = envio["Status"].eq("Enviado").sum()
        erros = envio["Status"].eq("Erro").sum()
        nao_enviados = envio["Status"].eq("Não enviado").sum()
        if enviados:
            st.success(f"{enviados} correção(ões) enviada(s) ao CRM com sucesso.")
        if erros or nao_enviados:
            st.warning(
                f"Envio concluído com {erros} erro(s) e {nao_enviados} registro(s) sem CPF correspondente."
            )
        st.dataframe(envio, hide_index=True, key="redacoes_envio_crm_tabela")
