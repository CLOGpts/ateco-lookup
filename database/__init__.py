"""
SYD Cyber - Database Package

Gestisce connessione e modelli PostgreSQL per persistenza dati.

Components:
- models.py: SQLAlchemy ORM models (6 tabelle)
- config.py: Database configuration e connection pooling
- test_connection.py: Script di test

Usage:
    from database import get_db_session, User, Company

    with get_db_session() as session:
        user = session.query(User).filter_by(email="test@test.com").first()
        print(user.name)
"""

__version__ = "1.0.0"
__author__ = "Claudio + Claude AI"

# Import modelli principali
from database.models import (
    Base,
    User,
    Company,
    Assessment,
    RiskEvent,
    ATECOCode,
    SeismicZone,
    UserRole,
    RiskLevel,
    ColorCode,
    ControlLevel
)

# Import funzioni database
from database.config import (
    get_engine,
    get_db_session,
    get_db,
    check_database_connection,
    get_pool_status,
    init_database
)

__all__ = [
    # Models
    "Base",
    "User",
    "Company",
    "Assessment",
    "RiskEvent",
    "ATECOCode",
    "SeismicZone",
    # Enums
    "UserRole",
    "RiskLevel",
    "ColorCode",
    "ControlLevel",
    # Functions
    "get_engine",
    "get_db_session",
    "get_db",
    "check_database_connection",
    "get_pool_status",
    "init_database"
]
