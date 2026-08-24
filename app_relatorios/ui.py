"""Componentes de interface compartilhados pelas páginas Streamlit."""

from __future__ import annotations

from datetime import datetime

import pandas as pd
import streamlit as st

from auth import exigir_autenticacao
from data_loader import carregar_dados
from services.relatorios import Relatorios, para_exibicao
from settings import AppSettings, carregar_settings, validar_settings


def iniciar_pagina(titulo: str, icone: str = "📊") -> tuple[Relatorios, datetime]:
    st.set_page_config(page_title=titulo, page_icon=icone, layout="wide")
    settings = carregar_settings()
    exigir_autenticacao(settings.app_password)
    _validar_configuracao(settings)
    _barra_lateral()
    try:
        return carregar_dados(settings)
    except Exception as exc:  # Streamlit deve apresentar erro operacional sem traceback público.
        st.error(f"Falha ao atualizar os relatórios: {exc}")
        st.info("Confira os secrets, a conectividade e os nomes das abas da planilha.")
        st.stop()


def _validar_configuracao(settings: AppSettings) -> None:
    faltantes = validar_settings(settings)
    if not faltantes:
        return
    st.error("Configuração incompleta: " + ", ".join(faltantes))
    st.code("Copy-Item .streamlit/secrets.toml.example .streamlit/secrets.toml")
    st.stop()


def _barra_lateral() -> None:
    st.sidebar.title("Relatórios de captação")
    st.sidebar.caption("CRM Educacional × planilha operacional")
    if st.sidebar.button("Atualizar dados agora", use_container_width=True):
        carregar_dados.clear()
        st.rerun()
    if st.session_state.get("autenticado") and st.sidebar.button(
        "Sair", use_container_width=True
    ):
        st.session_state.pop("autenticado", None)
        st.rerun()


def mostrar_atualizacao(instante: datetime) -> None:
    st.caption(f"Dados atualizados em {instante:%d/%m/%Y às %H:%M:%S %Z} · cache de 15 minutos")


def mostrar_metricas(metricas: dict[str, int], colunas: int = 4) -> None:
    itens = list(metricas.items())
    for inicio in range(0, len(itens), colunas):
        caixas = st.columns(colunas)
        for caixa, (rotulo, valor) in zip(caixas, itens[inicio : inicio + colunas]):
            caixa.metric(rotulo, f"{valor:,}".replace(",", "."))


def filtrar_dataframe(df: pd.DataFrame, prefixo: str) -> pd.DataFrame:
    resultado = df.copy()
    candidatas = [
        "CONSULTOR (a)",
        "Unidade",
        "Unidade Lead",
        "Unidade Inscrito",
        "Curso ID",
        "CURSO",
        "Motivo",
        "Situação Pagamento",
    ]
    colunas = [coluna for coluna in candidatas if coluna in resultado]
    if not colunas:
        return resultado

    with st.expander("Filtros", expanded=False):
        caixas = st.columns(min(3, len(colunas)))
        for indice, coluna in enumerate(colunas):
            opcoes = sorted(resultado[coluna].dropna().astype(str).unique().tolist())
            selecionadas = caixas[indice % len(caixas)].multiselect(
                coluna,
                opcoes,
                key=f"{prefixo}_{coluna}",
            )
            if selecionadas:
                resultado = resultado.loc[resultado[coluna].astype(str).isin(selecionadas)]
    return resultado


def mostrar_tabela(df: pd.DataFrame, prefixo: str) -> None:
    filtrado = filtrar_dataframe(df, prefixo)
    visivel = para_exibicao(filtrado)
    st.caption(f"{len(visivel):,} registro(s) exibido(s)".replace(",", "."))
    st.dataframe(visivel, use_container_width=True, hide_index=True)


def filtrar_por_unidade_lead(
    df: pd.DataFrame, unidades: list[str] | tuple[str, ...]
) -> pd.DataFrame:
    """Aplica o filtro executivo sem alterar bases que não possuem unidade do lead."""
    if not unidades or "Unidade Lead" not in df:
        return df.copy()
    return df.loc[df["Unidade Lead"].astype("string").isin(unidades)].copy()

