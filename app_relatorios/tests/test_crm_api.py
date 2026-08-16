from services.crm_api import CrmClient


def test_lookup_preserva_texto_como_id_e_name_em_coluna_separada():
    registro = {
        "cad_clientepotencialid": {
            "@name": "Pessoa Exemplo",
            "#text": "{ABC-123}",
        },
        "cad_situacao": {"@name": "Matriculado", "#text": "1"},
    }

    resultado = CrmClient._flatten_record(
        registro,
        {"cad_clientepotencialid"},
    )

    assert resultado["cad_clientepotencialid"] == "{ABC-123}"
    assert resultado["cad_clientepotencialid_name"] == "Pessoa Exemplo"
    assert resultado["cad_situacao"] == "Matriculado"
