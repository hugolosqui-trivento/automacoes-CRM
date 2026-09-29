from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict

from api.schemas.lead import CrmEntityReference, CrmOptionSet


class InscricaoWebhook(BaseModel):
    model_config = ConfigDict(extra="allow", populate_by_name=True)

    cad_clientepotencialid: CrmEntityReference | None = None
    cad_numeroinscricao: str | None = None
    cad_situacao: CrmOptionSet | None = None
    cad_ofertaid: CrmEntityReference | None = None
    crmeduc_linha_de_negocios: CrmEntityReference | None = None
    trivento_unidadedeensinotrivento: CrmEntityReference | None = None
    createdon: datetime | None = None
    modifiedon: datetime | None = None
    event_id: str | None = None
    event_type: str = "inscricao.updated"
    source: str = "crm_educacional"


class NormalizedInscricaoEvent(BaseModel):
    event_id: str
    event_type: str
    source: str
    lead_id: str
    numero_inscricao: str
    cad_situacao: int
    curso: str | None
    forma_ingresso: str | None
    unidade: str | None
    created_at: datetime | None
    modified_at: datetime | None
    payload: dict[str, Any]
