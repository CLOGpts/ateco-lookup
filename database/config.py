"""
SYD Cyber - Database Configuration

Gestisce connessione PostgreSQL con connection pooling
per supportare 100+ utenti concorrenti.

Author: Claudio + Claude AI
Date: 2025-10-09
"""

import os
from sqlalchemy import create_engine, event, pool
from sqlalchemy.orm import sessionmaker, Session
from contextlib import contextmanager
from typing import Generator
import logging

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# ==================== CONFIGURATION ====================

class DatabaseConfig:
    """
    Configurazione database PostgreSQL

    Environment Variables Required:
    - DATABASE_URL: postgresql://user:password@host:port/database
    """

    def __init__(self):
        # Railway fornisce automaticamente DATABASE_URL
        self.database_url = os.getenv(
            "DATABASE_URL",
            "postgresql://postgres:password@localhost:5432/sydcyber"  # Fallback locale
        )

        # Connection Pool Settings (per 100 utenti)
        self.pool_size = int(os.getenv("DB_POOL_SIZE", "20"))  # Connessioni permanenti
        self.max_overflow = int(os.getenv("DB_MAX_OVERFLOW", "10"))  # Connessioni extra temporanee
        self.pool_timeout = int(os.getenv("DB_POOL_TIMEOUT", "30"))  # Timeout secondi
        self.pool_recycle = int(os.getenv("DB_POOL_RECYCLE", "3600"))  # Ricicla connessioni ogni ora

        # Query Performance
        self.echo = os.getenv("DB_ECHO", "false").lower() == "true"  # Log query SQL
        self.echo_pool = os.getenv("DB_ECHO_POOL", "false").lower() == "true"  # Log pool

    def get_engine_url(self) -> str:
        """
        Ottiene URL database (Railway auto-gestisce)

        IMPORTANTE: Railway addon PostgreSQL fornisce DATABASE_URL automaticamente
        """
        return self.database_url

    def __repr__(self):
        # Non mostrare password nei log
        safe_url = self.database_url.split("@")[-1] if "@" in self.database_url else "local"
        return f"<DatabaseConfig(host={safe_url}, pool={self.pool_size}/{self.max_overflow})>"


# ==================== ENGINE CREATION ====================

# Singleton: una sola istanza engine per l'app
_engine = None
_SessionLocal = None

def get_engine():
    """
    Ottiene engine SQLAlchemy con connection pooling

    Connection Pool Explained:
    - pool_size=20: Mantiene 20 connessioni sempre aperte
    - max_overflow=10: Può creare fino a 10 connessioni extra se necessario
    - Totale max: 30 connessioni simultanee (supporta 100+ utenti con request rapide)
    """
    global _engine

    if _engine is None:
        config = DatabaseConfig()

        logger.info(f"Creazione engine database: {config}")

        _engine = create_engine(
            config.get_engine_url(),

            # Connection Pooling
            poolclass=pool.QueuePool,
            pool_size=config.pool_size,
            max_overflow=config.max_overflow,
            pool_timeout=config.pool_timeout,
            pool_recycle=config.pool_recycle,
            pool_pre_ping=True,  # Verifica connessione prima di usarla

            # Performance
            echo=config.echo,
            echo_pool=config.echo_pool,

            # PostgreSQL specific
            connect_args={
                "connect_timeout": 10,
                "options": "-c timezone=utc"
            }
        )

        # Event listeners per monitoring
        @event.listens_for(_engine, "connect")
        def receive_connect(dbapi_conn, connection_record):
            logger.debug("Nuova connessione database aperta")

        @event.listens_for(_engine, "checkout")
        def receive_checkout(dbapi_conn, connection_record, connection_proxy):
            logger.debug("Connessione prelevata dal pool")

        logger.info("✅ Engine database creato con successo!")

    return _engine


def get_session_factory():
    """
    Ottiene session factory per creare sessioni database
    """
    global _SessionLocal

    if _SessionLocal is None:
        engine = get_engine()
        _SessionLocal = sessionmaker(
            autocommit=False,
            autoflush=False,
            bind=engine
        )
        logger.info("✅ Session factory creato!")

    return _SessionLocal


# ==================== SESSION MANAGEMENT ====================

@contextmanager
def get_db_session() -> Generator[Session, None, None]:
    """
    Context manager per sessioni database

    Usage:
        with get_db_session() as session:
            user = session.query(User).filter_by(email="test@test.com").first()
            print(user.name)

    Auto-gestisce commit/rollback e chiude sessione
    """
    SessionLocal = get_session_factory()
    session = SessionLocal()

    try:
        yield session
        session.commit()  # Commit automatico se tutto ok
        logger.debug("Transazione committata con successo")
    except Exception as e:
        session.rollback()  # Rollback automatico in caso di errore
        logger.error(f"Errore database, rollback eseguito: {e}")
        raise
    finally:
        session.close()  # Chiude sempre la sessione
        logger.debug("Sessione database chiusa")


def get_db() -> Generator[Session, None, None]:
    """
    Dependency injection per FastAPI

    Usage in FastAPI endpoint:
        @app.get("/users")
        def get_users(db: Session = Depends(get_db)):
            return db.query(User).all()
    """
    SessionLocal = get_session_factory()
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# ==================== HEALTH CHECK ====================

def check_database_connection() -> bool:
    """
    Verifica connessione database (health check)

    Returns:
        bool: True se connessione ok, False altrimenti
    """
    try:
        engine = get_engine()
        with engine.connect() as conn:
            result = conn.execute("SELECT 1")
            logger.info("✅ Database connection: OK")
            return True
    except Exception as e:
        logger.error(f"❌ Database connection: FAILED - {e}")
        return False


def get_pool_status() -> dict:
    """
    Ottiene statistiche connection pool

    Returns:
        dict: Status pool (size, checked_out, overflow, etc.)
    """
    engine = get_engine()
    pool = engine.pool

    return {
        "pool_size": pool.size(),
        "checked_out": pool.checkedout(),
        "overflow": pool.overflow(),
        "checked_in": pool.checkedin(),
        "status": "healthy" if pool.checkedin() > 0 else "warning"
    }


# ==================== INITIALIZATION ====================

def init_database():
    """
    Inizializza database (crea tabelle se non esistono)

    ATTENZIONE: Usa Alembic migrations in produzione!
    Questa funzione è solo per sviluppo iniziale.
    """
    from database.models import Base

    engine = get_engine()

    logger.info("Creazione tabelle database...")
    Base.metadata.create_all(bind=engine)
    logger.info("✅ Tabelle create con successo!")

    return True


def drop_all_tables():
    """
    ⚠️ PERICOLO: Cancella TUTTE le tabelle

    Usa solo in sviluppo per reset completo!
    """
    from database.models import Base

    engine = get_engine()

    logger.warning("⚠️ CANCELLAZIONE TUTTE LE TABELLE...")
    Base.metadata.drop_all(bind=engine)
    logger.warning("❌ Tutte le tabelle cancellate!")


# ==================== EXPORT ====================

__all__ = [
    "DatabaseConfig",
    "get_engine",
    "get_session_factory",
    "get_db_session",
    "get_db",
    "check_database_connection",
    "get_pool_status",
    "init_database",
    "drop_all_tables"
]
