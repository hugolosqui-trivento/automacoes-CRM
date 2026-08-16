"""Transformações puras que produzem os relatórios executivos."""

from __future__ import annotations

from dataclasses import dataclass
import unicodedata

import pandas as pd


INSCRICAO_KEY = "_inscricao_key"
LEAD_KEY = "_lead_key"


@dataclass
class Relatorios:
    matriculas_crm: pd.DataFrame
    matriculas_planilha: pd.DataFrame
    sem_proprietario: pd.DataFrame
    casos_acionaveis: pd.DataFrame
    divergencias: pd.DataFrame
    proprietarios_nao_mapeados: pd.DataFrame
    somente_crm: pd.DataFrame
    somente_planilha: pd.DataFrame
    duplicidades_crm: pd.DataFrame
    duplicidades_planilha: pd.DataFrame

    @property
    def metricas(self) -> dict[str, int]:
        return {
            "Matrículas no CRM": len(self.matriculas_crm),
            "Matrículas na planilha": len(self.matriculas_planilha),
            "Sem proprietário": len(self.sem_proprietario),
            "Casos acionáveis": len(self.casos_acionaveis),
            "Divergências": len(self.divergencias),
            "Somente no CRM": len(self.somente_crm),
            "Somente na planilha": len(self.somente_planilha),
        }


def _normalizar_texto(valor) -> str:
    if pd.isna(valor):
        return ""
    texto = unicodedata.normalize("NFKD", str(valor).strip().casefold())
    return "".join(char for char in texto if not unicodedata.combining(char))


def _normalizar_inscricao(serie: pd.Series) -> pd.Series:
    return serie.astype("string").str.strip().str.upper().replace("", pd.NA)


def _normalizar_id(serie: pd.Series) -> pd.Series:
    return (
        serie.astype("string")
        .str.strip()
        .str.strip("{}")
        .str.upper()
        .replace("", pd.NA)
    )


def _com_chave(df: pd.DataFrame, coluna: str) -> pd.DataFrame:
    resultado = df.copy()
    if coluna not in resultado:
        resultado[coluna] = pd.NA
    resultado[INSCRICAO_KEY] = _normalizar_inscricao(resultado[coluna])
    return resultado


def _com_chave_lead(df: pd.DataFrame, coluna: str) -> pd.DataFrame:
    resultado = df.copy()
    if coluna not in resultado:
        resultado[coluna] = pd.NA
    resultado[LEAD_KEY] = _normalizar_id(resultado[coluna])
    return resultado


def _texto_preenchido(serie: pd.Series) -> pd.Series:
    return serie.notna() & serie.astype("string").str.strip().ne("")


def _ordenar_e_unificar(
    df: pd.DataFrame,
    data: str | None = None,
    chave: str = INSCRICAO_KEY,
) -> pd.DataFrame:
    resultado = df.dropna(subset=[chave]).copy()
    if data and data in resultado:
        resultado[data] = pd.to_datetime(resultado[data], errors="coerce", utc=True)
        resultado = resultado.sort_values(data, ascending=False, na_position="last")
    return resultado.drop_duplicates(chave, keep="first")


def gerar_relatorios(
    leads: pd.DataFrame,
    inscricoes: pd.DataFrame,
    planilha: pd.DataFrame,
    proprietario_para_consultor: dict[str, str],
    consultores_ignorados: set[str],
) -> Relatorios:
    leads = _com_chave_lead(leads, "ID Lead")
    inscricoes = _com_chave(inscricoes, "Numero Inscricao")
    inscricoes = _com_chave_lead(inscricoes, "ID Lead Inscrição")
    planilha = _com_chave(planilha, "Número de Inscrição")

    situacao = inscricoes.get("Situação Inscrição", pd.Series(index=inscricoes.index, dtype="object"))
    curso = inscricoes.get("Curso ID", pd.Series(index=inscricoes.index, dtype="object"))
    matriculado = situacao.map(_normalizar_texto).eq("matriculado")
    nao_medicina = ~curso.map(_normalizar_texto).eq("medicina")
    crm_bruto = inscricoes.loc[matriculado & nao_medicina].copy()
    planilha_bruta = planilha.dropna(subset=[INSCRICAO_KEY]).copy()

    duplicidades_crm = crm_bruto[crm_bruto.duplicated(INSCRICAO_KEY, keep=False)].copy()
    duplicidades_planilha = planilha_bruta[
        planilha_bruta.duplicated(INSCRICAO_KEY, keep=False)
    ].copy()
    crm = _ordenar_e_unificar(crm_bruto, "Data Criação Inscrição")
    planilha_unica = _ordenar_e_unificar(planilha_bruta, "DATA")
    leads_unicos = _ordenar_e_unificar(leads, "Data Criação Lead", LEAD_KEY)

    colunas_lead = [
        coluna
        for coluna in [
            LEAD_KEY,
            "ID Lead",
            "Inscrição Atual",
            "Nome Lead",
            "CPF Lead",
            "Proprietário",
        ]
        if coluna in leads_unicos
    ]
    captacao = crm.merge(leads_unicos[colunas_lead], on=LEAD_KEY, how="left")
    proprietario = captacao.get("Proprietário", pd.Series(index=captacao.index, dtype="object"))
    sem_proprietario = captacao.loc[~_texto_preenchido(proprietario)].copy()
    id_lead = sem_proprietario.get("ID Lead", pd.Series(index=sem_proprietario.index, dtype="object"))
    sem_proprietario["Motivo"] = "Lead sem proprietário"
    sem_proprietario.loc[~_texto_preenchido(id_lead), "Motivo"] = (
        "Inscrição sem lead correspondente"
    )

    colunas_planilha = [
        coluna
        for coluna in [
            INSCRICAO_KEY,
            "Número de Inscrição",
            "NOME",
            "CONSULTOR (a)",
            "Unidade",
            "CURSO",
        ]
        if coluna in planilha_unica
    ]
    com_consultor = sem_proprietario.merge(
        planilha_unica[colunas_planilha], on=INSCRICAO_KEY, how="left"
    )
    consultor = com_consultor.get(
        "CONSULTOR (a)", pd.Series(index=com_consultor.index, dtype="object")
    )
    ignorados = {_normalizar_texto(nome) for nome in consultores_ignorados}
    casos_acionaveis = com_consultor.loc[
        _texto_preenchido(consultor) & ~consultor.map(_normalizar_texto).isin(ignorados)
    ].copy()

    base_comparacao = captacao.merge(
        planilha_unica[colunas_planilha], on=INSCRICAO_KEY, how="inner"
    )
    proprietario = base_comparacao.get(
        "Proprietário", pd.Series(index=base_comparacao.index, dtype="object")
    )
    consultor = base_comparacao.get(
        "CONSULTOR (a)", pd.Series(index=base_comparacao.index, dtype="object")
    )
    base_comparacao = base_comparacao.loc[
        _texto_preenchido(proprietario)
        & _texto_preenchido(consultor)
        & ~consultor.map(_normalizar_texto).isin(ignorados)
    ].copy()
    base_comparacao["Consultor esperado"] = base_comparacao["Proprietário"].map(
        proprietario_para_consultor
    )
    nao_mapeados = base_comparacao.loc[
        ~_texto_preenchido(base_comparacao["Consultor esperado"])
    ].copy()
    comparaveis = base_comparacao.loc[
        _texto_preenchido(base_comparacao["Consultor esperado"])
    ].copy()
    divergencias = comparaveis.loc[
        comparaveis["Consultor esperado"].map(_normalizar_texto)
        != comparaveis["CONSULTOR (a)"].map(_normalizar_texto)
    ].copy()

    chaves_crm = set(crm[INSCRICAO_KEY].dropna())
    chaves_planilha = set(planilha_unica[INSCRICAO_KEY].dropna())
    somente_crm = crm.loc[crm[INSCRICAO_KEY].isin(chaves_crm - chaves_planilha)].copy()
    somente_planilha = planilha_unica.loc[
        planilha_unica[INSCRICAO_KEY].isin(chaves_planilha - chaves_crm)
    ].copy()

    return Relatorios(
        matriculas_crm=crm,
        matriculas_planilha=planilha_unica,
        sem_proprietario=com_consultor,
        casos_acionaveis=casos_acionaveis,
        divergencias=divergencias,
        proprietarios_nao_mapeados=nao_mapeados,
        somente_crm=somente_crm,
        somente_planilha=somente_planilha,
        duplicidades_crm=duplicidades_crm,
        duplicidades_planilha=duplicidades_planilha,
    )


def para_exibicao(df: pd.DataFrame) -> pd.DataFrame:
    return df.drop(columns=[col for col in df.columns if col.startswith("_")], errors="ignore")
