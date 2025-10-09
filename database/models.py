"""
SYD Cyber - Database Models (SQLAlchemy ORM)

Definisce le 6 tabelle del database PostgreSQL:
1. User - Consultanti (100 utenti)
2. Company - Aziende analizzate (500 aziende)
3. Assessment - Valutazioni rischio (50,000 assessment)
4. RiskEvent - 191 eventi di rischio
5. ATECOCode - 25,000 codici ATECO
6. SeismicZone - 8,102 comuni italiani

Author: Claudio + Claude AI
Date: 2025-10-09
"""

from datetime import datetime
from typing import List, Optional
from sqlalchemy import (
    Column, String, Integer, Boolean, DateTime, Text, DECIMAL,
    ForeignKey, CheckConstraint, Index, Enum as SQLEnum, JSON
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship, DeclarativeBase, Mapped, mapped_column
import uuid
import enum


# Base class per tutti i modelli
class Base(DeclarativeBase):
    pass


# ==================== ENUMS ====================

class UserRole(enum.Enum):
    """Ruoli utente"""
    CONSULTANT = "consultant"
    ADMIN = "admin"


class RiskLevel(enum.Enum):
    """Livelli di rischio"""
    LOW = "Low"
    MEDIUM = "Medium"
    HIGH = "High"
    CRITICAL = "Critical"


class ColorCode(enum.Enum):
    """Codici colore per perdite"""
    GREEN = "G"
    YELLOW = "Y"
    ORANGE = "O"
    RED = "R"


class ControlLevel(enum.Enum):
    """Livelli di controllo"""
    VERY_STRONG = "++"
    STRONG = "+"
    WEAK = "-"
    VERY_WEAK = "--"


# ==================== MODELS ====================

class User(Base):
    """
    Tabella: users
    Scopo: Gestire i consultanti (target: 100 utenti)
    """
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    subdomain: Mapped[Optional[str]] = mapped_column(String(50), unique=True, index=True)
    role: Mapped[UserRole] = mapped_column(SQLEnum(UserRole), default=UserRole.CONSULTANT)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    last_login: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    # Relationships
    companies: Mapped[List["Company"]] = relationship("Company", back_populates="creator")
    assessments: Mapped[List["Assessment"]] = relationship("Assessment", back_populates="user")

    def __repr__(self):
        return f"<User(id={self.id}, name={self.name}, email={self.email})>"


class Company(Base):
    """
    Tabella: companies
    Scopo: Anagrafica aziende clienti (riuso dati)
    """
    __tablename__ = "companies"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    partita_iva: Mapped[str] = mapped_column(String(11), unique=True, nullable=False, index=True)
    codice_ateco: Mapped[str] = mapped_column(String(10), nullable=False, index=True)
    ragione_sociale: Mapped[str] = mapped_column(String(255), nullable=False)
    oggetto_sociale: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    comune: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    provincia: Mapped[Optional[str]] = mapped_column(String(2), nullable=True)
    zona_sismica: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    # Foreign Keys
    created_by_user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True
    )

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow
    )

    # Relationships
    creator: Mapped[Optional["User"]] = relationship("User", back_populates="companies")
    assessments: Mapped[List["Assessment"]] = relationship("Assessment", back_populates="company")

    # Constraints
    __table_args__ = (
        CheckConstraint("char_length(partita_iva) = 11", name="check_piva_length"),
        CheckConstraint("zona_sismica >= 1 AND zona_sismica <= 4", name="check_zona_range"),
    )

    def __repr__(self):
        return f"<Company(id={self.id}, piva={self.partita_iva}, name={self.ragione_sociale})>"


class RiskEvent(Base):
    """
    Tabella: risk_events
    Scopo: Catalogo 191 eventi di rischio (da MAPPATURE_EXCEL_PERFETTE.json)
    """
    __tablename__ = "risk_events"

    code: Mapped[str] = mapped_column(String(10), primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    category: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    severity: Mapped[str] = mapped_column(String(20), default="medium")
    suggested_controls: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)

    # Relationships
    assessments: Mapped[List["Assessment"]] = relationship("Assessment", back_populates="risk_event")

    def __repr__(self):
        return f"<RiskEvent(code={self.code}, name={self.name}, category={self.category})>"


class Assessment(Base):
    """
    Tabella: assessments
    Scopo: Salvare ogni valutazione di rischio completata
    """
    __tablename__ = "assessments"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # Foreign Keys
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    company_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("companies.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    event_code: Mapped[str] = mapped_column(
        String(10),
        ForeignKey("risk_events.code", ondelete="RESTRICT"),
        nullable=False,
        index=True
    )

    # Risk Scoring
    risk_score: Mapped[int] = mapped_column(Integer, nullable=False)
    risk_level: Mapped[str] = mapped_column(String(20), nullable=False)
    matrix_position: Mapped[str] = mapped_column(String(5), nullable=False)  # A1-D4

    # Impact Assessment
    economic_loss: Mapped[str] = mapped_column(String(1), nullable=False)  # G/Y/O/R
    non_economic_loss: Mapped[str] = mapped_column(String(1), nullable=False)  # G/Y/O/R
    control_level: Mapped[str] = mapped_column(String(2), nullable=False)  # ++/+/-/--

    # Additional Fields
    financial_impact: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    image_impact: Mapped[bool] = mapped_column(Boolean, default=False)
    regulatory_impact: Mapped[bool] = mapped_column(Boolean, default=False)
    criminal_impact: Mapped[bool] = mapped_column(Boolean, default=False)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="assessments")
    company: Mapped["Company"] = relationship("Company", back_populates="assessments")
    risk_event: Mapped["RiskEvent"] = relationship("RiskEvent", back_populates="assessments")

    # Constraints
    __table_args__ = (
        CheckConstraint("risk_score >= 0 AND risk_score <= 100", name="check_risk_score_range"),
        CheckConstraint("economic_loss IN ('G', 'Y', 'O', 'R')", name="check_economic_loss"),
        CheckConstraint("non_economic_loss IN ('G', 'Y', 'O', 'R')", name="check_non_economic_loss"),
        CheckConstraint("control_level IN ('++', '+', '-', '--')", name="check_control_level"),
        # Composite index per query "storico azienda ordinato per data"
        Index("ix_company_created_at", "company_id", "created_at"),
    )

    def __repr__(self):
        return f"<Assessment(id={self.id}, score={self.risk_score}, level={self.risk_level})>"


class ATECOCode(Base):
    """
    Tabella: ateco_codes
    Scopo: Lookup ATECO 2022 → 2025 (da tabella_ATECO.xlsx)
    """
    __tablename__ = "ateco_codes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    code_2022: Mapped[Optional[str]] = mapped_column(String(10), nullable=True, index=True)
    code_2025: Mapped[str] = mapped_column(String(10), unique=True, nullable=False, index=True)
    code_2025_camerale: Mapped[Optional[str]] = mapped_column(String(10), nullable=True)
    title_2022: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    title_2025: Mapped[str] = mapped_column(Text, nullable=False)
    hierarchy: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    sector: Mapped[Optional[str]] = mapped_column(String(50), nullable=True, index=True)
    regulations: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    certifications: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)

    # Index GIN per ricerca JSON (PostgreSQL specific)
    __table_args__ = (
        Index("ix_ateco_regulations_gin", "regulations", postgresql_using="gin"),
    )

    def __repr__(self):
        return f"<ATECOCode(2022={self.code_2022}, 2025={self.code_2025}, title={self.title_2025[:50]})>"


class SeismicZone(Base):
    """
    Tabella: seismic_zones
    Scopo: Database completo 8,102 comuni italiani + zona sismica
    """
    __tablename__ = "seismic_zones"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    comune: Mapped[str] = mapped_column(String(100), nullable=False)
    provincia: Mapped[str] = mapped_column(String(2), nullable=False, index=True)
    regione: Mapped[str] = mapped_column(String(50), nullable=False)
    zona_sismica: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    accelerazione_ag: Mapped[float] = mapped_column(DECIMAL(4, 2), nullable=False)
    risk_level: Mapped[str] = mapped_column(String(20), nullable=False)

    # Constraints
    __table_args__ = (
        CheckConstraint("zona_sismica >= 1 AND zona_sismica <= 4", name="check_zona_sismica_range"),
        CheckConstraint("accelerazione_ag >= 0 AND accelerazione_ag <= 1", name="check_ag_range"),
        # UNIQUE constraint per disambiguare comuni omonimi
        Index("ix_comune_provincia_unique", "comune", "provincia", unique=True),
    )

    def __repr__(self):
        return f"<SeismicZone(comune={self.comune}, prov={self.provincia}, zona={self.zona_sismica})>"


# ==================== HELPER FUNCTIONS ====================

def get_sample_data():
    """
    Genera dati di test per sviluppo locale
    """
    sample_users = [
        User(
            email="dario@sydcyber.it",
            name="Dario",
            subdomain="dario",
            role=UserRole.CONSULTANT
        ),
        User(
            email="marcello@sydcyber.it",
            name="Marcello",
            subdomain="marcello",
            role=UserRole.CONSULTANT
        ),
        User(
            email="claudio@sydcyber.it",
            name="Claudio",
            subdomain="claudio",
            role=UserRole.ADMIN
        )
    ]

    return {
        "users": sample_users
    }


def create_tables(engine):
    """
    Crea tutte le tabelle nel database

    Usage:
        from sqlalchemy import create_engine
        engine = create_engine("postgresql://user:pass@host/db")
        create_tables(engine)
    """
    Base.metadata.create_all(engine)
    print("✅ Tutte le tabelle create con successo!")


def drop_tables(engine):
    """
    ATTENZIONE: Cancella TUTTE le tabelle (solo per sviluppo!)
    """
    Base.metadata.drop_all(engine)
    print("⚠️ Tutte le tabelle cancellate!")
