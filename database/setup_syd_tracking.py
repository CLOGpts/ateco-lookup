"""
Script per creare tabelle Syd Agent Tracking
Esegue add_syd_tracking_tables.sql e verifica risultati

Uso: python database/setup_syd_tracking.py
"""

import sys
import os
from pathlib import Path

# Aggiungi parent directory al path per import
sys.path.insert(0, str(Path(__file__).parent.parent))

from database.config import get_engine, check_database_connection
from sqlalchemy import text
import logging

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)


def read_sql_file() -> str:
    """Legge il file SQL"""
    sql_file = Path(__file__).parent / "add_syd_tracking_tables.sql"

    if not sql_file.exists():
        raise FileNotFoundError(f"File SQL non trovato: {sql_file}")

    with open(sql_file, 'r', encoding='utf-8') as f:
        return f.read()


def execute_sql(engine, sql_content: str):
    """Esegue SQL script"""
    logger.info("📝 Esecuzione script SQL...")

    with engine.connect() as conn:
        # SQLAlchemy 2.0 richiede explicit transaction
        trans = conn.begin()
        try:
            # Esegui tutto lo script
            conn.execute(text(sql_content))
            trans.commit()
            logger.info("✅ Script SQL eseguito con successo!")
            return True
        except Exception as e:
            trans.rollback()
            logger.error(f"❌ Errore esecuzione SQL: {e}")
            raise


def verify_tables(engine):
    """Verifica che le tabelle siano state create"""
    logger.info("🔍 Verifica tabelle create...")

    with engine.connect() as conn:
        # Controlla user_sessions
        result = conn.execute(text("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables
                WHERE table_schema = 'public'
                AND table_name = 'user_sessions'
            );
        """))
        user_sessions_exists = result.scalar()

        # Controlla session_events
        result = conn.execute(text("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables
                WHERE table_schema = 'public'
                AND table_name = 'session_events'
            );
        """))
        session_events_exists = result.scalar()

        if user_sessions_exists and session_events_exists:
            logger.info("✅ Tabelle create: user_sessions, session_events")
            return True
        else:
            logger.error("❌ Tabelle non trovate!")
            return False


def verify_indexes(engine):
    """Verifica indici creati"""
    logger.info("🔍 Verifica indici...")

    with engine.connect() as conn:
        result = conn.execute(text("""
            SELECT indexname
            FROM pg_indexes
            WHERE tablename IN ('user_sessions', 'session_events')
            ORDER BY indexname;
        """))

        indexes = [row[0] for row in result]
        logger.info(f"✅ Indici creati: {len(indexes)}")
        for idx in indexes:
            logger.info(f"   - {idx}")

        return len(indexes) > 0


def verify_test_data(engine):
    """Verifica dati di test inseriti"""
    logger.info("🔍 Verifica dati di test...")

    with engine.connect() as conn:
        # Conta sessioni test
        result = conn.execute(text("""
            SELECT COUNT(*) FROM user_sessions WHERE user_id = 'test-user-1';
        """))
        sessions_count = result.scalar()

        # Conta eventi test
        result = conn.execute(text("""
            SELECT COUNT(*) FROM session_events WHERE user_id = 'test-user-1';
        """))
        events_count = result.scalar()

        logger.info(f"✅ Dati di test: {sessions_count} sessioni, {events_count} eventi")

        if sessions_count > 0 and events_count > 0:
            # Mostra dati
            result = conn.execute(text("""
                SELECT user_id, phase, progress, start_time
                FROM user_sessions
                WHERE user_id = 'test-user-1'
                LIMIT 1;
            """))
            session = result.fetchone()
            logger.info(f"   Sessione test: user={session[0]}, phase={session[1]}, progress={session[2]}%")

            result = conn.execute(text("""
                SELECT event_type, event_data, timestamp
                FROM session_events
                WHERE user_id = 'test-user-1'
                LIMIT 1;
            """))
            event = result.fetchone()
            logger.info(f"   Evento test: type={event[0]}, data={event[1]}")

        return sessions_count > 0 and events_count > 0


def main():
    """Funzione principale"""
    logger.info("=" * 60)
    logger.info("🚀 SETUP SYD AGENT TRACKING TABLES")
    logger.info("=" * 60)

    # Step 1: Verifica connessione
    logger.info("\n📡 Step 1: Verifica connessione database...")
    if not check_database_connection():
        logger.error("❌ Impossibile connettersi al database!")
        logger.error("   Verifica che DATABASE_URL sia configurato correttamente")
        return False

    logger.info("✅ Connessione database OK")

    # Step 2: Carica SQL
    logger.info("\n📄 Step 2: Carica script SQL...")
    try:
        sql_content = read_sql_file()
        logger.info(f"✅ Script SQL caricato ({len(sql_content)} caratteri)")
    except Exception as e:
        logger.error(f"❌ Errore lettura file SQL: {e}")
        return False

    # Step 3: Esegui SQL
    logger.info("\n⚡ Step 3: Esecuzione script SQL...")
    engine = get_engine()
    try:
        execute_sql(engine, sql_content)
    except Exception as e:
        logger.error(f"❌ Esecuzione fallita: {e}")
        return False

    # Step 4: Verifica tabelle
    logger.info("\n🔍 Step 4: Verifica tabelle...")
    if not verify_tables(engine):
        logger.error("❌ Tabelle non create correttamente!")
        return False

    # Step 5: Verifica indici
    logger.info("\n🔍 Step 5: Verifica indici...")
    if not verify_indexes(engine):
        logger.warning("⚠️ Nessun indice trovato (potrebbe essere ok se già esistevano)")

    # Step 6: Verifica dati test
    logger.info("\n🔍 Step 6: Verifica dati di test...")
    if not verify_test_data(engine):
        logger.warning("⚠️ Dati di test non trovati (potrebbero essere già stati cancellati)")

    # Success!
    logger.info("\n" + "=" * 60)
    logger.info("🎉 SETUP COMPLETATO CON SUCCESSO!")
    logger.info("=" * 60)
    logger.info("")
    logger.info("✅ 2 nuove tabelle create:")
    logger.info("   - user_sessions (sessioni utente)")
    logger.info("   - session_events (eventi tracciati)")
    logger.info("")
    logger.info("✅ Trigger e funzioni configurate:")
    logger.info("   - Auto-update last_activity")
    logger.info("   - Cleanup sessioni vecchie")
    logger.info("")
    logger.info("🚀 Syd Agent ora può tracciare TUTTO!")
    logger.info("")

    return True


if __name__ == "__main__":
    try:
        success = main()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        logger.warning("\n⚠️ Esecuzione interrotta dall'utente")
        sys.exit(1)
    except Exception as e:
        logger.error(f"\n❌ Errore inaspettato: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
