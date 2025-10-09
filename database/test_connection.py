"""
Script di test connessione database PostgreSQL

Verifica che:
1. DATABASE_URL sia configurata
2. PostgreSQL sia raggiungibile
3. Connection pool funzioni
4. Tabelle possano essere create

Usage:
    python database/test_connection.py
"""

import sys
import os

# Aggiungi parent directory al path per import
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database.config import (
    check_database_connection,
    get_pool_status,
    get_engine,
    DatabaseConfig
)
from database.models import Base, User, get_sample_data


def test_connection():
    """Test 1: Verifica connessione base"""
    print("\n" + "="*60)
    print("TEST 1: Connessione Database")
    print("="*60)

    try:
        if check_database_connection():
            print("✅ Connessione PostgreSQL: OK")
            return True
        else:
            print("❌ Connessione PostgreSQL: FALLITA")
            return False
    except Exception as e:
        print(f"❌ Errore connessione: {e}")
        return False


def test_config():
    """Test 2: Verifica configurazione"""
    print("\n" + "="*60)
    print("TEST 2: Configurazione")
    print("="*60)

    try:
        config = DatabaseConfig()
        print(f"📝 Database URL: {config.database_url[:50]}...")
        print(f"🔧 Pool Size: {config.pool_size}")
        print(f"🔧 Max Overflow: {config.max_overflow}")
        print(f"⏱️  Pool Timeout: {config.pool_timeout}s")
        print(f"♻️  Pool Recycle: {config.pool_recycle}s")
        print("✅ Configurazione: OK")
        return True
    except Exception as e:
        print(f"❌ Errore configurazione: {e}")
        return False


def test_pool():
    """Test 3: Verifica connection pool"""
    print("\n" + "="*60)
    print("TEST 3: Connection Pool")
    print("="*60)

    try:
        status = get_pool_status()
        print(f"📊 Pool Size: {status['pool_size']}")
        print(f"📊 Checked Out: {status['checked_out']}")
        print(f"📊 Overflow: {status['overflow']}")
        print(f"📊 Checked In: {status['checked_in']}")
        print(f"📊 Status: {status['status']}")

        if status['status'] == 'healthy':
            print("✅ Connection Pool: OK")
            return True
        else:
            print("⚠️ Connection Pool: WARNING")
            return False
    except Exception as e:
        print(f"❌ Errore pool: {e}")
        return False


def test_create_tables():
    """Test 4: Prova a creare tabelle"""
    print("\n" + "="*60)
    print("TEST 4: Creazione Tabelle")
    print("="*60)

    try:
        engine = get_engine()
        print("📝 Creazione tabelle...")

        # Crea tutte le tabelle definite nei modelli
        Base.metadata.create_all(engine)

        # Conta tabelle create
        from sqlalchemy import inspect
        inspector = inspect(engine)
        tables = inspector.get_table_names()

        print(f"✅ Tabelle create: {len(tables)}")
        for table in tables:
            print(f"   - {table}")

        return True
    except Exception as e:
        print(f"❌ Errore creazione tabelle: {e}")
        return False


def test_insert_sample_data():
    """Test 5: Inserisci dati di test"""
    print("\n" + "="*60)
    print("TEST 5: Inserimento Dati Test")
    print("="*60)

    try:
        from database.config import get_db_session

        sample_data = get_sample_data()

        with get_db_session() as session:
            # Inserisci 3 utenti di test
            for user in sample_data["users"]:
                # Controlla se esiste già
                existing = session.query(User).filter_by(email=user.email).first()
                if not existing:
                    session.add(user)
                    print(f"➕ Utente creato: {user.name} ({user.email})")
                else:
                    print(f"⏭️  Utente già esiste: {user.name}")

            session.commit()

        print("✅ Dati di test inseriti: OK")
        return True
    except Exception as e:
        print(f"❌ Errore inserimento dati: {e}")
        return False


def test_query_data():
    """Test 6: Query dati"""
    print("\n" + "="*60)
    print("TEST 6: Query Dati")
    print("="*60)

    try:
        from database.config import get_db_session

        with get_db_session() as session:
            users = session.query(User).all()
            print(f"📊 Utenti nel database: {len(users)}")

            for user in users:
                print(f"   👤 {user.name} ({user.email}) - {user.role.value}")

        print("✅ Query dati: OK")
        return True
    except Exception as e:
        print(f"❌ Errore query: {e}")
        return False


def cleanup_test_data():
    """Opzionale: Pulisci dati di test"""
    print("\n" + "="*60)
    print("CLEANUP: Vuoi cancellare le tabelle di test? (y/n)")
    print("="*60)

    # In modalità automatica, non chiedere
    if "--auto" in sys.argv:
        return

    choice = input("Scelta: ").strip().lower()

    if choice == 'y':
        try:
            from database.config import drop_all_tables
            drop_all_tables()
            print("✅ Tabelle cancellate")
        except Exception as e:
            print(f"❌ Errore cancellazione: {e}")


def main():
    """Esegui tutti i test in sequenza"""
    print("\n" + "="*60)
    print("🧪 SYD CYBER - TEST DATABASE POSTGRESQL")
    print("="*60)
    print("Questo script verifica:")
    print("  1. Connessione a PostgreSQL")
    print("  2. Configurazione corretta")
    print("  3. Connection pool funzionante")
    print("  4. Creazione tabelle")
    print("  5. Inserimento dati")
    print("  6. Query dati")
    print("="*60)

    results = []

    # Esegui test
    results.append(("Connessione", test_connection()))
    results.append(("Configurazione", test_config()))
    results.append(("Connection Pool", test_pool()))
    results.append(("Creazione Tabelle", test_create_tables()))
    results.append(("Inserimento Dati", test_insert_sample_data()))
    results.append(("Query Dati", test_query_data()))

    # Cleanup (opzionale)
    cleanup_test_data()

    # Report finale
    print("\n" + "="*60)
    print("📊 REPORT FINALE")
    print("="*60)

    passed = sum(1 for _, result in results if result)
    total = len(results)

    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status} - {test_name}")

    print("="*60)
    print(f"Risultato: {passed}/{total} test passati")

    if passed == total:
        print("\n🎉 TUTTI I TEST PASSATI!")
        print("✅ Database PostgreSQL è pronto per l'uso!")
        return 0
    else:
        print("\n⚠️ ALCUNI TEST FALLITI")
        print("Controlla gli errori sopra e correggi la configurazione")
        return 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
