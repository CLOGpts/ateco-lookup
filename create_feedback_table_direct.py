#!/usr/bin/env python3
"""
Script per creare tabella user_feedback direttamente su Railway PostgreSQL

Uso: python create_feedback_table_direct.py

IMPORTANTE: Richiede DATABASE_URL environment variable
"""

import os
import sys
from pathlib import Path

# Add parent to path for imports
sys.path.insert(0, str(Path(__file__).parent))

try:
    from database.config import get_engine
    from sqlalchemy import text
except ImportError as e:
    print(f"❌ Import error: {e}")
    print("Assicurati di aver installato le dipendenze: pip install -r requirements.txt")
    sys.exit(1)


def main():
    print("=" * 80)
    print("🚀 CREAZIONE TABELLA USER_FEEDBACK")
    print("=" * 80)

    # Check DATABASE_URL
    if not os.getenv("DATABASE_URL"):
        print("\n❌ DATABASE_URL non trovato nelle environment variables!")
        print("\nPer Railway PostgreSQL:")
        print("1. Vai su railway.app → tuo progetto")
        print("2. Variables → Copia DATABASE_URL")
        print("3. Esporta: export DATABASE_URL='postgres://...'")
        print("4. Riprova questo script\n")
        sys.exit(1)

    print(f"\n✅ DATABASE_URL trovato")

    try:
        # Get engine
        print("\n1️⃣ Connessione al database...")
        engine = get_engine()
        print("✅ Connesso!")

        # SQL to create table
        sql_create = """
        CREATE TABLE IF NOT EXISTS user_feedback (
            id SERIAL PRIMARY KEY,

            -- User identification
            user_id VARCHAR(255),
            session_id VARCHAR(255) NOT NULL,

            -- Quantitative feedback (scale 1-5 or 1-4)
            impression_ui INTEGER CHECK (impression_ui BETWEEN 1 AND 5),
            impression_utility INTEGER CHECK (impression_utility BETWEEN 1 AND 5),
            ease_of_use INTEGER CHECK (ease_of_use BETWEEN 1 AND 4),
            innovation INTEGER CHECK (innovation BETWEEN 1 AND 4),
            syd_helpfulness INTEGER CHECK (syd_helpfulness BETWEEN 1 AND 4),
            assessment_clarity INTEGER CHECK (assessment_clarity BETWEEN 1 AND 4),

            -- Qualitative feedback (open text)
            liked_most TEXT,
            improvements TEXT,

            -- Metadata
            created_at TIMESTAMP DEFAULT NOW(),
            user_email VARCHAR(255),
            assessment_id INTEGER,

            -- One feedback per session
            CONSTRAINT user_feedback_session_unique UNIQUE (session_id)
        );

        -- Create indexes
        CREATE INDEX IF NOT EXISTS idx_user_feedback_user_id ON user_feedback(user_id);
        CREATE INDEX IF NOT EXISTS idx_user_feedback_created_at ON user_feedback(created_at DESC);
        CREATE INDEX IF NOT EXISTS idx_user_feedback_session_id ON user_feedback(session_id);

        -- Add table comment
        COMMENT ON TABLE user_feedback IS 'User feedback collected after first risk assessment completion';
        """

        print("\n2️⃣ Esecuzione SQL script...")
        with engine.connect() as conn:
            trans = conn.begin()
            try:
                conn.execute(text(sql_create))
                trans.commit()
                print("✅ Tabella user_feedback creata!")
            except Exception as e:
                trans.rollback()
                raise e

        # Verify table
        print("\n3️⃣ Verifica tabella...")
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
                print("❌ Tabella NON trovata!")
                sys.exit(1)

            print("✅ Tabella esistente verificata!")

            # Count columns
            result = conn.execute(text("""
                SELECT COUNT(*)
                FROM information_schema.columns
                WHERE table_name = 'user_feedback';
            """))
            col_count = result.scalar()
            print(f"✅ Colonne trovate: {col_count}")

            # Count indexes
            result = conn.execute(text("""
                SELECT COUNT(*)
                FROM pg_indexes
                WHERE tablename = 'user_feedback';
            """))
            idx_count = result.scalar()
            print(f"✅ Indici trovati: {idx_count}")

        print("\n" + "=" * 80)
        print("🎉 SETUP COMPLETATO CON SUCCESSO!")
        print("=" * 80)
        print("\n📋 Prossimi passi:")
        print("   1. Deploy backend su Railway (se non già fatto)")
        print("   2. Test endpoint POST /api/feedback dal frontend")
        print("   3. Verifica ricezione messaggio Telegram\n")

        return True

    except Exception as e:
        print(f"\n❌ ERRORE: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
