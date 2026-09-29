import os
from collections.abc import Mapping

from streamlit.errors import StreamlitSecretNotFoundError


def load_database_url_from_streamlit_secrets(
    secrets: Mapping[str, object],
) -> None:
    """Expose a Streamlit secret to the shared settings layer when available."""
    if os.getenv("DATABASE_URL"):
        return

    try:
        database_url = secrets.get("DATABASE_URL")
    except StreamlitSecretNotFoundError:
        # Local development commonly uses the project-level .env instead of
        # .streamlit/secrets.toml. Pydantic loads that file afterwards.
        return

    if database_url:
        os.environ["DATABASE_URL"] = str(database_url)
