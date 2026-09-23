import json
import os

import requests
from dotenv import load_dotenv


OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"
MODELO = "openai/gpt-4o-mini"

CRITERIOS = """
Avalie a redação considerando, de forma equilibrada:
- coerência temática;
- abrangência do conteúdo;
- correção gramatical;
- qualidade geral da escrita.

A nota deve estar entre 1 e 10.
""".strip()


def corrigir_redacao(texto_redacao):
    load_dotenv()

    resposta = requests.post(
        OPENROUTER_URL,
        headers={
            "Authorization": f"Bearer {os.environ['OPENROUTER_KEY']}",
            "Content-Type": "application/json",
        },
        json={
            "model": MODELO,
            "temperature": 0,
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "Você é um corretor de redações. "
                        f"{CRITERIOS}"
                    ),
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
                            "nota": {
                                "type": "number",
                                "minimum": 1,
                                "maximum": 10,
                            }
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
    return json.loads(conteudo)["nota"]
