"""Página para reconciliar as matrículas do CRM com uma exportação do Power BI."""

import streamlit as st

from data_loader import carregar_dados_medicina
from services.comparacao_bi import (
    ArquivoBIInvalido,
    carregar_csv_bi,
    comparar_matriculas_bi,
)
from services.relatorios import gerar_comparacao_medicina
from settings import carregar_settings
from ui import iniciar_pagina, mostrar_cabecalho, mostrar_metricas, mostrar_tabela


COLUNAS_CRM_VISIVEIS = [
    "Numero Inscricao",
    "Situação Inscrição",
    "Curso ID",
    "Unidade Lead",
    "Forma de Ingresso",
]
COLUNAS_BI_VISIVEIS = [
    "Número de Inscrição",
    "Situação Inscrição",
    "Curso",
    "Unidade",
    "Forma de Ingresso",
]


relatorios, atualizado_em = iniciar_pagina(
    "Checar matrículas do BI", ":material/fact_check:"
)

mostrar_cabecalho(
    "Checar matrículas do BI",
    "Envie uma exportação CSV de matriculados do Power BI para compará-la com as "
    "matrículas carregadas do CRM via API.",
    atualizado_em,
)

arquivo = st.file_uploader(
    "Arquivo CSV do Power BI",
    type="csv",
    key="arquivo_matriculas_bi",
    help="O arquivo deve conter a coluna 'Numero Inscricao' e, de preferência, 'Unidade'.",
)

if arquivo is None:
    st.info("Envie o arquivo CSV para gerar a conferência.")
    st.stop()

try:
    dados_bi = carregar_csv_bi(arquivo.getvalue())
except ArquivoBIInvalido as exc:
    st.error(str(exc))
    st.stop()

settings = carregar_settings()
if not settings.matriculas_medicina_url:
    st.error("Configuração incompleta: MATRICULAS_MEDICINA_URL")
    st.stop()

try:
    planilha_medicina = carregar_dados_medicina(
        settings.matriculas_medicina_url
    )
    matriculas_medicina = gerar_comparacao_medicina(
        relatorios.inscricoes_crm, planilha_medicina
    ).matriculas_crm
    comparacao = comparar_matriculas_bi(
        relatorios.matriculas_crm,
        dados_bi,
        matriculas_medicina,
    )
except ArquivoBIInvalido as exc:
    st.error(str(exc))
    st.stop()
except Exception as exc:
    st.error(f"Falha ao carregar a planilha de Medicina: {exc}")
    st.info("Confira o secret MATRICULAS_MEDICINA_URL e o acesso à planilha.")
    st.stop()

escopo = ", ".join(comparacao.unidades) if comparacao.unidades else "Todas as unidades"
st.caption(
    f"Arquivo: {arquivo.name} · Escopo aplicado ao CRM, incluindo Medicina: {escopo}"
)

mostrar_metricas(
    {
        "Matrículas do CRM via API": len(comparacao.matriculas_crm),
        "Matrículas únicas no CSV": len(comparacao.matriculas_bi),
        "Presentes em ambos": comparacao.em_ambas,
        "Somente no CRM": len(comparacao.somente_crm),
        "Somente no BI": len(comparacao.somente_bi),
    },
    colunas=5,
)

if comparacao.linhas_arquivo != len(comparacao.matriculas_bi):
    st.warning(
        f"O CSV possui {comparacao.linhas_arquivo} linha(s), mas "
        f"{len(comparacao.matriculas_bi)} inscrição(ões) única(s) válida(s)."
    )

aba_crm, aba_bi, aba_qualidade = st.tabs(
    ["Somente no CRM", "Somente no BI", "Qualidade do CSV"]
)
with aba_crm:
    colunas = [coluna for coluna in COLUNAS_CRM_VISIVEIS if coluna in comparacao.somente_crm]
    if comparacao.somente_crm.empty:
        st.success("Nenhuma inscrição existe somente no CRM neste escopo.")
    else:
        mostrar_tabela(comparacao.somente_crm[colunas], "bi_somente_crm")

with aba_bi:
    colunas = [coluna for coluna in COLUNAS_BI_VISIVEIS if coluna in comparacao.somente_bi]
    if comparacao.somente_bi.empty:
        st.success("Nenhuma inscrição existe somente no Power BI neste escopo.")
    else:
        mostrar_tabela(comparacao.somente_bi[colunas], "bi_somente_powerbi")

with aba_qualidade:
    if comparacao.duplicidades_bi.empty:
        st.success("O CSV não contém inscrições duplicadas.")
    else:
        st.warning(
            f"Foram encontradas {len(comparacao.duplicidades_bi)} linha(s) envolvendo "
            "inscrições duplicadas. A primeira ocorrência foi usada na comparação."
        )
        colunas = [
            coluna
            for coluna in COLUNAS_BI_VISIVEIS
            if coluna in comparacao.duplicidades_bi
        ]
        mostrar_tabela(comparacao.duplicidades_bi[colunas], "bi_duplicidades")
