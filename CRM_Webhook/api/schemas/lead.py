from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class CrmEntityReference(BaseModel):
    model_config = ConfigDict(extra="allow")

    id: str | None = Field(default=None, alias="Id")
    name: str | None = Field(default=None, alias="Name")


class CrmOptionSet(BaseModel):
    model_config = ConfigDict(extra="allow")

    value: int | str | None = Field(default=None, alias="Value")


class LeadWebhook(BaseModel):
    model_config = ConfigDict(extra="allow", populate_by_name=True)

    lead_id: str | None = None
    leadid: str | None = None
    id: str | None = None
    nome: str | None = None
    fullname: str | None = None
    firstname: str | None = None
    lastname: str | None = None
    email: str | None = None
    emailaddress1: str | None = None
    telefone: str | None = None
    mobilephone: str | None = None
    unidade: str | None = None
    origem: str | None = None
    curso: str | None = None
    forma_ingresso: str | None = None
    status: str | None = None
    created_at: datetime | None = None
    createdon: datetime | None = None
    event_id: str | None = None
    event_type: str = "lead.updated"
    source: str = "crm_educacional"
    cad_cpf: str | None = Field(default=None, repr=False)
    cad_concursoatual: CrmEntityReference | None = None
    cad_situacaofunil: CrmOptionSet | None = None


class NormalizedEvent(BaseModel):
    event_id: str
    event_type: str
    source: str
    lead_id: str
    nome: str | None
    email: str | None
    telefone: str | None
    unidade: str | None
    origem: str | None
    curso: str | None
    forma_ingresso: str | None
    lead_status: str | None
    created_at: datetime | None
    payload: dict[str, Any]
