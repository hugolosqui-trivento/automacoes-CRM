"""Carregamento de configuração por Streamlit secrets ou variáveis de ambiente."""

from __future__ import annotations

from dataclasses import dataclass
import os

import streamlit as st

from services.crm_api import CrmSettings


def _valor(nome: str, padrao: str = "") -> str:
    ambiente = os.getenv(nome)
    if ambiente is not None:
        return ambiente
    try:
        return str(st.secrets.get(nome, padrao))
    except FileNotFoundError:
        return padrao


@dataclass(frozen=True)
class AppSettings:
    crm: CrmSettings
    matriculas_url: str
    app_env: str
    app_password: str
    matriculas_medicina_url: str = ""


def carregar_settings() -> AppSettings:
    return AppSettings(
        crm=CrmSettings(
            base_url=_valor("CRM_BASE_URL", "https://trivento.api.crmeducacional.com"),
            username=_valor("CRM_USERNAME"),
            password=_valor("CRM_PASSWORD"),
            auth_type=_valor("CRM_AUTH_TYPE", "APICRMEducacional"),
        ),
        matriculas_url=_valor("MATRICULAS_URL"),
        app_env=_valor("APP_ENV", "development").casefold(),
        app_password=_valor("APP_PASSWORD"),
        matriculas_medicina_url=_valor("MATRICULAS_MEDICINA_URL"),
    )


def validar_settings(settings: AppSettings) -> list[str]:
    faltantes = []
    if not settings.crm.username:
        faltantes.append("CRM_USERNAME")
    if not settings.crm.password:
        faltantes.append("CRM_PASSWORD")
    if not settings.matriculas_url:
        faltantes.append("MATRICULAS_URL")
    if settings.app_env == "production" and not settings.app_password:
        faltantes.append("APP_PASSWORD")
    return faltantes

