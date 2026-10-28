"""Leitura e reconciliação de exportações do Power BI com o CRM."""

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
    "Lagoa Santa": "LAGOA SANTA",
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


def _normalizar_unidade(valor) -> str | None:
    texto = _normalizar_texto(valor)
    if texto in UNIDADES_CONHECIDAS:
        return UNIDADES_CONHECIDAS[texto]

    if "medicina" in texto:
        unidades_encontradas = [
            unidade
            for identificador, unidade in UNIDADES_CONHECIDAS.items()
            if identificador in texto
        ]
        if len(unidades_encontradas) == 1:
            return f"Medicina - {unidades_encontradas[0]}"

    return None


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

    return _validar_colunas_bi(dataframe, "CSV")


def carregar_arquivo_bi(conteudo: bytes, nome_arquivo: str) -> pd.DataFrame:
    """Lê uma exportação CSV ou XLSX do Power BI."""
    if not conteudo:
        raise ArquivoBIInvalido("O arquivo enviado está vazio.")

    extensao = nome_arquivo.rsplit(".", maxsplit=1)[-1].casefold()
    if extensao == "csv":
        return carregar_csv_bi(conteudo)
    if extensao == "xlsx":
        try:
            dataframe = pd.read_excel(BytesIO(conteudo))
        except (ValueError, OSError, ImportError) as exc:
            raise ArquivoBIInvalido(
                "Não foi possível ler o XLSX. Exporte-o novamente pelo Power BI."
            ) from exc
        return _validar_colunas_bi(dataframe, "XLSX")

    raise ArquivoBIInvalido("Formato não aceito. Envie um arquivo CSV ou XLSX.")


def _validar_colunas_bi(dataframe: pd.DataFrame, formato: str) -> pd.DataFrame:
    coluna_inscricao = _localizar_coluna(
        dataframe,
        {"Numero Inscricao", "Número de Inscrição", "Numero de Inscricao"},
    )
    if coluna_inscricao is None:
        raise ArquivoBIInvalido(
            f"O {formato} não contém a coluna 'Numero Inscricao'."
        )

    renomear = {coluna_inscricao: COLUNA_INSCRICAO_BI}
    coluna_unidade = _localizar_coluna(dataframe, {"Unidade"})
    if coluna_unidade is not None:
        renomear[coluna_unidade] = COLUNA_UNIDADE_BI
    return dataframe.rename(columns=renomear)


def comparar_matriculas_bi(
    matriculas_crm: pd.DataFrame,
    arquivo_bi: pd.DataFrame,
    matriculas_medicina: pd.DataFrame | None = None,
) -> ComparacaoBI:
    """Compara inscrições únicas, incluindo Medicina quando sua base é informada."""
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
            str(valor).strip()
            for valor in bi[COLUNA_UNIDADE_BI].dropna()
            if str(valor).strip()
        }
        unidades_normalizadas = {
            valor: _normalizar_unidade(valor) for valor in valores_unidade
        }
        desconhecidas = sorted(
            valor
            for valor, unidade in unidades_normalizadas.items()
            if unidade is None
        )
        if desconhecidas:
            raise ArquivoBIInvalido(
                "Unidade(s) não reconhecida(s) no CSV: "
                + ", ".join(desconhecidas)
                + "."
            )
        unidades = tuple(
            sorted(
                {
                    unidade
                    for unidade in unidades_normalizadas.values()
                    if unidade is not None
                }
            )
        )

    crm = matriculas_crm.copy()
    if matriculas_medicina is not None:
        crm = pd.concat([crm, matriculas_medicina], ignore_index=True)
        crm = crm.drop_duplicates(INSCRICAO_KEY, keep="first")
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
