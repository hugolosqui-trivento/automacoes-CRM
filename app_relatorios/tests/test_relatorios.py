import pandas as pd

from services.relatorios import gerar_relatorios


MAPA = {"Dona A": "Ana", "Dono B": "Bruno"}


def _fontes():
    leads = pd.DataFrame(
        [
            {
                "Inscrição Atual": "OUTRA-INSCRICAO",
                "ID Lead": "{L1}",
                "Nome Lead": "Lead 1",
                "Proprietário": None,
                "Data Criação Lead": "2026-08-01",
            },
            {
                "Inscrição Atual": "CAN-002",
                "ID Lead": "L2",
                "Nome Lead": "Lead 2",
                "Proprietário": "Dona A",
                "Data Criação Lead": "2026-08-02",
            },
            {
                "Inscrição Atual": "CAN-004",
                "ID Lead": "L4",
                "Nome Lead": "Lead 4",
                "Proprietário": "Proprietário Novo",
                "Data Criação Lead": "2026-08-04",
            },
        ]
    )
    inscricoes = pd.DataFrame(
        [
            {"Numero Inscricao": "CAN-001", "ID Lead Inscrição": "l1", "Situação Inscrição": "Matriculado", "Curso ID": "Direito"},
            {"Numero Inscricao": "CAN-002 ", "ID Lead Inscrição": "{L2}", "Situação Inscrição": "Matriculado", "Curso ID": "Direito"},
            {"Numero Inscricao": "CAN-003", "ID Lead Inscrição": "L3", "Situação Inscrição": "Matriculado", "Curso ID": "Direito"},
            {"Numero Inscricao": "CAN-004", "ID Lead Inscrição": "L4", "Situação Inscrição": "Matriculado", "Curso ID": "Direito"},
            {"Numero Inscricao": "CAN-005", "ID Lead Inscrição": "L5", "Situação Inscrição": "Matriculado", "Curso ID": "Medicina"},
            {"Numero Inscricao": "CAN-001", "ID Lead Inscrição": "L1", "Situação Inscrição": "Matriculado", "Curso ID": "Direito"},
        ]
    )
    planilha = pd.DataFrame(
        [
            {"Número de Inscrição": "CAN-001", "CONSULTOR (a)": "Ana", "Unidade": "A"},
            {"Número de Inscrição": "CAN-002", "CONSULTOR (a)": "Bruno", "Unidade": "A"},
            {"Número de Inscrição": "CAN-004", "CONSULTOR (a)": "Ana", "Unidade": "A"},
            {"Número de Inscrição": "CAN-999", "CONSULTOR (a)": "Ana", "Unidade": "B"},
        ]
    )
    return leads, inscricoes, planilha


def test_reconciliacao_normaliza_deduplica_e_exclui_medicina():
    rel = gerar_relatorios(*_fontes(), MAPA, {"Bruno"})

    assert len(rel.matriculas_crm) == 4
    assert len(rel.matriculas_planilha) == 4
    assert len(rel.duplicidades_crm) == 2
    assert set(rel.somente_crm["Numero Inscricao"]) == {"CAN-003"}
    assert set(rel.somente_planilha["Número de Inscrição"]) == {"CAN-999"}


def test_sem_proprietario_distingue_lead_ausente_e_caso_acionavel():
    rel = gerar_relatorios(*_fontes(), MAPA, {"Bruno"})

    assert len(rel.sem_proprietario) == 2
    assert set(rel.sem_proprietario["Motivo"]) == {
        "Lead sem proprietário",
        "Inscrição sem lead correspondente",
    }
    assert len(rel.casos_acionaveis) == 1
    assert rel.casos_acionaveis.iloc[0]["ID Lead"] == "{L1}"
    assert rel.casos_acionaveis.iloc[0]["Inscrição Atual"] == "OUTRA-INSCRICAO"


def test_divergencias_ignoram_consultor_e_separam_proprietario_nao_mapeado():
    rel = gerar_relatorios(*_fontes(), MAPA, {"Bruno"})

    assert rel.divergencias.empty
    assert len(rel.proprietarios_nao_mapeados) == 1
    assert rel.proprietarios_nao_mapeados.iloc[0]["Proprietário"] == "Proprietário Novo"

