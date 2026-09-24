import json

import pandas as pd
from pandas.api.types import is_datetime64_any_dtype

from services import redacoes


def test_prepara_somente_redacoes_entregues_e_renomeia_colunas():
    entrada = pd.DataFrame(
        {
            "cad_redacaoid": ["{ABC}", "{DEF}"],
            "cad_situacao": ["Entregue", "Pendente"],
            "cad_dataentrega": ["2026-09-23T19:14:30-03:00", None],
            "cad_nota": ["7.5", None],
            "cad_textoredacao": ["Texto entregue", "Rascunho"],
        }
    )

    resultado = redacoes.preparar_redacoes(entrada)

    assert resultado["Id"].tolist() == ["ABC"]
    assert resultado["Situação"].tolist() == ["Entregue"]
    assert resultado["Nota"].tolist() == [7.5]
    assert is_datetime64_any_dtype(resultado["Data de entrega"])
    assert str(resultado["Data de entrega"].dt.tz) == "America/Sao_Paulo"


def test_corrige_dataframe_sem_alterar_original():
    entrada = pd.DataFrame(
        {
            "Id": ["1", "2"],
            "Tema da redação": ["Educação", "Meio ambiente"],
            "Texto da redação": ["Primeiro texto", "Segundo texto"],
            "Nota": [None, None],
            "Corrigido por": [None, None],
        }
    )
    progresso = []

    resultado = redacoes.corrigir_redacoes(
        entrada,
        "chave",
        "modelo",
        ao_corrigir=lambda atual, total: progresso.append((atual, total)),
        corretor=lambda texto, tema, chave, modelo: (
            8 if tema == "Educação" and texto.startswith("Primeiro") else 9
        ),
    )

    assert entrada["Nota"].isna().all()
    assert resultado["Nota"].tolist() == [8, 9]
    assert resultado["Corrigido por"].tolist() == ["IA Trivento", "IA Trivento"]
    assert progresso == [(1, 2), (2, 2)]


def test_chamada_openrouter_pede_nota_estruturada(monkeypatch):
    chamada = {}

    class Resposta:
        def raise_for_status(self):
            pass

        def json(self):
            return {"choices": [{"message": {"content": json.dumps({"nota": 8.5})}}]}

    def post(url, **kwargs):
        chamada.update(url=url, **kwargs)
        return Resposta()

    monkeypatch.setattr(redacoes.requests, "post", post)

    nota = redacoes.corrigir_redacao(
        "Minha redação", "O papel da educação", "segredo", "modelo/teste"
    )

    assert nota == 8.5
    assert chamada["headers"]["Authorization"] == "Bearer segredo"
    assert chamada["json"]["model"] == "modelo/teste"
    mensagens = chamada["json"]["messages"]
    assert "fuga total ou parcial" in mensagens[0]["content"]
    assert "Tema da redação:\nO papel da educação" in mensagens[1]["content"]
    assert "Texto da redação:\nMinha redação" in mensagens[1]["content"]
    schema = chamada["json"]["response_format"]["json_schema"]["schema"]
    assert schema["properties"]["nota"]["minimum"] == 1
    assert schema["properties"]["nota"]["maximum"] == 10


def test_gera_arquivo_excel():
    arquivo = redacoes.dataframe_para_excel(
        pd.DataFrame(
            {
                "Nota": [8.5],
                "Data de entrega": pd.to_datetime(
                    ["2026-09-23T19:14:30-03:00"], utc=True
                ).tz_convert("America/Sao_Paulo"),
            }
        )
    )

    assert arquivo.startswith(b"PK")
