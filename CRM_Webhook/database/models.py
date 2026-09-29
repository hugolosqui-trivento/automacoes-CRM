from datetime import UTC, datetime
from typing import Any

from sqlalchemy import (
    JSON,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


def utc_now() -> datetime:
    return datetime.now(UTC)


class Base(DeclarativeBase):
    pass


class WebhookEvent(Base):
    __tablename__ = "webhook_events"

    id: Mapped[int] = mapped_column(primary_key=True)
    event_id: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    event_type: Mapped[str] = mapped_column(String(100))
    source: Mapped[str] = mapped_column(String(100))
    lead_id: Mapped[str] = mapped_column(String(255), index=True)
    payload: Mapped[dict[str, Any]] = mapped_column(JSON)
    received_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    processed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    status: Mapped[str] = mapped_column(String(30), default="received")
    error_message: Mapped[str | None] = mapped_column(Text)


class Lead(Base):
    __tablename__ = "leads"
    __table_args__ = (Index("idx_leads_received_at", "received_at"),)

    lead_id: Mapped[str] = mapped_column(String(255), primary_key=True)
    nome: Mapped[str | None] = mapped_column(String(255))
    email: Mapped[str | None] = mapped_column(String(320))
    telefone: Mapped[str | None] = mapped_column(String(100))
    unidade: Mapped[str | None] = mapped_column(String(255), index=True)
    origem: Mapped[str | None] = mapped_column(String(255), index=True)
    curso: Mapped[str | None] = mapped_column(String(255))
    forma_ingresso: Mapped[str | None] = mapped_column(String(255))
    status: Mapped[str | None] = mapped_column(String(100))
    created_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    received_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    payload: Mapped[dict[str, Any]] = mapped_column(JSON)


class Inscricao(Base):
    __tablename__ = "inscricoes"
    __table_args__ = (
        CheckConstraint(
            "cad_situacao BETWEEN 1 AND 6",
            name="ck_inscricoes_cad_situacao_1_6",
        ),
        Index("idx_inscricoes_lead_id", "lead_id"),
        Index("idx_inscricoes_received_at", "received_at"),
    )

    numero_inscricao: Mapped[str] = mapped_column(String(255), primary_key=True)
    lead_id: Mapped[str] = mapped_column(
        ForeignKey("leads.lead_id"), nullable=False
    )
    cad_situacao: Mapped[int] = mapped_column(Integer, nullable=False)
    curso: Mapped[str | None] = mapped_column(String(255))
    forma_ingresso: Mapped[str | None] = mapped_column(String(255))
    unidade: Mapped[str | None] = mapped_column(String(255), index=True)
    created_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    modified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    received_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    payload: Mapped[dict[str, Any]] = mapped_column(JSON)
