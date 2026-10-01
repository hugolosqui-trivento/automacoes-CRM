import sys
from base64 import b64encode
from datetime import datetime
from html import escape
from pathlib import Path
from urllib.parse import quote

import pandas as pd
import streamlit as st

# Streamlit adds the entrypoint directory (``dashboard``) to ``sys.path``.
# Add the project root so sibling packages such as ``database`` and ``shared``
# are importable regardless of the directory from which Streamlit is started.
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from dashboard.config import load_database_url_from_streamlit_secrets

load_database_url_from_streamlit_secrets(st.secrets)

from database.connection import create_tables
from database.repositories.dashboard import (
    load_daily_matriculas,
    load_daily_funnel,
    load_leads_at_funnel_stage,
    load_metrics,
    load_recent_inscricoes,
    load_recent_leads,
)
from database.retention import purge_records_outside_current_day


CRM_LEAD_EDIT_URL = "https://wakeme.crmeducacional.com/app/leads/edit"
MATRICULAS_ASSET_DIR = Path(__file__).parent / "aba Matriculas"
MATRICULA_UNIT_LOGOS = {
    "Altamira": MATRICULAS_ASSET_DIR / "Altamira.png",
    "Canaã": MATRICULAS_ASSET_DIR / "canaa.png",
    "Itabirito": MATRICULAS_ASSET_DIR / "itabirito.png",
    "Lagoa Santa": MATRICULAS_ASSET_DIR / "Logo-SD-lagoa-santa.svg",
    "Lorena": MATRICULAS_ASSET_DIR / "lorena.png",
}


def dataframe_with_lead_links(rows: list[dict]) -> pd.DataFrame:
    """Transform Lead IDs into clickable CRM edit-page URLs."""
    dataframe = pd.DataFrame(rows)
    if "Lead ID" in dataframe.columns:
        dataframe["Lead ID"] = dataframe["Lead ID"].map(
            lambda lead_id: f"{CRM_LEAD_EDIT_URL}/{quote(str(lead_id), safe='')}"
        )
    return dataframe


def lead_link_column():
    return st.column_config.LinkColumn(
        "Lead ID",
        help="Abrir o lead no CRM Educacional",
        display_text=r".*/([^/?#]+)$",
    )


@st.cache_resource
def prepare_database() -> dict[str, int]:
    create_tables()
    return purge_records_outside_current_day()


def apply_styles() -> None:
    """Apply the same visual identity used by the report pages."""
    st.markdown(
        """
        <style>
        :root {
            --brand: #356ba8;
            --brand-dark: #214f86;
            --muted: #62748a;
            --line: #dfe7f0;
            --canvas: #f5f8fc;
        }

        .stApp { background: var(--canvas); }
        [data-testid="stAppViewContainer"] > .main {
            background: radial-gradient(
                circle at 100% 0%,
                rgba(53,107,168,.08),
                transparent 28rem
            ), var(--canvas);
        }
        .block-container {
            max-width: 1600px;
            padding-top: 4.25rem;
            padding-left: clamp(1rem, 2vw, 2rem);
            padding-right: clamp(1rem, 2vw, 2rem);
            padding-bottom: 3rem;
        }

        [data-testid="stSidebar"] {
            background: linear-gradient(180deg, #183e6b 0%, #24598f 58%, #2f6aa5 100%);
            border-right: 0;
        }
        [data-testid="stSidebar"] * { color: #f7fbff; }
        [data-testid="stSidebar"] [data-testid="stMarkdownContainer"] p {
            color: rgba(247,251,255,.76);
        }

        .app-header {
            min-height: 116px;
            display: grid;
            grid-template-columns: minmax(150px,.7fr) minmax(240px,2fr) minmax(180px,.8fr);
            align-items: center;
            gap: 1.25rem;
            padding: 1.25rem 1.5rem;
            margin: 0 0 1rem;
            color: white;
            background: linear-gradient(118deg, #255a92 0%, #356ba8 58%, #3e78b9 100%);
            border: 1px solid rgba(255,255,255,.16);
            border-radius: 1rem;
            box-shadow: 0 14px 34px rgba(24,62,107,.18);
            overflow: hidden;
            position: relative;
        }
        .app-header::after {
            content: "";
            position: absolute;
            width: 250px;
            height: 250px;
            right: -95px;
            top: -145px;
            border: 42px solid rgba(255,255,255,.06);
            border-radius: 50%;
        }
        .brand-lockup, .header-copy, .updated-at { position: relative; z-index: 1; }
        .brand-lockup {
            display: flex;
            flex-direction: column;
            align-items: flex-start;
            gap: .35rem;
        }
        .brand-logo { display: block; width: 112px; height: auto; }
        .brand-title {
            color: white;
            font-size: 1.05rem;
            font-weight: 700;
            line-height: 1.1;
            white-space: nowrap;
        }
        .header-copy { text-align: center; }
        .header-copy h1 {
            margin: 0;
            color: white;
            font-size: clamp(1.55rem,2.6vw,2.25rem);
            line-height: 1.14;
            letter-spacing: -.035em;
        }
        .header-copy p {
            max-width: 720px;
            margin: .48rem auto 0;
            color: rgba(255,255,255,.8);
            font-size: .88rem;
            line-height: 1.4;
        }
        .updated-at {
            justify-self: end;
            padding: .55rem .7rem;
            border: 1px solid rgba(255,255,255,.18);
            border-radius: .65rem;
            background: rgba(14,49,87,.22);
            font-size: .72rem;
            font-weight: 650;
            white-space: nowrap;
        }

        [data-testid="stMetric"] {
            min-height: 114px;
            padding: 1rem 1.1rem;
            background: white;
            border: 1px solid var(--line);
            border-top: 4px solid var(--brand);
            border-radius: .85rem;
            box-shadow: 0 5px 16px rgba(38,68,103,.07);
        }
        [data-testid="stMetricLabel"] { color: var(--muted); font-weight: 650; }
        [data-testid="stMetricValue"] {
            color: var(--brand-dark);
            font-weight: 760;
            letter-spacing: -.04em;
        }
        [data-testid="stAlert"] { border-radius: .75rem; }
        [data-testid="stDataFrame"] {
            overflow: hidden;
            background: white;
            border: 1px solid var(--line);
            border-radius: .8rem;
            box-shadow: 0 5px 16px rgba(38,68,103,.06);
        }
        h2, h3 { color: #17263a; letter-spacing: -.025em; }

        .matriculas-summary {
            margin: .35rem 0 1.75rem;
            text-align: center;
        }
        .matriculas-total {
            color: #111827;
            font-size: clamp(3.2rem, 7vw, 5.2rem);
            font-weight: 780;
            line-height: .95;
            letter-spacing: -.06em;
        }
        .matriculas-title {
            margin: .35rem 0 .75rem;
            color: #111827;
            font-size: clamp(1.65rem, 3.4vw, 2.8rem);
            font-weight: 500;
            letter-spacing: -.035em;
            text-align: center;
        }
        .matriculas-unit-name {
            margin-top: .15rem;
            color: #111827;
            font-size: 1.35rem;
            font-weight: 600;
            text-align: center;
        }
        .matriculas-unit-value {
            color: #111827;
            font-size: 3rem;
            font-weight: 780;
            line-height: 1;
            text-align: center;
        }

        @media (max-width: 800px) {
            .block-container { padding-top: 4rem; }
            .app-header { grid-template-columns: 1fr; gap: .8rem; padding: 1.15rem; }
            .brand-logo { width: 100px; }
            .brand-title { font-size: 1rem; }
            .header-copy { text-align: left; }
            .header-copy p { margin-left: 0; }
            .updated-at { justify-self: start; }
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def logo_data_uri() -> str:
    logo_path = Path(__file__).parent / "assets" / "logo-transparent.png"
    content = logo_path.read_bytes()
    return "data:image/png;base64," + b64encode(content).decode("ascii")


def show_sidebar() -> None:
    st.sidebar.markdown("## Trivento")
    st.sidebar.caption("INTELIGÊNCIA COMERCIAL")
    st.sidebar.markdown("---")
    st.sidebar.caption("MONITORAMENTO CRM")


def show_header(updated_at: datetime) -> None:
    logo = logo_data_uri()
    title = escape("Monitoramento de leads")
    description = escape(
        "Acompanhamento dos eventos recebidos pelo webhook do CRM Educacional."
    )
    st.markdown(
        f"""
        <section class="app-header">
            <div class="brand-lockup">
                <img src="{logo}" alt="Símbolo Trivento Educação" class="brand-logo">
                <div class="brand-title">Trivento Educação</div>
            </div>
            <div class="header-copy">
                <h1>{title}</h1>
                <p>{description}</p>
            </div>
            <div class="updated-at">Atualizado em {updated_at:%d/%m/%Y %H:%M}</div>
        </section>
        """,
        unsafe_allow_html=True,
    )


st.set_page_config(
    page_title="CRM - Monitoramento de leads",
    page_icon=":material/monitoring:",
    layout="wide",
)
apply_styles()
show_sidebar()
prepare_database()


@st.fragment(run_every="5s")
def error_metric() -> None:
    metrics = load_metrics()
    show_header(datetime.now().astimezone())
    metric_column, _, _, _ = st.columns(4)
    metric_column.metric("Eventos com erro", metrics["errors"])


@st.fragment(run_every="5s")
def daily_funnel() -> None:
    funnel = load_daily_funnel()
    st.subheader("Evolução dos leads criados hoje")
    st.caption(
        "Funil cumulativo baseado na Situação da inscrição mais recente. "
        "Classificados e desistentes permanecem contabilizados até Aprovado; "
        "desclassificados, até Inscrito. Clique em uma etapa para ver quem "
        "ainda não avançou."
    )

    chart_data = pd.DataFrame(funnel["stages"])
    max_count = max(funnel["total"], 1)
    rows = []
    for _, stage in chart_data.iterrows():
        count = int(stage["count"])
        label = escape(str(stage["label"]))
        tooltip = escape(
            f"{stage['label']}: {count} leads; "
            f"{int(stage['stalled_count'])} ainda nesta etapa; "
            f"{stage['percentage']:.1f}% da coorte",
            quote=True,
        )
        width = count / max_count * 100
        rows.append(
            f'<div class="funnel-stage">'
            f'<span class="funnel-label">{label}</span>'
            f'<div class="funnel-track" title="{tooltip}">'
            f'<div class="funnel-bar" style="width: max(48px, {width:.2f}%)">'
            f"{count}</div></div></div>"
        )

    st.html(
        """
        <style>
        .funnel-chart { display: grid; gap: 12px; padding: 10px 0 18px; }
        .funnel-stage {
            display: grid;
            grid-template-columns: 150px minmax(0, 1fr);
            align-items: center;
            gap: 16px;
        }
        .funnel-label { color: #214F86; font-size: 15px; font-weight: 700; }
        .funnel-track { min-width: 0; }
        .funnel-bar {
            box-sizing: border-box;
            max-width: 100%;
            height: 44px;
            border-radius: 6px;
            background: #295E97;
            color: #FFFFFF;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 18px;
            font-weight: 700;
        }
        </style>
        <div class="funnel-chart" role="img" aria-label="Funil de leads de hoje">
        """
        + "".join(rows)
        + "</div>"
    )
    if funnel["total"] == 0:
        st.info("Nenhum lead com data de criação de hoje foi recebido.")

    stages = [int(stage) for stage in chart_data["stage"]]
    stage_labels = {
        int(row["stage"]): (
            f"{row['label']} · {int(row['stalled_count'])} nesta etapa"
        )
        for _, row in chart_data.iterrows()
    }
    selected_stage = st.segmented_control(
        "Ver pessoas por etapa",
        options=stages,
        format_func=stage_labels.__getitem__,
        key="selected-funnel-stage",
        width="stretch",
        wrap=True,
    )
    if selected_stage is None:
        st.caption("Selecione uma etapa acima para ver quem ainda não avançou.")
        return

    selected_stage = int(selected_stage)
    selected_row = chart_data.loc[chart_data["stage"] == selected_stage].iloc[0]
    stage_label = str(selected_row["label"])
    stopped_leads = load_leads_at_funnel_stage(selected_stage, limit=100)

    st.markdown(f"#### Pessoas que estão em {stage_label}")
    if selected_stage < int(chart_data["stage"].max()):
        next_label = str(
            chart_data.loc[chart_data["stage"] == selected_stage + 1, "label"].iloc[0]
        )
        st.caption(
            f"{len(stopped_leads)} lead(s) chegaram a {stage_label}, mas ainda não "
            f"avançaram para {next_label}."
        )
    else:
        st.caption(f"{len(stopped_leads)} lead(s) estão na etapa final do funil.")

    if not stopped_leads:
        if selected_stage < int(chart_data["stage"].max()):
            st.success("Todos os leads que chegaram a esta etapa já avançaram.")
        else:
            st.info("Nenhum lead está nesta etapa.")
        return

    st.dataframe(
        dataframe_with_lead_links(stopped_leads),
        width="stretch",
        hide_index=True,
        column_config={
            "Lead ID": lead_link_column(),
            "Última movimentação": st.column_config.DatetimeColumn(
                format="DD/MM/YYYY HH:mm"
            ),
        },
    )


@st.fragment(run_every="10s")
def recent_leads() -> None:
    st.subheader("Leads recentes")
    rows = load_recent_leads(50)
    if not rows:
        st.info("Nenhum lead recebido ainda.")
        return
    st.dataframe(
        dataframe_with_lead_links(rows),
        width="stretch",
        hide_index=True,
        column_config={"Lead ID": lead_link_column()},
    )


@st.fragment(run_every="5s")
def daily_matriculas() -> None:
    summary = load_daily_matriculas()

    st.markdown(
        '<div class="matriculas-title">Total de matrículas hoje</div>',
        unsafe_allow_html=True,
    )
    with st.container(horizontal_alignment="center"):
        st.image(
            MATRICULAS_ASSET_DIR / "trivento.png",
            width=270,
        )
    st.markdown(
        f"""
        <section class="matriculas-summary">
            <div class="matriculas-total">{summary['total']}</div>
        </section>
        """,
        unsafe_allow_html=True,
    )

    columns = st.columns(5, gap="small", vertical_alignment="bottom")
    for column, (unit, logo_path) in zip(columns, MATRICULA_UNIT_LOGOS.items()):
        with column:
            with st.container(horizontal_alignment="center"):
                st.image(logo_path, width=180)
                st.markdown(
                    f'<div class="matriculas-unit-name">{escape(unit)}</div>',
                    unsafe_allow_html=True,
                )
                st.markdown(
                    f'<div class="matriculas-unit-value">{summary["units"][unit]}</div>',
                    unsafe_allow_html=True,
                )

    if summary["unmapped"]:
        st.warning(
            f'{summary["unmapped"]} matrícula(s) sem unidade reconhecida estão '
            "incluídas no total."
        )

    updated_at = datetime.now().astimezone()
    with st.container(horizontal_alignment="center"):
        st.caption(
            f"Atualização automática a cada 5 segundos · "
            f"{updated_at:%d/%m/%Y %H:%M:%S}"
        )


@st.fragment(run_every="10s")
def recent_inscricoes() -> None:
    st.subheader("Inscrições recentes")
    rows = load_recent_inscricoes(50)
    if not rows:
        st.info("Nenhuma inscrição recebida ainda.")
        return
    st.dataframe(
        dataframe_with_lead_links(rows),
        width="stretch",
        hide_index=True,
        column_config={"Lead ID": lead_link_column()},
    )


matriculas_tab, monitoring_tab = st.tabs(
    [":material/school: Matrículas", ":material/monitoring: Monitoramento de leads"]
)

with matriculas_tab:
    daily_matriculas()

with monitoring_tab:
    error_metric()
    daily_funnel()
    recent_leads()
    recent_inscricoes()
