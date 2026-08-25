"""Leitura e reconciliação de exportações CSV do Power BI com o CRM."""

from __future__ import annotations

from dataclasses import dataclass
from io import BytesIO
import unicodedata

import pandas as pd

from services.relatorios import INSCRICAO_KEY


COLUNA_INSCRICAO_BI = "Número de Inscrição"
COLUNA_UNIDADE_BI = "Unidade"
UNIDADES_CONHECIDAS = {
    "altamira": "Altamira",
    "canaa": "Canaã",
    "itabirito": "Itabirito",
    "lorena": "Lorena",
}


class ArquivoBIInvalido(ValueError):
    """Indica que a exportação não pode ser comparada com segurança."""


@dataclass(frozen=True)
class ComparacaoBI:
    matriculas_crm: pd.DataFrame
    matriculas_bi: pd.DataFrame
    somente_crm: pd.DataFrame
    somente_bi: pd.DataFrame
    unidades: tuple[str, ...]
    linhas_arquivo: int
    duplicidades_bi: pd.DataFrame

    @property
    def em_ambas(self) -> int:
        chaves_crm = set(self.matriculas_crm[INSCRICAO_KEY].dropna())
        chaves_bi = set(self.matriculas_bi[INSCRICAO_KEY].dropna())
        return len(chaves_crm & chaves_bi)


def _normalizar_texto(valor) -> str:
    if pd.isna(valor):
        return ""
    texto = unicodedata.normalize("NFKD", str(valor).strip().casefold())
    return "".join(char for char in texto if not unicodedata.combining(char))


def _localizar_coluna(df: pd.DataFrame, nomes: set[str]) -> str | None:
    nomes_normalizados = {_normalizar_texto(nome) for nome in nomes}
    return next(
        (
            coluna
            for coluna in df.columns
            if _normalizar_texto(coluna) in nomes_normalizados
        ),
        None,
    )


def carregar_csv_bi(conteudo: bytes) -> pd.DataFrame:
    """Lê CSV com separador detectado e os encodings usuais do Power BI."""
    if not conteudo:
        raise ArquivoBIInvalido("O arquivo enviado está vazio.")

    ultimo_erro: Exception | None = None
    for encoding in ("utf-8-sig", "cp1252"):
        try:
            dataframe = pd.read_csv(
                BytesIO(conteudo),
                encoding=encoding,
                sep=None,
                engine="python",
            )
            break
        except (UnicodeDecodeError, pd.errors.ParserError) as exc:
            ultimo_erro = exc
    else:
        raise ArquivoBIInvalido(
            "Não foi possível ler o CSV. Exporte-o novamente em UTF-8."
        ) from ultimo_erro

    coluna_inscricao = _localizar_coluna(
        dataframe,
        {"Numero Inscricao", "Número de Inscrição", "Numero de Inscricao"},
    )
    if coluna_inscricao is None:
        raise ArquivoBIInvalido(
            "O CSV não contém a coluna 'Numero Inscricao'."
        )

    renomear = {coluna_inscricao: COLUNA_INSCRICAO_BI}
    coluna_unidade = _localizar_coluna(dataframe, {"Unidade"})
    if coluna_unidade is not None:
        renomear[coluna_unidade] = COLUNA_UNIDADE_BI
    return dataframe.rename(columns=renomear)


def comparar_matriculas_bi(
    matriculas_crm: pd.DataFrame,
    arquivo_bi: pd.DataFrame,
) -> ComparacaoBI:
    """Compara inscrições únicas, limitando o CRM às unidades presentes no CSV."""
    bi = arquivo_bi.copy()
    bi[INSCRICAO_KEY] = (
        bi[COLUNA_INSCRICAO_BI]
        .astype("string")
        .str.strip()
        .str.upper()
        .replace("", pd.NA)
    )
    linhas_arquivo = len(bi)
    bi = bi.dropna(subset=[INSCRICAO_KEY]).copy()
    duplicidades = bi.loc[bi.duplicated(INSCRICAO_KEY, keep=False)].copy()
    bi = bi.drop_duplicates(INSCRICAO_KEY, keep="first")

    unidades: tuple[str, ...] = ()
    if COLUNA_UNIDADE_BI in bi:
        valores_unidade = {
            _normalizar_texto(valor)
            for valor in bi[COLUNA_UNIDADE_BI].dropna()
            if str(valor).strip()
        }
        desconhecidas = sorted(valores_unidade - set(UNIDADES_CONHECIDAS))
        if desconhecidas:
            raise ArquivoBIInvalido(
                "Unidade(s) não reconhecida(s) no CSV: "
                + ", ".join(desconhecidas)
                + "."
            )
        unidades = tuple(sorted(UNIDADES_CONHECIDAS[valor] for valor in valores_unidade))

    crm = matriculas_crm.copy()
    if unidades:
        if "Unidade Lead" not in crm:
            raise ArquivoBIInvalido(
                "As matrículas do CRM não possuem a unidade necessária para o recorte."
            )
        crm = crm.loc[crm["Unidade Lead"].astype("string").isin(unidades)].copy()

    chaves_crm = set(crm[INSCRICAO_KEY].dropna())
    chaves_bi = set(bi[INSCRICAO_KEY].dropna())
    somente_crm = crm.loc[crm[INSCRICAO_KEY].isin(chaves_crm - chaves_bi)].copy()
    somente_bi = bi.loc[bi[INSCRICAO_KEY].isin(chaves_bi - chaves_crm)].copy()

    return ComparacaoBI(
        matriculas_crm=crm,
        matriculas_bi=bi,
        somente_crm=somente_crm,
        somente_bi=somente_bi,
        unidades=unidades,
        linhas_arquivo=linhas_arquivo,
        duplicidades_bi=duplicidades,
    )
