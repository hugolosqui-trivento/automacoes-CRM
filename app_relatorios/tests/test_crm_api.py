from services.crm_api import CrmClient


def test_fetch_xml_aplica_filtro_de_intake_somente_em_leads():
    xml = CrmClient._fetch_xml("lead", ["leadid"])

    assert 'entity name="lead"' in xml
    assert 'attribute="crmeduc_intake"' in xml
    assert 'value="2027/1%"' in xml


def test_fetch_xml_filtra_inscricoes_pelo_intake_do_lead_relacionado():
    xml = CrmClient._fetch_xml(
        "cad_inscricaocandidato",
        ["cad_inscricaocandidatoid"],
    )

    assert 'entity name="cad_inscricaocandidato"' in xml
    assert (
        '<link-entity name="lead" from="leadid" '
        'to="cad_clientepotencialid" link-type="inner" '
        'alias="cad_lead_cad_inscricaocandidato">'
    ) in xml
    assert 'attribute="crmeduc_intake" operator="not-like"' in xml
    assert 'value="2027/1%"' in xml


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
