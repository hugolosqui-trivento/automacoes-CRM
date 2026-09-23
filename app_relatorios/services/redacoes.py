"""Consulta e correção das redações entregues pelo CRM."""

from __future__ import annotations

from collections.abc import Callable
from io import BytesIO
import json

import pandas as pd
import requests

from services.crm_api import CrmClient, CrmSettings


OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"
MODELO_PADRAO = "openai/gpt-4o-mini"

CRITERIOS = """
Avalie a redação considerando, de forma equilibrada:
- coerência temática;
- abrangência do conteúdo;
- correção gramatical;
- qualidade geral da escrita.

A nota deve estar entre 1 e 10.
""".strip()

REDACAO_ATTRIBUTES = (
    "cad_redacaoid",
    "cad_name",
    "cad_redacaocomentarios",
    "cad_corrigidopor",
    "cad_datacorrecao",
    "cad_dataentrega",
    "cad_datainicio",
    "cad_datalimitetermino",
    "cad_dataretorno",
    "cad_inscricao_redacao",
    "cad_maximocaracteres",
    "cad_minimocaracteres",
    "cad_minimocaracterespreenchidos",
    "cad_nota",
    "cad_situacao",
    "cad_observacoes",
    "cad_temasredacao_redacao",
    "cad_textoredacao",
    "cad_totaldecaracteres",
)

REDACAO_RENAME = {
    "cad_redacaoid": "Id",
    "cad_name": "Assunto",
    "cad_redacaocomentarios": "Comentários",
    "cad_corrigidopor": "Corrigido por",
    "cad_datacorrecao": "Data da correção",
    "cad_dataentrega": "Data de entrega",
    "cad_datainicio": "Data de início",
    "cad_datalimitetermino": "Data limite para o término",
    "cad_dataretorno": "Data de retorno",
    "cad_inscricao_redacao": "Inscrição",
    "cad_maximocaracteres": "Máximo de caracteres",
    "cad_minimocaracteres": "Mínimo de caracteres",
    "cad_minimocaracterespreenchidos": "Mínimo de caracteres preenchidos",
    "cad_nota": "Nota",
    "cad_situacao": "Situação",
    "cad_observacoes": "Observações",
    "cad_temasredacao_redacao": "Tema da redação",
    "cad_textoredacao": "Texto da redação",
    "cad_totaldecaracteres": "Total de caracteres",
}


def preparar_redacoes(dataframe: pd.DataFrame) -> pd.DataFrame:
    """Mantém apenas entregues e aplica os tratamentos do fluxo original."""
    if dataframe.empty:
        return pd.DataFrame(columns=list(REDACAO_RENAME.values()))

    resultado = dataframe.copy()
    if "cad_situacao" in resultado:
        situacao = resultado["cad_situacao"].astype("string").str.strip().str.casefold()
        resultado = resultado.loc[situacao.eq("entregue")].copy()

    for coluna in [nome for nome in resultado if "data" in nome.casefold()]:
        resultado[coluna] = pd.to_datetime(
            resultado[coluna], errors="coerce", utc=True
        ).dt.tz_convert("America/Sao_Paulo")

    if "cad_redacaoid" in resultado:
        resultado["cad_redacaoid"] = (
            resultado["cad_redacaoid"]
            .astype("string")
            .str.replace("{", "", regex=False)
            .str.replace("}", "", regex=False)
        )
    if "cad_nota" in resultado:
        resultado["cad_nota"] = pd.to_numeric(resultado["cad_nota"], errors="coerce")

    return resultado.rename(columns=REDACAO_RENAME).reset_index(drop=True)


def buscar_redacoes_entregues(settings: CrmSettings) -> pd.DataFrame:
    cliente = CrmClient(settings)
    dataframe = cliente.fetch_entity("cad_redacao", REDACAO_ATTRIBUTES, {})
    return preparar_redacoes(dataframe)


def corrigir_redacao(
    texto_redacao: str,
    api_key: str,
    modelo: str = MODELO_PADRAO,
) -> float:
    resposta = requests.post(
        OPENROUTER_URL,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        json={
            "model": modelo,
            "temperature": 0,
            "messages": [
                {
                    "role": "system",
                    "content": f"Você é um corretor de redações. {CRITERIOS}",
                },
                {
                    "role": "user",
                    "content": f"Redação:\n\n{texto_redacao}",
                },
            ],
            "response_format": {
                "type": "json_schema",
                "json_schema": {
                    "name": "nota_redacao",
                    "strict": True,
                    "schema": {
                        "type": "object",
                        "properties": {
                            "nota": {"type": "number", "minimum": 1, "maximum": 10}
                        },
                        "required": ["nota"],
                        "additionalProperties": False,
                    },
                },
            },
        },
        timeout=60,
    )
    resposta.raise_for_status()
    conteudo = resposta.json()["choices"][0]["message"]["content"]
    return float(json.loads(conteudo)["nota"])


def corrigir_redacoes(
    dataframe: pd.DataFrame,
    api_key: str,
    modelo: str = MODELO_PADRAO,
    ao_corrigir: Callable[[int, int], None] | None = None,
    corretor: Callable[[str, str, str], float] = corrigir_redacao,
) -> pd.DataFrame:
    """Corrige uma cópia do dataframe e informa o progresso após cada redação."""
    resultado = dataframe.copy()
    total = len(resultado)

    for concluida, (indice, linha) in enumerate(resultado.iterrows(), start=1):
        texto = str(linha.get("Texto da redação", "")).strip()
        if not texto or texto.casefold() in {"nan", "none", "<na>"}:
            raise ValueError(f"A redação da linha {indice + 1} não possui texto.")
        resultado.at[indice, "Nota"] = corretor(texto, api_key, modelo)
        resultado.at[indice, "Corrigido por"] = "IA Trivento"
        if ao_corrigir is not None:
            ao_corrigir(concluida, total)

    return resultado


def dataframe_para_excel(dataframe: pd.DataFrame) -> bytes:
    exportacao = dataframe.copy()
    for coluna in exportacao.select_dtypes(include=["datetimetz"]).columns:
        exportacao[coluna] = exportacao[coluna].dt.tz_localize(None)

    arquivo = BytesIO()
    with pd.ExcelWriter(arquivo, engine="openpyxl") as writer:
        exportacao.to_excel(writer, sheet_name="Redações corrigidas", index=False)
    return arquivo.getvalue()
