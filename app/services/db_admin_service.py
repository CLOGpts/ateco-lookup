"""
DB Admin Service - Business logic for database administration.

Extracted from main.py for modular architecture.
Handles database setup, table management, and data migration operations.
"""
import logging
from typing import Dict, List, Any, Optional
from pathlib import Path
import json

logger = logging.getLogger(__name__)


class DBAdminService:
    """
    Service for database administration operations.

    Handles:
    - Database setup and initialization
    - Table creation and verification
    - Data migration (risk events, ATECO codes, seismic zones)
    - Feedback table management
    """

    def __init__(self):
        """Initialize DB Admin service."""
        logger.info("DBAdminService initialized")

    def setup_database(self) -> Dict[str, Any]:
        """
        Execute database setup for Syd Agent tracking tables.

        IMPORTANT: Use this endpoint ONLY to initialize database.

        Returns:
            Dict with setup steps and success status
        """
        from database.setup_syd_tracking import (
            read_sql_file,
            execute_sql,
            verify_tables,
            verify_indexes,
            verify_test_data
        )
        from database.config import get_engine, check_database_connection

        results = {
            "steps": [],
            "success": False
        }

        # Step 1: Check connection
        results["steps"].append({"step": 1, "name": "Verifica connessione", "status": "running"})
        if not check_database_connection():
            results["steps"][-1]["status"] = "failed"
            results["steps"][-1]["error"] = "Impossibile connettersi al database"
            raise ConnectionError("Cannot connect to database")
        results["steps"][-1]["status"] = "completed"

        # Step 2: Load SQL
        results["steps"].append({"step": 2, "name": "Carica SQL", "status": "running"})
        try:
            sql_content = read_sql_file()
            results["steps"][-1]["status"] = "completed"
            results["steps"][-1]["sql_size"] = len(sql_content)
        except Exception as e:
            results["steps"][-1]["status"] = "failed"
            results["steps"][-1]["error"] = str(e)
            raise

        # Step 3: Execute SQL
        results["steps"].append({"step": 3, "name": "Esegui SQL", "status": "running"})
        engine = get_engine()
        try:
            execute_sql(engine, sql_content)
            results["steps"][-1]["status"] = "completed"
        except Exception as e:
            results["steps"][-1]["status"] = "failed"
            results["steps"][-1]["error"] = str(e)
            raise

        # Step 4: Verify tables
        results["steps"].append({"step": 4, "name": "Verifica tabelle", "status": "running"})
        if not verify_tables(engine):
            results["steps"][-1]["status"] = "failed"
            results["steps"][-1]["error"] = "Tabelle non create"
            raise RuntimeError("Tables not created")
        results["steps"][-1]["status"] = "completed"

        # Step 5: Verify indexes
        results["steps"].append({"step": 5, "name": "Verifica indici", "status": "running"})
        if not verify_indexes(engine):
            results["steps"][-1]["status"] = "warning"
            results["steps"][-1]["message"] = "Nessun indice trovato (potrebbero già esistere)"
        else:
            results["steps"][-1]["status"] = "completed"

        # Step 6: Verify test data
        results["steps"].append({"step": 6, "name": "Verifica dati test", "status": "running"})
        if not verify_test_data(engine):
            results["steps"][-1]["status"] = "warning"
            results["steps"][-1]["message"] = "Dati test non trovati"
        else:
            results["steps"][-1]["status"] = "completed"

        results["success"] = True
        results["message"] = "🎉 Setup completato con successo!"
        results["tables_created"] = ["user_sessions", "session_events"]

        return results

    def check_tables_status(self) -> Dict[str, Any]:
        """
        Verify which tables exist in the database.

        READ ONLY - does not modify anything.

        Returns:
            Dict with table status information
        """
        from database.config import get_engine
        from sqlalchemy import text, inspect

        engine = get_engine()
        inspector = inspect(engine)

        # Get all table names
        all_tables = inspector.get_table_names()

        # Target tables we want to check
        target_tables = {
            "users": "Consultanti (100 utenti)",
            "companies": "Aziende clienti (500)",
            "assessments": "Valutazioni rischio (50K)",
            "risk_events": "191 eventi rischio",
            "ateco_codes": "25K codici ATECO",
            "seismic_zones": "8,102 comuni",
            "user_sessions": "Sessioni Syd Agent",
            "session_events": "Eventi tracking Syd"
        }

        results = {
            "total_tables": len(all_tables),
            "tables": {},
            "missing_tables": []
        }

        # Check each target table
        for table_name, description in target_tables.items():
            if table_name in all_tables:
                # Table exists, count rows
                try:
                    with engine.connect() as conn:
                        count = conn.execute(text(f"SELECT COUNT(*) FROM {table_name}")).scalar()
                        results["tables"][table_name] = {
                            "exists": True,
                            "row_count": count,
                            "description": description
                        }
                except Exception as e:
                    results["tables"][table_name] = {
                        "exists": True,
                        "row_count": None,
                        "error": str(e),
                        "description": description
                    }
            else:
                results["missing_tables"].append({
                    "name": table_name,
                    "description": description
                })

        results["status"] = "ok" if len(results["missing_tables"]) == 0 else "incomplete"

        return results

    def create_missing_tables(self) -> Dict[str, Any]:
        """
        Create missing tables in PostgreSQL database.

        SECURITY:
        - Does not delete existing tables
        - Does not modify existing data
        - Uses SQLAlchemy create_all (idempotent)

        Tables created:
        1. users (consultants)
        2. companies (client companies)
        3. assessments (risk assessments)
        4. risk_events (191 events)
        5. ateco_codes (25K codes)
        6. seismic_zones (8K municipalities)

        Returns:
            Dict with creation steps and results
        """
        from database.config import get_engine
        from database.models import Base
        from sqlalchemy import inspect

        results = {
            "steps": [],
            "success": False
        }

        # Step 1: Check connection
        results["steps"].append({
            "step": 1,
            "name": "Verifica connessione",
            "status": "running"
        })

        engine = get_engine()
        inspector = inspect(engine)

        results["steps"][-1]["status"] = "completed"

        # Step 2: Check existing tables
        results["steps"].append({
            "step": 2,
            "name": "Controlla tabelle esistenti",
            "status": "running"
        })

        existing_tables = inspector.get_table_names()
        results["steps"][-1]["status"] = "completed"
        results["steps"][-1]["existing_tables"] = existing_tables
        results["steps"][-1]["count"] = len(existing_tables)

        # Step 3: Create tables
        results["steps"].append({
            "step": 3,
            "name": "Crea tabelle mancanti",
            "status": "running"
        })

        logger.info("Creazione tabelle con Base.metadata.create_all()...")
        Base.metadata.create_all(bind=engine)

        results["steps"][-1]["status"] = "completed"
        logger.info("✅ Base.metadata.create_all() completato!")

        # Step 4: Verify new tables
        results["steps"].append({
            "step": 4,
            "name": "Verifica tabelle create",
            "status": "running"
        })

        # Refresh inspector
        inspector = inspect(engine)
        new_tables = inspector.get_table_names()

        created_tables = [t for t in new_tables if t not in existing_tables]

        results["steps"][-1]["status"] = "completed"
        results["steps"][-1]["new_tables"] = new_tables
        results["steps"][-1]["created_tables"] = created_tables
        results["steps"][-1]["total_count"] = len(new_tables)

        # Success
        results["success"] = True
        results["message"] = f"✅ Tabelle create con successo! ({len(created_tables)} nuove)"
        results["summary"] = {
            "before": len(existing_tables),
            "after": len(new_tables),
            "created": len(created_tables)
        }

        return results

    def migrate_risk_events(self) -> Dict[str, Any]:
        """
        Migrate 191 risk events from MAPPATURE_EXCEL_PERFETTE.json → PostgreSQL.

        SECURITY:
        - Skip events that already exist (no duplicates)
        - Atomic transaction (rollback on error)
        - Detailed step-by-step report

        Returns:
            Dict with migration results
        """
        from database.config import get_db_session
        from database.models import RiskEvent

        results = {
            "steps": [],
            "success": False
        }

        # Step 1: Load JSON file
        results["steps"].append({
            "step": 1,
            "name": "Carica MAPPATURE_EXCEL_PERFETTE.json",
            "status": "running"
        })

        json_path = Path(__file__).parent.parent.parent / "MAPPATURE_EXCEL_PERFETTE.json"

        if not json_path.exists():
            results["steps"][-1]["status"] = "failed"
            results["steps"][-1]["error"] = f"File non trovato: {json_path}"
            raise FileNotFoundError(f"File not found: {json_path}")

        with open(json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        results["steps"][-1]["status"] = "completed"
        results["steps"][-1]["file_size"] = len(json.dumps(data))

        # Step 2: Parse events
        results["steps"].append({
            "step": 2,
            "name": "Parse eventi da JSON",
            "status": "running"
        })

        vlookup_map = data.get("vlookup_map", {})
        mappature_categoria = data.get("mappature_categoria_eventi", {})

        events_to_insert = []
        for code, description in vlookup_map.items():
            # Find category for this event
            category = None
            for cat_name, cat_events in mappature_categoria.items():
                for event_line in cat_events:
                    if event_line.startswith(code):
                        category = cat_name
                        break
                if category:
                    break

            events_to_insert.append({
                "code": code,
                "description": description,
                "category": category or "unknown"
            })

        results["steps"][-1]["status"] = "completed"
        results["steps"][-1]["events_parsed"] = len(events_to_insert)

        # Step 3: Insert into database
        results["steps"].append({
            "step": 3,
            "name": "Inserisci in database",
            "status": "running"
        })

        session = get_db_session()
        inserted = 0
        skipped = 0

        try:
            for event in events_to_insert:
                # Check if exists
                existing = session.query(RiskEvent).filter_by(code=event["code"]).first()
                if existing:
                    skipped += 1
                    continue

                # Insert new
                new_event = RiskEvent(
                    code=event["code"],
                    description=event["description"],
                    category=event["category"]
                )
                session.add(new_event)
                inserted += 1

            session.commit()
            results["steps"][-1]["status"] = "completed"
            results["steps"][-1]["inserted"] = inserted
            results["steps"][-1]["skipped"] = skipped

        except Exception as e:
            session.rollback()
            results["steps"][-1]["status"] = "failed"
            results["steps"][-1]["error"] = str(e)
            raise
        finally:
            session.close()

        results["success"] = True
        results["message"] = f"✅ Migrazione completata! ({inserted} inseriti, {skipped} saltati)"

        return results

    def migrate_ateco_codes(self, df) -> Dict[str, Any]:
        """
        Migrate ATECO codes from DataFrame → PostgreSQL.

        Args:
            df: DataFrame with ATECO codes

        Returns:
            Dict with migration results
        """
        from database.config import get_db_session
        from database.models import ATECOCode

        results = {
            "steps": [],
            "success": False
        }

        # Step 1: Analyze DataFrame
        results["steps"].append({
            "step": 1,
            "name": "Analizza DataFrame ATECO",
            "status": "running"
        })

        total_rows = len(df)
        results["steps"][-1]["status"] = "completed"
        results["steps"][-1]["total_rows"] = total_rows

        # Step 2: Insert into database
        results["steps"].append({
            "step": 2,
            "name": "Inserisci in database",
            "status": "running"
        })

        session = get_db_session()
        inserted = 0
        skipped = 0

        try:
            for _, row in df.iterrows():
                code_2025 = str(row.get('CODICE_ATECO_2025_RAPPRESENTATIVO', ''))
                if not code_2025 or code_2025 == 'nan':
                    continue

                # Check if exists
                existing = session.query(ATECOCode).filter_by(code_2025=code_2025).first()
                if existing:
                    skipped += 1
                    continue

                # Insert new
                new_code = ATECOCode(
                    code_2025=code_2025,
                    description_2025=str(row.get('DESCRIZIONE_2025', '')),
                    code_2022=str(row.get('CODICE_ATECO_2022', '')),
                    description_2022=str(row.get('DESCRIZIONE_2022', ''))
                )
                session.add(new_code)
                inserted += 1

                # Commit every 1000 rows
                if inserted % 1000 == 0:
                    session.commit()
                    logger.info(f"Committed {inserted} ATECO codes...")

            session.commit()
            results["steps"][-1]["status"] = "completed"
            results["steps"][-1]["inserted"] = inserted
            results["steps"][-1]["skipped"] = skipped

        except Exception as e:
            session.rollback()
            results["steps"][-1]["status"] = "failed"
            results["steps"][-1]["error"] = str(e)
            raise
        finally:
            session.close()

        results["success"] = True
        results["message"] = f"✅ Migrazione ATECO completata! ({inserted} inseriti, {skipped} saltati)"

        return results

    def migrate_seismic_zones(self) -> Dict[str, Any]:
        """
        Migrate seismic zones from JSON → PostgreSQL.

        Returns:
            Dict with migration results
        """
        from database.config import get_db_session
        from database.models import SeismicZone

        results = {
            "steps": [],
            "success": False
        }

        # Step 1: Load JSON
        results["steps"].append({
            "step": 1,
            "name": "Carica zone_sismiche_comuni.json",
            "status": "running"
        })

        json_path = Path(__file__).parent.parent.parent / "zone_sismiche_comuni.json"

        if not json_path.exists():
            results["steps"][-1]["status"] = "failed"
            results["steps"][-1]["error"] = f"File non trovato: {json_path}"
            raise FileNotFoundError(f"File not found: {json_path}")

        with open(json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        comuni_data = data.get("comuni", {})
        results["steps"][-1]["status"] = "completed"
        results["steps"][-1]["total_comuni"] = len(comuni_data)

        # Step 2: Insert into database
        results["steps"].append({
            "step": 2,
            "name": "Inserisci in database",
            "status": "running"
        })

        session = get_db_session()
        inserted = 0
        skipped = 0

        try:
            for comune_name, comune_data in comuni_data.items():
                # Check if exists
                existing = session.query(SeismicZone).filter_by(comune=comune_name).first()
                if existing:
                    skipped += 1
                    continue

                # Insert new
                new_zone = SeismicZone(
                    comune=comune_name,
                    provincia=comune_data.get("provincia", ""),
                    zona=comune_data.get("zona", ""),
                    ag=comune_data.get("ag", 0.0),
                    risk_level=comune_data.get("risk_level", ""),
                    description=comune_data.get("description", "")
                )
                session.add(new_zone)
                inserted += 1

                # Commit every 1000 rows
                if inserted % 1000 == 0:
                    session.commit()
                    logger.info(f"Committed {inserted} seismic zones...")

            session.commit()
            results["steps"][-1]["status"] = "completed"
            results["steps"][-1]["inserted"] = inserted
            results["steps"][-1]["skipped"] = skipped

        except Exception as e:
            session.rollback()
            results["steps"][-1]["status"] = "failed"
            results["steps"][-1]["error"] = str(e)
            raise
        finally:
            session.close()

        results["success"] = True
        results["message"] = f"✅ Migrazione zone sismiche completata! ({inserted} inseriti, {skipped} saltati)"

        return results

    def create_feedback_table(self) -> Dict[str, Any]:
        """
        Create user_feedback table in PostgreSQL database.

        SECURITY:
        - This endpoint is protected (admin call only once)
        - Uses IF NOT EXISTS to avoid errors if already exists

        CALL ONCE ONLY:
        POST https://celerya-cyber-ateco-production.up.railway.app/admin/create-feedback-table

        Returns:
            Dict with creation results
        """
        from database.config import get_engine
        from sqlalchemy import text

        results = {"steps": []}
        engine = get_engine()

        # SQL to create table (with IF NOT EXISTS for safety)
        sql_create_table = """
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

        with engine.connect() as conn:
            trans = conn.begin()
            try:
                # Execute table creation
                conn.execute(text(sql_create_table))
                trans.commit()
                results["steps"].append("✅ Tabella user_feedback creata")
                logger.info("✅ Tabella user_feedback creata con successo")

                # Verify table
                result = conn.execute(text("""
                    SELECT column_name, data_type
                    FROM information_schema.columns
                    WHERE table_name = 'user_feedback'
                    ORDER BY ordinal_position;
                """))
                columns = result.fetchall()
                results["steps"].append(f"✅ Trovate {len(columns)} colonne")

                # Verify indexes
                result = conn.execute(text("""
                    SELECT indexname
                    FROM pg_indexes
                    WHERE tablename = 'user_feedback';
                """))
                indexes = result.fetchall()
                results["steps"].append(f"✅ Trovati {len(indexes)} indici")

            except Exception as e:
                trans.rollback()
                raise e

        logger.info("🎉 Tabella user_feedback setup completato!")

        return {
            "success": True,
            "message": "Tabella user_feedback creata con successo",
            "steps": results["steps"]
        }
