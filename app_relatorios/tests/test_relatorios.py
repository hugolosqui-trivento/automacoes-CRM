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
                "Unidade 1": "Medicina - Itabirito",
                "Unidade 2": "Altamira",
                "Data Criação Lead": "2026-08-01",
            },
            {
                "Inscrição Atual": "CAN-002",
                "ID Lead": "L2",
                "Nome Lead": "Lead 2",
                "Proprietário": "Dona A",
                "Unidade 1": " ",
                "Unidade 2": "Altamira",
                "Data Criação Lead": "2026-08-02",
            },
            {
                "Inscrição Atual": "CAN-004",
                "ID Lead": "L4",
                "Nome Lead": "Lead 4",
                "Proprietário": "Proprietário Novo",
                "Unidade 1": None,
                "Unidade 2": "Unidade Lorena",
                "Data Criação Lead": "2026-08-04",
            },
            {
                "Inscrição Atual": "CAN-999",
                "ID Lead": "L999",
                "Nome Lead": "Lead 999",
                "Proprietário": "Dona A",
                "Unidade 1": None,
                "Unidade 2": "Altamira",
                "Data Criação Lead": "2026-08-05",
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
            {"Número de Inscrição": "CAN-001", "CONSULTOR (a)": "Ana", "Unidade": "Itabirito"},
            {"Número de Inscrição": "CAN-002", "CONSULTOR (a)": "Bruno", "Unidade": "ALTAMIRA"},
            {"Número de Inscrição": "CAN-004", "CONSULTOR (a)": "Ana", "Unidade": "Unidade Lorena"},
            {"Número de Inscrição": "CAN-999", "CONSULTOR (a)": "Ana", "Unidade": "Canaa"},
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


def test_unidade_lead_prioriza_unidade_1_e_faz_fallback_para_unidade_2():
    rel = gerar_relatorios(*_fontes(), MAPA, {"Bruno"})

    unidades_crm = rel.matriculas_crm.set_index("Numero Inscricao")["Unidade Lead"]
    assert unidades_crm["CAN-001"] == "Itabirito"
    assert unidades_crm["CAN-002 "] == "Altamira"
    assert unidades_crm["CAN-004"] == "Lorena"
    assert "Unidade Lead" in rel.somente_crm
    assert "Unidade Lead" in rel.somente_planilha
    assert rel.somente_planilha.iloc[0]["Unidade Lead"] == "Canaã"
    assert not unidades_crm.dropna().str.startswith("Medicina").any()


def test_planilha_usa_sua_propria_unidade_sem_relacionar_lead_por_inscricao():
    rel = gerar_relatorios(*_fontes(), MAPA, {"Bruno"})

    unidades_planilha = rel.matriculas_planilha.set_index("Número de Inscrição")[
        "Unidade Lead"
    ]
    assert unidades_planilha["CAN-001"] == "Itabirito"
    assert unidades_planilha["CAN-002"] == "Altamira"
    assert unidades_planilha["CAN-004"] == "Lorena"
    assert unidades_planilha["CAN-999"] == "Canaã"


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

