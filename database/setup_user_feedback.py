"""
Script per creare tabella User Feedback
Esegue add_user_feedback_table.sql e verifica risultati

Uso: python database/setup_user_feedback.py
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
    sql_file = Path(__file__).parent / "add_user_feedback_table.sql"

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


def verify_table(engine):
    """Verifica che la tabella sia stata creata"""
    logger.info("🔍 Verifica tabella user_feedback...")

    with engine.connect() as conn:
        # Check table exists
        result = conn.execute(text("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables
                WHERE table_name = 'user_feedback'
            );
        """))
        exists = result.scalar()

        if not exists:
            logger.error("❌ Tabella user_feedback NON trovata!")
            return False

        logger.info("✅ Tabella user_feedback trovata!")

        # Check columns
        result = conn.execute(text("""
            SELECT column_name, data_type
            FROM information_schema.columns
            WHERE table_name = 'user_feedback'
            ORDER BY ordinal_position;
        """))

        columns = result.fetchall()
        logger.info(f"📊 Colonne trovate ({len(columns)}):")
        for col_name, col_type in columns:
            logger.info(f"   - {col_name}: {col_type}")

        # Check indexes
        result = conn.execute(text("""
            SELECT indexname
            FROM pg_indexes
            WHERE tablename = 'user_feedback';
        """))

        indexes = result.fetchall()
        logger.info(f"🔑 Indici trovati ({len(indexes)}):")
        for idx in indexes:
            logger.info(f"   - {idx[0]}")

        return True


def main():
    """Main execution"""
    logger.info("=" * 80)
    logger.info("🚀 SETUP USER FEEDBACK TABLE")
    logger.info("=" * 80)

    try:
        # 1. Check database connection
        logger.info("\n1️⃣ Verifica connessione database...")
        if not check_database_connection():
            logger.error("❌ Impossibile connettersi al database!")
            return False

        # 2. Get engine
        engine = get_engine()

        # 3. Read SQL file
        logger.info("\n2️⃣ Lettura file SQL...")
        sql_content = read_sql_file()
        logger.info(f"✅ File SQL letto ({len(sql_content)} caratteri)")

        # 4. Execute SQL
        logger.info("\n3️⃣ Esecuzione SQL script...")
        execute_sql(engine, sql_content)

        # 5. Verify table
        logger.info("\n4️⃣ Verifica risultati...")
        verify_table(engine)

        logger.info("\n" + "=" * 80)
        logger.info("✅ SETUP COMPLETATO CON SUCCESSO!")
        logger.info("=" * 80)
        logger.info("\n📋 Prossimi passi:")
        logger.info("   1. Implementa endpoint POST /api/feedback in main.py")
        logger.info("   2. Crea componente FeedbackForm.tsx nel frontend")
        logger.info("   3. Testa invio feedback e notifica Telegram\n")

        return True

    except Exception as e:
        logger.error(f"\n❌ ERRORE: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
