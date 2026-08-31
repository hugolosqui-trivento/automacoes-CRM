"""Identidade visual compartilhada pelo dashboard Streamlit."""

from __future__ import annotations

import streamlit as st


def aplicar_estilos() -> None:
    st.markdown(
        """
        <style>
        :root {
            --brand: #356ba8;
            --brand-dark: #214f86;
            --ink: #17263a;
            --muted: #62748a;
            --line: #dfe7f0;
            --canvas: #f5f8fc;
        }

        .stApp { background: var(--canvas); }
        [data-testid="stAppViewContainer"] > .main {
            background: radial-gradient(circle at 100% 0%, rgba(53,107,168,.08), transparent 28rem), var(--canvas);
        }
        .block-container {
            max-width: 1480px;
            padding-top: 1.25rem;
            padding-bottom: 3rem;
        }

        [data-testid="stSidebar"] {
            background: linear-gradient(180deg, #183e6b 0%, #24598f 58%, #2f6aa5 100%);
            border-right: 0;
        }
        [data-testid="stSidebar"] * { color: #f7fbff; }
        [data-testid="stSidebar"] [data-testid="stMarkdownContainer"] p { color: rgba(247,251,255,.76); }
        [data-testid="stSidebarNav"] a {
            border-radius: .65rem;
            margin: .12rem .45rem;
            transition: background .15s ease, transform .15s ease;
        }
        [data-testid="stSidebarNav"] a:hover {
            background: rgba(255,255,255,.12);
            transform: translateX(2px);
        }
        [data-testid="stSidebar"] button {
            border-color: rgba(255,255,255,.28);
            background: rgba(255,255,255,.09);
        }
        [data-testid="stSidebar"] button:hover {
            border-color: rgba(255,255,255,.62);
            background: rgba(255,255,255,.16);
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
        .brand-name { font-size: 1.35rem; font-weight: 760; letter-spacing: -.02em; line-height: 1; }
        .brand-name span { color: #9fd0ff; }
        .brand-tagline {
            margin-top: .34rem;
            color: rgba(255,255,255,.72);
            font-size: .58rem;
            font-weight: 700;
            letter-spacing: .22em;
            text-transform: uppercase;
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
        [data-testid="stMetricValue"] { color: var(--brand-dark); font-weight: 760; letter-spacing: -.04em; }
        [data-testid="stExpander"], [data-testid="stFileUploaderDropzone"] {
            background: white;
            border-color: var(--line);
            border-radius: .8rem;
        }
        [data-testid="stAlert"] { border-radius: .75rem; }
        div[data-baseweb="select"] > div, [data-baseweb="input"] > div {
            background: white;
            border-color: #cfd9e5;
            border-radius: .55rem;
        }

        .stTabs [data-baseweb="tab-list"] {
            gap: .35rem;
            padding: .3rem;
            background: #e9eff6;
            border-radius: .75rem;
        }
        .stTabs [data-baseweb="tab"] {
            height: 2.65rem;
            padding: 0 1rem;
            border-radius: .55rem;
            color: #52667d;
            font-weight: 650;
        }
        .stTabs [aria-selected="true"] {
            color: var(--brand-dark);
            background: white;
            box-shadow: 0 2px 7px rgba(38,68,103,.1);
        }
        [data-testid="stDataFrame"] {
            overflow: hidden;
            background: white;
            border: 1px solid var(--line);
            border-radius: .8rem;
            box-shadow: 0 5px 16px rgba(38,68,103,.06);
        }
        h2, h3 { color: var(--ink); letter-spacing: -.025em; }
        hr { border-color: var(--line); }

        @media (max-width: 800px) {
            .block-container { padding-top: .75rem; }
            .app-header { grid-template-columns: 1fr; gap: .8rem; padding: 1.15rem; }
            .header-copy { text-align: left; }
            .header-copy p { margin-left: 0; }
            .updated-at { justify-self: start; }
        }
        </style>
        """,
        unsafe_allow_html=True,
    )
