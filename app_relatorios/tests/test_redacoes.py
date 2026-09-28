import json

import pandas as pd
from pandas.api.types import is_datetime64_any_dtype

from services import redacoes
from services.crm_api import CrmSettings


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
            "Observações": [None, None],
            "Corrigido por": [None, None],
            "Data da correção": pd.Series(
                [pd.NaT, pd.NaT], dtype="datetime64[s, America/Sao_Paulo]"
            ),
        }
    )
    progresso = []

    resultado = redacoes.corrigir_redacoes(
        entrada,
        "chave",
        "modelo",
        ao_corrigir=lambda atual, total: progresso.append((atual, total)),
        corretor=lambda texto, tema, chave, modelo: (
            (8, "Boa abordagem do tema")
            if tema == "Educação" and texto.startswith("Primeiro")
            else (9, "Argumentação consistente")
        ),
    )

    assert entrada["Nota"].isna().all()
    assert resultado["Nota"].tolist() == [8, 9]
    assert resultado["Observações"].tolist() == [
        "Boa abordagem do tema",
        "Argumentação consistente",
    ]
    assert resultado["Corrigido por"].tolist() == ["IA Trivento", "IA Trivento"]
    assert str(resultado["Data da correção"].dtype) == (
        "datetime64[s, America/Sao_Paulo]"
    )
    assert resultado["Data da correção"].notna().all()
    assert progresso == [(1, 2), (2, 2)]


def test_vincula_cpf_pela_inscricao_atual_normalizada():
    entregues = pd.DataFrame(
        {
            "Inscrição": [" can-001 ", "CAN-002", "CAN-SEM-LEAD"],
            "Nota": [8, 9, 7],
        }
    )
    leads = pd.DataFrame(
        {
            "Inscrição Atual": ["CAN-001", "can-002", "CAN-003"],
            "CPF Lead": ["111.111.111-11", "222.222.222-22", "333.333.333-33"],
        }
    )

    resultado = redacoes.vincular_redacoes_a_leads(entregues, leads)

    assert resultado["CPF Lead"].iloc[:2].tolist() == [
        "111.111.111-11",
        "222.222.222-22",
    ]
    assert pd.isna(resultado["CPF Lead"].iloc[2])
    assert "_inscricao_key" not in resultado


def test_envia_correcao_ao_crm_e_sinaliza_linha_sem_cpf(monkeypatch):
    chamadas = []

    class Resposta:
        def __init__(self, corpo):
            self.corpo = corpo

        def raise_for_status(self):
            pass

        def json(self):
            return self.corpo

    class Sessao:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            pass

        def post(self, url, **kwargs):
            chamadas.append((url, kwargs))
            if url.endswith("/api/token"):
                return Resposta({"access_token": "token-teste"})
            return Resposta({"TrackId": "track-123", "Erros": []})

    monkeypatch.setattr(redacoes.requests, "Session", Sessao)
    progresso = []
    entrada = pd.DataFrame(
        {
            "Inscrição": ["CAN-001", "CAN-002"],
            "CPF Lead": ["111.111.111-11", pd.NA],
            "Data da correção": pd.to_datetime(
                ["2026-09-28 10:30:00", "2026-09-28 11:00:00"]
            ),
            "Nota": [8.5, 7],
            "Observações": ["Bom texto.", "Texto adequado."],
            "Texto da redação": ["Conteúdo integral da redação.", "Outro texto."],
            "Total de caracteres": [3050, 2000],
        }
    )

    resultado = redacoes.enviar_correcoes_crm(
        entrada,
        CrmSettings("https://crm.example", "usuario", "senha"),
        ao_enviar=lambda atual, total: progresso.append((atual, total)),
    )

    assert resultado["Status"].tolist() == ["Enviado", "Não enviado"]
    assert progresso == [(1, 2), (2, 2)]
    assert len(chamadas) == 2
    url, kwargs = chamadas[1]
    assert url == (
        "https://crm.example/api/IntegracaoGenericaClientes/CadastroInscricao"
    )
    assert kwargs["headers"]["Authorization"] == "Bearer token-teste"
    atributos = kwargs["json"]["lead"]["attributes"]
    assert atributos == {
        "cad_cpf": "111.111.111-11",
        "crmeduc_redacaotrivento": "Conteúdo integral da redação.",
        "crmeduc_datacorrecaoredacaotrivento": "28/09/2026",
        "crmeduc_notatriventoredacao": "8,5",
        "crmeduc_observacaodaredacaotrivento": "Bom texto.",
        "crmeduc_totaldecaracterescorrecaoredacaotrivento": 3050,
    }
    assert kwargs["json"]["concurso"]["attributes"]["cad_codigo"] == 1005


def test_chamada_openrouter_pede_nota_estruturada(monkeypatch):
    chamada = {}

    class Resposta:
        def raise_for_status(self):
            pass

        def json(self):
            return {
                "choices": [
                    {
                        "message": {
                            "content": json.dumps(
                                {
                                    "nota": 8.5,
                                    "comentario": "Atendeu ao tema e apresentou bons argumentos.",
                                }
                            )
                        }
                    }
                ]
            }

    def post(url, **kwargs):
        chamada.update(url=url, **kwargs)
        return Resposta()

    monkeypatch.setattr(redacoes.requests, "post", post)

    nota, comentario = redacoes.corrigir_redacao(
        "Minha redação", "O papel da educação", "segredo", "modelo/teste"
    )

    assert nota == 8.5
    assert comentario == "Atendeu ao tema e apresentou bons argumentos."
    assert chamada["headers"]["Authorization"] == "Bearer segredo"
    assert chamada["json"]["model"] == "modelo/teste"
    mensagens = chamada["json"]["messages"]
    assert "fuga total ou parcial" in mensagens[0]["content"]
    assert "Tema da redação:\nO papel da educação" in mensagens[1]["content"]
    assert "Texto da redação:\nMinha redação" in mensagens[1]["content"]
    schema = chamada["json"]["response_format"]["json_schema"]["schema"]
    assert schema["properties"]["nota"]["minimum"] == 0
    assert schema["properties"]["nota"]["maximum"] == 100
    assert schema["properties"]["comentario"]["minLength"] == 1
    assert schema["required"] == ["nota", "comentario"]


def test_gera_arquivo_excel():
    arquivo = redacoes.dataframe_para_excel(
        pd.DataFrame(
            {
                "Id": ["1"],
                "Nota": [8.5],
                "Corrigido por": ["IA Trivento"],
                "Observações": ["Atendeu ao tema e apresentou bons argumentos."],
                "Data da correção": pd.Series(
                    ["2026-09-24 10:00:00"], dtype="datetime64[s]"
                ).dt.tz_localize("America/Sao_Paulo"),
            }
        )
    )

    assert arquivo.startswith(b"PK")
