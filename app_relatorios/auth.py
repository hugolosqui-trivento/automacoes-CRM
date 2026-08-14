"""Barreira simples de acesso para instalações internas do dashboard."""

from __future__ import annotations

import hmac

import streamlit as st


def exigir_autenticacao(senha_configurada: str) -> None:
    if not senha_configurada:
        return
    if st.session_state.get("autenticado"):
        return

    st.title("Relatórios de captação")
    st.caption("Informe a senha de acesso para continuar.")
    with st.form("login"):
        senha = st.text_input("Senha", type="password")
        entrar = st.form_submit_button("Entrar", type="primary")
    if entrar:
        if hmac.compare_digest(senha, senha_configurada):
            st.session_state["autenticado"] = True
            st.rerun()
        st.error("Senha inválida.")
    st.stop()

