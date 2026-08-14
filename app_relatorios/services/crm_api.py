"""Cliente do endpoint LocalizacaoAvancada do CRM Educacional."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

import pandas as pd
import requests
import xmltodict


@dataclass(frozen=True)
class CrmSettings:
    base_url: str
    username: str
    password: str
    auth_type: str = "APICRMEducacional"


class CrmApiError(RuntimeError):
    """Erro legível gerado durante uma consulta ao CRM."""


class CrmClient:
    def __init__(self, settings: CrmSettings, timeout: int = 60) -> None:
        self.settings = settings
        self.timeout = timeout

    def _token(self, session: requests.Session) -> str:
        response = session.post(
            f"{self.settings.base_url.rstrip('/')}/api/token",
            data={
                "grant_type": "password",
                "username": self.settings.username,
                "password": self.settings.password,
                "authentication_type": self.settings.auth_type,
            },
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            timeout=30,
        )
        response.raise_for_status()
        return response.json()["access_token"]

    @staticmethod
    def _fetch_xml(entity: str, attributes: Iterable[str]) -> str:
        tags = "\n".join(f'<attribute name="{name}"/>' for name in attributes)
        return (
            '<fetch version="1.0" output-format="xml-platform" mapping="logical">'
            f'<entity name="{entity}">{tags}'
            '<order attribute="createdon" descending="true"/>'
            "</entity></fetch>"
        )

    @staticmethod
    def _flatten(value):
        if not isinstance(value, dict):
            return value
        return value.get("@name", value.get("#text", value))

    def fetch_entity(
        self,
        entity: str,
        attributes: Iterable[str],
        rename: dict[str, str],
    ) -> pd.DataFrame:
        rows: list[dict] = []
        body = self._fetch_xml(entity, attributes)
        endpoint = f"{self.settings.base_url.rstrip('/')}/api/LocalizacaoAvancada"

        try:
            with requests.Session() as session:
                token = self._token(session)
                page = 1
                while True:
                    response = session.post(
                        endpoint,
                        headers={
                            "Authorization": f"Bearer {token}",
                            "Content-Type": "application/xml",
                            "Pagina": str(page),
                        },
                        data=body.encode("utf-8"),
                        timeout=self.timeout,
                    )
                    response.raise_for_status()
                    resultset = xmltodict.parse(response.text).get("resultset", {})
                    records = resultset.get("result", [])
                    if isinstance(records, dict):
                        records = [records]
                    rows.extend(
                        {key: self._flatten(value) for key, value in record.items()}
                        for record in records
                    )
                    if resultset.get("@morerecords") != "1":
                        break
                    page += 1
        except (requests.RequestException, KeyError, ValueError) as exc:
            raise CrmApiError(f"Não foi possível consultar {entity} no CRM: {exc}") from exc

        return pd.DataFrame(rows).rename(columns=rename)

