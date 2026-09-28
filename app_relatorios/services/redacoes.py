"""Consulta e correção das redações entregues pelo CRM."""

from __future__ import annotations

from collections.abc import Callable
from io import BytesIO
import json

import pandas as pd
import requests

from services.crm_api import CrmApiError, CrmClient, CrmSettings


OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"
MODELO_PADRAO = "openai/gpt-4o-mini"
CAMINHO_ENVIO_CRM = "/api/IntegracaoGenericaClientes/CadastroInscricao"
CODIGO_CONCURSO_REDACAO = 1005

CRITERIOS = """
Avalie a redação considerando, de forma equilibrada:
- coerência temática;
- coesão textual;
- abrangência do conteúdo;
- correção gramatical;
- qualidade geral da escrita.

A nota deve estar entre 0 e 100.
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


def _normalizar_inscricao(serie: pd.Series) -> pd.Series:
    return serie.astype("string").str.strip().str.upper().replace("", pd.NA)


def vincular_redacoes_a_leads(
    redacoes: pd.DataFrame,
    leads: pd.DataFrame,
) -> pd.DataFrame:
    """Associa o CPF do lead usando Inscrição × Inscrição Atual."""
    resultado = redacoes.copy()
    resultado["_inscricao_key"] = _normalizar_inscricao(
        resultado.get(
            "Inscrição", pd.Series(pd.NA, index=resultado.index, dtype="string")
        )
    )

    candidatos = leads.copy()
    candidatos["_inscricao_key"] = _normalizar_inscricao(
        candidatos.get(
            "Inscrição Atual",
            pd.Series(pd.NA, index=candidatos.index, dtype="string"),
        )
    )
    cpf = candidatos.get(
        "CPF Lead", pd.Series(pd.NA, index=candidatos.index, dtype="string")
    )
    candidatos = candidatos.loc[
        candidatos["_inscricao_key"].notna()
        & cpf.notna()
        & cpf.astype("string").str.strip().ne("")
    ].drop_duplicates("_inscricao_key", keep="first")

    resultado = resultado.merge(
        candidatos[["_inscricao_key", "CPF Lead"]],
        on="_inscricao_key",
        how="left",
        validate="many_to_one",
    )
    return resultado.drop(columns="_inscricao_key")


def corrigir_redacao(
    texto_redacao: str,
    tema_redacao: str,
    api_key: str,
    modelo: str = MODELO_PADRAO,
) -> tuple[float, str]:
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
                    "content": (
                        f"Você é um corretor de redações. {CRITERIOS}\n\n"
                        "Compare o texto ao tema proposto e considere fuga total ou "
                        "parcial ao tema na nota. Forneça também um comentário objetivo "
                        "que explique a nota atribuída, destacando os principais acertos "
                        "e pontos a melhorar."
                    ),
                },
                {
                    "role": "user",
                    "content": (
                        f"Tema da redação:\n{tema_redacao}\n\n"
                        f"Texto da redação:\n{texto_redacao}"
                    ),
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
                            "nota": {"type": "number", "minimum": 0, "maximum": 100},
                            "comentario": {"type": "string", "minLength": 1},
                        },
                        "required": ["nota", "comentario"],
                        "additionalProperties": False,
                    },
                },
            },
        },
        timeout=60,
    )
    resposta.raise_for_status()
    conteudo = resposta.json()["choices"][0]["message"]["content"]
    correcao = json.loads(conteudo)
    return float(correcao["nota"]), str(correcao["comentario"]).strip()


def corrigir_redacoes(
    dataframe: pd.DataFrame,
    api_key: str,
    modelo: str = MODELO_PADRAO,
    ao_corrigir: Callable[[int, int], None] | None = None,
    corretor: Callable[[str, str, str, str], tuple[float, str]] = corrigir_redacao,
) -> pd.DataFrame:
    """Corrige uma cópia do dataframe e informa o progresso após cada redação."""
    resultado = dataframe.copy()
    total = len(resultado)

    for concluida, (indice, linha) in enumerate(resultado.iterrows(), start=1):
        texto = str(linha.get("Texto da redação", "")).strip()
        if not texto or texto.casefold() in {"nan", "none", "<na>"}:
            raise ValueError(f"A redação da linha {indice + 1} não possui texto.")
        tema = str(linha.get("Tema da redação", "")).strip()
        if not tema or tema.casefold() in {"nan", "none", "<na>"}:
            raise ValueError(f"A redação da linha {indice + 1} não possui tema.")
        nota, comentario = corretor(texto, tema, api_key, modelo)
        if not comentario:
            raise ValueError(
                f"A IA não forneceu um comentário para a redação da linha {indice + 1}."
            )
        resultado.at[indice, "Nota"] = nota
        resultado.at[indice, "Observações"] = comentario
        resultado.at[indice, "Corrigido por"] = "IA Trivento"
        resultado.at[indice, "Data da correção"] = pd.Timestamp.now(
            tz="America/Sao_Paulo"
        ).floor("s")
        if ao_corrigir is not None:
            ao_corrigir(concluida, total)

    return resultado


def _valor_preenchido(valor) -> bool:
    return not pd.isna(valor) and str(valor).strip() != ""


def _formatar_nota_crm(valor) -> str:
    """Formata decimal no padrão aceito pela Integração Genérica do CRM."""
    numero = float(valor)
    if pd.isna(numero):
        raise ValueError("Nota inválida.")
    return f"{numero:g}".replace(".", ",")


def montar_payload_correcao(linha: pd.Series) -> dict:
    """Monta o contrato usado pelo endpoint CadastroInscricao do CRM."""
    data_correcao = pd.to_datetime(linha["Data da correção"], errors="coerce")
    if pd.isna(data_correcao):
        raise ValueError("Data da correção inválida.")

    return {
        "concurso": {"attributes": {"cad_codigo": CODIGO_CONCURSO_REDACAO}},
        "lead": {
            "attributes": {
                "cad_cpf": str(linha["CPF Lead"]).strip(),
                "crmeduc_redacaotrivento": str(linha["Texto da redação"]).strip(),
                "crmeduc_datacorrecaoredacaotrivento": data_correcao.strftime(
                    "%d/%m/%Y"
                ),
                "crmeduc_notatriventoredacao": _formatar_nota_crm(linha["Nota"]),
                "crmeduc_observacaodaredacaotrivento": str(
                    linha["Observações"]
                ).strip(),
                "crmeduc_totaldecaracterescorrecaoredacaotrivento": int(
                    linha["Total de caracteres"]
                ),
            }
        },
        "inscricao": {"attributes": {}},
    }


def enviar_correcoes_crm(
    dataframe: pd.DataFrame,
    settings: CrmSettings,
    ao_enviar: Callable[[int, int], None] | None = None,
) -> pd.DataFrame:
    """Envia as correções ao CRM e devolve o resultado individual de cada linha."""
    colunas_obrigatorias = {
        "Inscrição",
        "CPF Lead",
        "Data da correção",
        "Nota",
        "Observações",
        "Texto da redação",
        "Total de caracteres",
    }
    faltantes = colunas_obrigatorias.difference(dataframe.columns)
    if faltantes:
        raise ValueError(
            "Colunas obrigatórias ausentes para envio: " + ", ".join(sorted(faltantes))
        )

    total = len(dataframe)
    resultados = []
    endpoint = f"{settings.base_url.rstrip('/')}{CAMINHO_ENVIO_CRM}"

    try:
        with requests.Session() as session:
            token = CrmClient(settings)._token(session)
            headers = {
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json",
            }

            for posicao, (_, linha) in enumerate(dataframe.iterrows(), start=1):
                inscricao = linha.get("Inscrição")
                cpf = linha.get("CPF Lead")
                status = "Não enviado"
                detalhe = "CPF não localizado pela inscrição atual do lead."

                if _valor_preenchido(cpf):
                    try:
                        resposta = session.post(
                            endpoint,
                            headers=headers,
                            json=montar_payload_correcao(linha),
                            timeout=60,
                        )
                        resposta.raise_for_status()
                        corpo = resposta.json()
                        erros = corpo.get("Erros", []) if isinstance(corpo, dict) else []
                        if erros:
                            status = "Erro"
                            detalhe = json.dumps(erros, ensure_ascii=False)
                        else:
                            status = "Enviado"
                            detalhe = str(
                                corpo.get("TrackId", "Envio confirmado pelo CRM")
                                if isinstance(corpo, dict)
                                else "Envio confirmado pelo CRM"
                            )
                    except (requests.RequestException, ValueError, TypeError, KeyError) as exc:
                        status = "Erro"
                        detalhe = str(exc)

                resultados.append(
                    {
                        "Inscrição": inscricao,
                        "CPF Lead": cpf,
                        "Status": status,
                        "Detalhe": detalhe,
                    }
                )
                if ao_enviar is not None:
                    ao_enviar(posicao, total)
    except (requests.RequestException, KeyError, ValueError) as exc:
        raise CrmApiError(f"Não foi possível autenticar no CRM: {exc}") from exc

    return pd.DataFrame(resultados)


def dataframe_para_excel(dataframe: pd.DataFrame) -> bytes:
    exportacao = dataframe.copy()
    # exportar apenas as seguintes colunas: Id, Nota, Corrigido por, Observações, Data da correção
    exportacao = exportacao[["Id", "Nota", "Corrigido por", "Observações", "Data da correção"]]
    for coluna in exportacao.select_dtypes(include=["datetimetz"]).columns:
        exportacao[coluna] = exportacao[coluna].dt.tz_localize(None)
    arquivo = BytesIO()
    with pd.ExcelWriter(arquivo, engine="openpyxl") as writer:
        exportacao.to_excel(writer, sheet_name="Redações corrigidas", index=False)
    return arquivo.getvalue()
