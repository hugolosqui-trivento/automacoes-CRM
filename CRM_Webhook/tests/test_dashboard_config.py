import os

from streamlit.errors import StreamlitSecretNotFoundError

from dashboard.config import load_database_url_from_streamlit_secrets


class MissingSecrets(dict):
    def get(self, key, default=None):
        raise StreamlitSecretNotFoundError("No secrets found")


def test_missing_streamlit_secrets_allows_env_file_fallback(monkeypatch):
    monkeypatch.delenv("DATABASE_URL", raising=False)

    load_database_url_from_streamlit_secrets(MissingSecrets())

    assert "DATABASE_URL" not in os.environ


def test_streamlit_secret_is_exposed_to_shared_settings(monkeypatch):
    monkeypatch.delenv("DATABASE_URL", raising=False)

    load_database_url_from_streamlit_secrets(
        {"DATABASE_URL": "postgresql+psycopg://example.invalid/db"}
    )

    assert os.environ["DATABASE_URL"] == "postgresql+psycopg://example.invalid/db"


def test_environment_variable_takes_precedence_over_streamlit_secret(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "sqlite:///existing.db")

    load_database_url_from_streamlit_secrets(
        {"DATABASE_URL": "postgresql+psycopg://example.invalid/db"}
    )

    assert os.environ["DATABASE_URL"] == "sqlite:///existing.db"
