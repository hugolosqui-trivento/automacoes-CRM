from threading import Barrier, Lock, get_ident

import pandas as pd

import data_loader
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
