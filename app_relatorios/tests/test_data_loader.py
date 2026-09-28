from threading import Barrier, Lock, get_ident

import pandas as pd

import data_loader
from services.planilha_matriculas import carregar_planilha_medicina
from services.crm_api import CrmSettings
from settings import AppSettings


def test_carrega_uma_fonte_por_thread(monkeypatch):
    barrier = Barrier(3)
    lock = Lock()
    threads_por_fonte = {}

    def registrar(fonte):
        with lock:
            threads_por_fonte[fonte] = get_ident()
        barrier.wait(timeout=2)
        return pd.DataFrame({"fonte": [fonte]})

    class FakeCrmClient:
        def __init__(self, settings):
            pass

        def fetch_entity(self, entity, attributes, rename, text_attributes=()):
            return registrar(entity)

    monkeypatch.setattr(data_loader, "CrmClient", FakeCrmClient)
    monkeypatch.setattr(
        data_loader,
        "carregar_planilha",
        lambda url, abas: registrar("planilha"),
    )
    settings = AppSettings(
        crm=CrmSettings("https://crm.example", "usuario", "senha"),
        matriculas_url="https://example.com/matriculas.xlsx",
        app_env="development",
        app_password="",
    )

    leads, inscricoes, planilha = data_loader._carregar_fontes(settings)

    assert leads.iloc[0]["fonte"] == "lead"
    assert inscricoes.iloc[0]["fonte"] == "cad_inscricaocandidato"
    assert planilha.iloc[0]["fonte"] == "planilha"
    assert len(set(threads_por_fonte.values())) == 3


def test_carrega_e_concatena_as_abas_de_medicina(monkeypatch):
    chamadas = []

    def ler_aba(url, sheet_name):
        chamadas.append((url, sheet_name))
        return pd.DataFrame({"Número de Inscrição": [sheet_name]})

    monkeypatch.setattr(
        "services.planilha_matriculas.pd.read_excel", ler_aba
    )

    resultado = carregar_planilha_medicina(
        "https://example.com/medicina.xlsx",
        {
            "MEDICINA LORENA": "Medicina - Lorena",
            "MEDICINA ALTAMIRA": "Medicina - Altamira",
        },
    )

    assert chamadas == [
        ("https://example.com/medicina.xlsx", "MEDICINA LORENA"),
        ("https://example.com/medicina.xlsx", "MEDICINA ALTAMIRA"),
    ]
    assert resultado["Número de Inscrição"].tolist() == [
        "MEDICINA LORENA",
        "MEDICINA ALTAMIRA",
    ]
    assert resultado["Unidade Lead"].tolist() == [
        "Medicina - Lorena",
        "Medicina - Altamira",
    ]


def test_filtra_leads_de_redacao_pelas_escolas_parceiras():
    leads = pd.DataFrame(
        {
            "Inscrição Atual": ["CAN-001", "CAN-002", "CAN-003"],
            "CPF Lead": ["111", "222", "333"],
            "Escola Lorena": ["Escola A", None, "  "],
        }
    )

    resultado = data_loader._filtrar_leads_escolas_parceiras(leads)

    assert resultado["Inscrição Atual"].tolist() == ["CAN-001"]
