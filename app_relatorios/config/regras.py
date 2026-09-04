"""Campos e regras de negócio compartilhados pelos relatórios."""

LEAD_ATTRIBUTES = [
    "cad_inscricaoatual",
    "cad_cpf",
    "fullname",
    "leadid",
    "createdon",
    "cad_proprietariopro",
    "trivento_unidadetrivento",
    "crmeduc_unidadeform",
]

LEAD_RENAME = {
    "cad_inscricaoatual": "Inscrição Atual",
    "cad_cpf": "CPF Lead",
    "fullname": "Nome Lead",
    "leadid": "ID Lead",
    "createdon": "Data Criação Lead",
    "cad_proprietariopro": "Proprietário",
    "trivento_unidadetrivento": "Unidade 1",
    "crmeduc_unidadeform": "Unidade 2",
}

INSCRICAO_ATTRIBUTES = [
    "cad_situacao",
    "cad_numeroinscricao",
    "cad_clientepotencialid",
    "crmeduc_data_aprovacao",
    "cad_datapagamento",
    "cad_situacaoavaliacao",
    "cad_ofertaid",
    "trivento_unidadedeensinotrivento",
    "cad_concursoid",
    "coc_situacaopagamento",
    "createdon",
    "cad_inscricaocandidatoid",
]

INSCRICAO_RENAME = {
    "cad_situacao": "Situação Inscrição",
    "cad_numeroinscricao": "Numero Inscricao",
    "cad_clientepotencialid": "ID Lead Inscrição",
    "cad_clientepotencialid_name": "Nome CRM",
    "crmeduc_data_aprovacao": "Data Aprovação",
    "cad_datapagamento": "Data de Pagamento",
    "cad_situacaoavaliacao": "Situação de Avaliação",
    "cad_ofertaid": "Curso ID",
    "trivento_unidadedeensinotrivento": "Unidade Inscrito",
    "cad_concursoid": "Forma de Ingresso",
    "coc_situacaopagamento": "Situação Pagamento",
    "createdon": "Data Criação Inscrição",
    "cad_inscricaocandidatoid": "ID Inscrição",
}

PLANILHA_ABAS = {
    "ITABIRITO": "Itabirito",
    "ALTAMIRA": "Altamira",
    "LORENA": "Lorena",
    "Canaã": "Canaã",
}

PLANILHA_MEDICINA_ABAS = {
    "MEDICINA LORENA": "Medicina - Lorena",
    "MEDICINA ALTAMIRA": "Medicina - Altamira",
}

CONSULTORES_IGNORADOS = {"Lorena", "Breno"}

PROPRIETARIO_PARA_CONSULTOR = {
    "Gabriel Matos": "Gabriel",
    "Maria Eduarda Freire": "Duda",
    "Maria Rafaela da Rocha Tavares": "Maria Rafaela",
    "Adauri Marques Delfino Junior": "Adauri",
    "Karen Flávia": "Flávia",
    "Daniel Faria Santos": "Daniel",
    "Geovana Souza da Silva": "Geovana",
    "Agnata Pamela Silva Souza": "Agnata",
    "Giovanna Eduarda Do Carmo Braga": "Giovanna Braga",
    "Hailton Alves Júnior": "Hailton",
    "Karolaine de Oliveira Alves Souza": "Karolaine",
    "Thiago Oliveira da Cruz": "Thiago",
    "Maria Fernanda Luiz Monteiro": "Maria Fernanda",
    "Ana Carolina Guimarães": "Ana Carolina",
    "Lorena Viana Gonçalves Pereira": "Lorena",
    "Thalia Gabriela de Araújo Silva": "Thalia",
    "Thalia Costa": "Thalia Costa",
    "Camila Guimarães Santos": "Camila",
    "Breno Assis Ferreira": "Breno",
    "Alana Mileyde de Souza Pinto":"Alana",
    "Debora Soares": "Débora",
}

