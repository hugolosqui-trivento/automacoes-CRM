"""
CRM Educacional -> Power BI
Script refatorado (template)

Preencha a lista `atributos` e o dicionário `rename_columns`
com os valores do seu projeto.
"""

import time
import requests
import xmltodict
import pandas as pd

BASE_URL = "https://trivento.api.crmeducacional.com"
URL = f"{BASE_URL}/api/LocalizacaoAvancada"

USERNAME = "IntegraçãoCRM"
PASSWORD = "IntegraçãoCRM"
AUTH_TYPE = "APICRMEducacional"


def get_token(session):
    payload = {
        "grant_type": "password",
        "username": USERNAME,
        "password": PASSWORD,
        "authentication_type": AUTH_TYPE,
    }

  


def create_headers(token):
    return {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/xml",
    }

