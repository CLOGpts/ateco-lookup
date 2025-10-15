"""
Script di Migrazione: Eventi di Rischio
========================================

Questo script legge il file MAPPATURE_EXCEL_PERFETTE.json e inserisce
i 191 eventi di rischio nella tabella PostgreSQL 'risk_events'.

COSA FA:
1. Legge JSON con 7 categorie Basel II/III
2. Estrae codice evento (es: "101") e nome (es: "Disastro naturale: fuoco")
3. Inserisce nel database PostgreSQL Railway

COME USARE:
    python database/migrate_risk_events.py

Author: Claude + Claudio
Date: 2025-10-11
"""

import json
import sys
import os
from pathlib import Path

# Aggiungi cartella parent al path per import
sys.path.insert(0, str(Path(__file__).parent.parent))

from database.config import get_db_session
from database.models import RiskEvent


# ==================== CONFIGURATION ====================

# Mappatura categorie: JSON key → Nome leggibile
CATEGORY_MAPPING = {
    "Damage_Danni": "Damage/Danni",
    "Business_disruption": "Business Disruption",
    "Employment_practices_Dipendenti": "Employment Practices",
    "Execution_delivery_Problemi_di_produzione_o_consegna": "Execution & Delivery",
    "Clients_product_Clienti": "Clients & Products",
    "Internal_Fraud_Frodi_interne": "Internal Fraud",
    "External_fraud_Frodi_esterne": "External Fraud"
}

# Severity mapping (codici 100-199 = low, 200-399 = medium, 400+ = high)
def get_severity(code: str) -> str:
    """
    Determina severity dell'evento dal codice

    Logica:
    - 100-199: Low (danni fisici)
    - 200-299: Medium (business disruption)
    - 300-499: High (frodi, clienti, produzione)
    - 500+: Critical
    """
    code_num = int(code)
    if code_num < 200:
        return "low"
    elif code_num < 300:
        return "medium"
    elif code_num < 500:
        return "high"
    else:
        return "critical"


# ==================== PARSING FUNCTIONS ====================

def parse_event_line(line: str) -> tuple[str, str]:
    """
    Estrae codice e nome da una riga tipo: "101 - Disastro naturale: fuoco"

    Returns:
        (code, name): Tupla con codice e nome evento

    Example:
        >>> parse_event_line("101 - Disastro naturale: fuoco")
        ("101", "Disastro naturale: fuoco")
    """
    # Split su primo " - " (dash con spazi)
    parts = line.split(" - ", 1)

    if len(parts) != 2:
        print(f"  ⚠️ ATTENZIONE: Formato evento non standard: {line}")
        return None, None

    code = parts[0].strip()
    name = parts[1].strip()

    return code, name


def load_json_file(filepath: str) -> dict:
    """
    Carica file JSON mappature
    """
    print(f"📂 Caricamento file: {filepath}")

    with open(filepath, 'r', encoding='utf-8') as f:
        data = json.load(f)

    print(f"✅ File caricato con successo")
    return data


# ==================== DATABASE OPERATIONS ====================

def insert_risk_events(events_data: dict) -> tuple[int, int]:
    """
    Inserisce eventi nel database PostgreSQL

    Args:
        events_data: Dizionario con categorie ed eventi

    Returns:
        (inserted, skipped): Numero eventi inseriti e saltati
    """
    print("\n🔄 Inizio migrazione eventi nel database...")
    print("=" * 60)

    inserted = 0
    skipped = 0
    errors = []

    with get_db_session() as session:

        for category_key, events_list in events_data['mappature_categoria_eventi'].items():

            # Ottieni nome categoria leggibile
            category_name = CATEGORY_MAPPING.get(category_key, category_key)

            print(f"\n📁 Categoria: {category_name}")
            print(f"   Eventi da processare: {len(events_list)}")

            for event_line in events_list:
                # Parse evento
                code, name = parse_event_line(event_line)

                if not code or not name:
                    skipped += 1
                    errors.append(f"Parse fallito: {event_line}")
                    continue

                # Determina severity
                severity = get_severity(code)

                # Controlla se evento esiste già
                existing = session.query(RiskEvent).filter_by(code=code).first()

                if existing:
                    print(f"   ⏭️  {code} - Già esistente, skip")
                    skipped += 1
                    continue

                # Crea nuovo evento
                risk_event = RiskEvent(
                    code=code,
                    name=name,
                    category=category_name,
                    description=None,  # Da aggiungere in futuro
                    severity=severity,
                    suggested_controls=None  # Da aggiungere in futuro
                )

                session.add(risk_event)
                inserted += 1

                print(f"   ✅ {code} - {name[:50]}{'...' if len(name) > 50 else ''}")

        # Commit tutti gli inserimenti
        print(f"\n💾 Commit al database...")
        session.commit()
        print(f"✅ Commit completato con successo!")

    # Report finale
    print("\n" + "=" * 60)
    print("📊 MIGRAZIONE COMPLETATA")
    print("=" * 60)
    print(f"✅ Eventi inseriti: {inserted}")
    print(f"⏭️  Eventi saltati:  {skipped}")

    if errors:
        print(f"\n⚠️  ERRORI ({len(errors)}):")
        for error in errors[:5]:  # Mostra primi 5 errori
            print(f"   - {error}")
        if len(errors) > 5:
            print(f"   ... e altri {len(errors) - 5} errori")

    return inserted, skipped


# ==================== MAIN ====================

def main():
    """
    Funzione principale di migrazione
    """
    print("=" * 60)
    print("🚀 MIGRAZIONE EVENTI DI RISCHIO → PostgreSQL")
    print("=" * 60)

    # Path file JSON
    json_filepath = Path(__file__).parent.parent / "MAPPATURE_EXCEL_PERFETTE.json"

    if not json_filepath.exists():
        print(f"❌ ERRORE: File non trovato: {json_filepath}")
        return 1

    try:
        # 1. Carica JSON
        events_data = load_json_file(json_filepath)

        # 2. Inserisci nel database
        inserted, skipped = insert_risk_events(events_data)

        # 3. Verifica
        print("\n🔍 Verifica finale...")
        with get_db_session() as session:
            total_in_db = session.query(RiskEvent).count()
            print(f"📊 Totale eventi nel database: {total_in_db}")

        if total_in_db != 191:
            print(f"⚠️  ATTENZIONE: Attesi 191 eventi, trovati {total_in_db}")
        else:
            print(f"✅ PERFETTO! Database contiene tutti i 191 eventi!")

        print("\n" + "=" * 60)
        print("🎉 MIGRAZIONE COMPLETATA CON SUCCESSO!")
        print("=" * 60)

        return 0

    except Exception as e:
        print(f"\n❌ ERRORE FATALE durante migrazione:")
        print(f"   {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
