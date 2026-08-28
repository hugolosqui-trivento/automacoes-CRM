import pandas as pd
import pytest

from services.comparacao_bi import (
    ArquivoBIInvalido,
    carregar_csv_bi,
    comparar_matriculas_bi,
)
from services.relatorios import INSCRICAO_KEY


def _crm():
    return pd.DataFrame(
        [
            {"Numero Inscricao": "CAN-001", INSCRICAO_KEY: "CAN-001", "Unidade Lead": "Lorena"},
            {"Numero Inscricao": "CAN-002", INSCRICAO_KEY: "CAN-002", "Unidade Lead": "Lorena"},
            {"Numero Inscricao": "CAN-003", INSCRICAO_KEY: "CAN-003", "Unidade Lead": "Altamira"},
        ]
    )


def test_le_csv_do_power_bi_em_utf8_e_normaliza_nome_da_coluna():
    conteudo = "Numero Inscricao,Unidade\n can-001 ,Lorena\nCAN-004,Lorena\n".encode(
        "utf-8-sig"
    )

    resultado = comparar_matriculas_bi(_crm(), carregar_csv_bi(conteudo))

    assert resultado.unidades == ("Lorena",)
    assert set(resultado.matriculas_crm[INSCRICAO_KEY]) == {"CAN-001", "CAN-002"}
    assert resultado.em_ambas == 1
    assert resultado.somente_crm["Numero Inscricao"].tolist() == ["CAN-002"]
    assert resultado.somente_bi["Número de Inscrição"].tolist() == ["CAN-004"]


def test_arquivo_geral_com_varias_unidades_compara_todo_o_escopo_informado():
    arquivo = pd.DataFrame(
        {
            "Número de Inscrição": ["CAN-001", "CAN-003"],
            "Unidade": ["Lorena", "Altamira"],
        }
    )

    resultado = comparar_matriculas_bi(_crm(), arquivo)

    assert resultado.unidades == ("Altamira", "Lorena")
    assert len(resultado.matriculas_crm) == 3
    assert resultado.em_ambas == 2


def test_consolida_inscricoes_duplicadas_do_bi():
    arquivo = pd.DataFrame(
        {
            "Número de Inscrição": ["CAN-001", " can-001 ", "CAN-002"],
            "Unidade": ["Lorena", "Lorena", "Lorena"],
        }
    )

    resultado = comparar_matriculas_bi(_crm(), arquivo)

    assert resultado.linhas_arquivo == 3
    assert len(resultado.matriculas_bi) == 2
    assert len(resultado.duplicidades_bi) == 2


def test_arquivo_sem_coluna_de_inscricao_e_rejeitado():
    with pytest.raises(ArquivoBIInvalido, match="Numero Inscricao"):
        carregar_csv_bi(b"Nome,Unidade\nPessoa,Lorena\n")


def test_unidade_desconhecida_e_rejeitada_para_evitar_comparacao_geral():
    arquivo = pd.DataFrame(
        {"Número de Inscrição": ["CAN-001"], "Unidade": ["Unidade nova"]}
    )

    with pytest.raises(ArquivoBIInvalido, match="não reconhecida"):
        comparar_matriculas_bi(_crm(), arquivo)


def test_inclui_matriculas_de_medicina_e_filtra_por_unidade_do_csv():
    medicina = pd.DataFrame(
        [
            {
                "Numero Inscricao": "MED-001",
                INSCRICAO_KEY: "MED-001",
                "Unidade Lead": "Medicina - Lorena",
            },
            {
                "Numero Inscricao": "MED-002",
                INSCRICAO_KEY: "MED-002",
                "Unidade Lead": "Medicina - Altamira",
            },
        ]
    )
    arquivo = pd.DataFrame(
        {
            "Número de Inscrição": ["MED-001", "MED-003"],
            "Unidade": ["Medicina - Lorena", "MEDICINA LORENA"],
        }
    )

    resultado = comparar_matriculas_bi(_crm(), arquivo, medicina)

    assert resultado.unidades == ("Medicina - Lorena",)
    assert resultado.matriculas_crm[INSCRICAO_KEY].tolist() == ["MED-001"]
    assert resultado.em_ambas == 1
    assert resultado.somente_crm.empty
    assert resultado.somente_bi["Número de Inscrição"].tolist() == ["MED-003"]
