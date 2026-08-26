"""Leitura da planilha operacional de matrículas."""

from __future__ import annotations

import pandas as pd


def carregar_planilha(url: str, abas: dict[str, str]) -> pd.DataFrame:
    quadros: list[pd.DataFrame] = []
    for aba, unidade in abas.items():
        quadro = pd.read_excel(url, sheet_name=aba)
        quadro["Unidade"] = unidade
        quadros.append(quadro)
    return pd.concat(quadros, ignore_index=True)


def carregar_planilha_medicina(
    url: str, abas: dict[str, str]
) -> pd.DataFrame:
    """Carrega as abas de Medicina e identifica a unidade de cada registro."""
    quadros: list[pd.DataFrame] = []
    for aba, unidade in abas.items():
        quadro = pd.read_excel(url, sheet_name=aba)
        quadro["Unidade Lead"] = unidade
        quadros.append(quadro)
    return pd.concat(quadros, ignore_index=True)

