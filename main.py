#!/usr/bin/env python3
"""
ATECO Lookup – offline & API-ready (no ISTAT APIs)

Obiettivo: dato un codice ATECO, restituire subito tutte le informazioni (descrizioni 2022/2025,
ricodifiche, gerarchie) + arricchimento con normative e certificazioni dal mapping.yaml.
Funziona:
  • in locale via CLI
  • come micro-API FastAPI (per uso esterno dalla chat in futuro)

Dipendenze minime: pandas, openpyxl, pyyaml
Opzionali per API: fastapi, uvicorn

Installazione (Windows/macOS/Linux):
  pip install pandas openpyxl pyyaml
  # API opzionali
  pip install fastapi uvicorn

Esempi CLI:
  python ateco_lookup.py --file tabella_ATECO.xlsx --code 01.11.0
  python ateco_lookup.py --file tabella_ATECO.xlsx --code 01.11 --prefix
  python ateco_lookup.py --file tabella_ATECO.xlsx --code 01.11.00 --prefer 2025-camerale

Avvio API locali:
  python ateco_lookup.py --file tabella_ATECO.xlsx --serve --host 127.0.0.1 --port 8000
  # poi GET http://127.0.0.1:8000/lookup?code=01.11.0
"""
from __future__ import annotations
import argparse
import json
import logging
from functools import lru_cache
from pathlib import Path
from typing import Dict, List, Optional, Union
from difflib import get_close_matches
import os
import tempfile

import pandas as pd
import yaml

# Import FastAPI opzionali - necessari per l'API
try:
    from fastapi import FastAPI, Query, HTTPException, UploadFile, File, Body
    from fastapi.responses import JSONResponse
    from fastapi.middleware.cors import CORSMiddleware
    from pydantic import BaseModel
    from typing import List
    FASTAPI_AVAILABLE = True
except ImportError:
    FASTAPI_AVAILABLE = False

# Import condizionale per VisuraExtractor - verrà fatto dopo la configurazione del logger

# ----------------------- Caricamento mapping esterno -------------------------
def load_mapping(path: Path = Path("mapping.yaml")) -> dict:
    if not path.exists():
        return {}
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}

MAPPING = load_mapping()

# ----------------------- Header alias (tolleranza nomi) -----------------------
ALIASES = {
    "ORDINE_CODICE_ATECO_2022": ["ORDINE_CODICE_ATECO_2022", "ORDINE_CODICE"],
    "CODICE_ATECO_2022": ["CODICE_ATECO_2022", "CODICE ATECO 2022", "CODICE_ATECO"],
    "TITOLO_ATECO_2022": ["TITOLO_ATECO_2022", "TITOLO ATECO 2022", "TITOLO_2022", "TITOLO_ATECO"],
    "GERARCHIA_ATECO_2022": ["GERARCHIA_ATECO_2022", "GERARCHIA_ATEC", "GERARCHIA"],
    "NUMERO_CORR_ATECO_2022": ["NUMERO_CORR_ATECO_2022", "NUMERO_CORR_A", "N_CORR_2022"],
    "SOTTOTIPOLOGIA": ["SOTTOTIPOLOGIA"],
    "TIPO_RICODIFICA": ["TIPO_RICODIFICA"],
    "CODICE_ATECO_2025_RAPPRESENTATIVO": ["CODICE_ATECO_2025_RAPPRESENTATIVO", "CODICE ATECO 2025 RAPPRESENTATIVO"],
    "TITOLO_ATECO_2025_RAPPRESENTATIVO": ["TITOLO_ATECO_2025_RAPPRESENTATIVO", "TITOLO ATECO 2025 RAPPRESENTATIVO"],
    "CODICE_ATECO_2025_RAPPRESENTATIVO_SISTEMA_CAMERALE": [
        "CODICE_ATECO_2025_RAPPRESENTATIVO_SISTEMA_CAMERALE", "CODICE 2025 SISTEMA CAMERALE"
    ],
    "TITOLO_ATECO_2025_RAPPRESENTATIVO_SISTEMA_CAMERALE": [
        "TITOLO_ATECO_2025_RAPPRESENTATIVO_SISTEMA_CAMERALE", "TITOLO 2025 SISTEMA CAMERALE"
    ],
}
HEADER_RESOLVE: Dict[str, str] = {opt.lower(): std for std, lst in ALIASES.items() for opt in lst}

# ----------------------- Utils normalizzazione codici -------------------------
def normalize_code(raw: Union[str, float]) -> str:
    if pd.isna(raw):
        return ""
    return str(raw).strip().replace(",", ".").replace(" ", "").upper()

def strip_code(raw: Union[str, float]) -> str:
    if pd.isna(raw):
        return ""
    return "".join(ch for ch in str(raw) if ch.isalnum())

def code_variants(code: str) -> List[str]:
    c = normalize_code(code)
    if not c:
        return []
    parts = c.split(".")
    variants = {c, "".join(parts)}  # con punti e senza
    if c.endswith("."):
        variants.add(c[:-1])
    if parts and parts[-1].isdigit():
        last = parts[-1]
        if len(last) == 1:
            variants.add(".".join(parts[:-1] + [last + "0"]))
            variants.add(".".join(parts[:-1] + [last + "00"]))
        elif len(last) == 2:
            variants.add(".".join(parts[:-1] + [last + "0"]))
    return sorted(variants)

# ----------------------- Caricamento dataset ---------------------------------
def normalize_headers(df: pd.DataFrame) -> pd.DataFrame:
    mapping: Dict[str, str] = {}
    for col in df.columns:
        mapping[col] = HEADER_RESOLVE.get(str(col).strip().lower(), col)
    return df.rename(columns=mapping)

POSSIBLE_SHEETS = ["Tabella operativa", "tabella operativa", "Foglio1", "Sheet1"]

def load_dataset(path: Path, debug: bool = False) -> pd.DataFrame:
    if not path.exists():
        raise FileNotFoundError(f"File non trovato: {path}")
    xls = pd.ExcelFile(path)
    sheet_to_use = xls.sheet_names[0]
    for s in POSSIBLE_SHEETS:
        if s in xls.sheet_names:
            sheet_to_use = s
            break
    if debug:
        print("# sheets:", xls.sheet_names, "| using:", sheet_to_use)
    df = pd.read_excel(xls, sheet_name=sheet_to_use, dtype=str)
    df = normalize_headers(df)
    for key in [
        "CODICE_ATECO_2022",
        "CODICE_ATECO_2025_RAPPRESENTATIVO",
        "CODICE_ATECO_2025_RAPPRESENTATIVO_SISTEMA_CAMERALE",
    ]:
        if key in df.columns:
            df[key + "__NORM"] = df[key].apply(normalize_code)
            df[key + "__STRIP"] = df[key].apply(strip_code)
    return df

# ----------------------- Ricerca "smart" -------------------------------------
SEARCH_ORDER = [
    ("2022", "CODICE_ATECO_2022"),
    ("2025", "CODICE_ATECO_2025_RAPPRESENTATIVO"),
    ("2025-camerale", "CODICE_ATECO_2025_RAPPRESENTATIVO_SISTEMA_CAMERALE"),
]

@lru_cache(maxsize=500)
def cached_search(code: str, prefer: Optional[str], prefix: bool, df_hash: int):
    """Cached version of search. df_hash is used to invalidate cache if df changes."""
    global _global_df
    return search_smart_internal(_global_df, code, prefer, prefix)

def search_smart(df: pd.DataFrame, code: str, prefer: Optional[str] = None, prefix: bool = False) -> pd.DataFrame:
    """Wrapper that uses cache when possible."""
    global _global_df, _df_hash
    _global_df = df
    _df_hash = id(df)
    return cached_search(code, prefer, prefix, _df_hash)

def search_smart_internal(df: pd.DataFrame, code: str, prefer: Optional[str] = None, prefix: bool = False) -> pd.DataFrame:
    variants = code_variants(code)
    order = SEARCH_ORDER.copy()
    if prefer:
        order.sort(key=lambda x: 0 if x[0] == prefer else 1)

    for _, base in order:
        cols = [c for c in (base + "__NORM", base + "__STRIP", base) if c in df.columns]
        if not cols:
            continue
        mask = False
        for col in cols:
            ser = df[col].astype(str)
            mask = mask | ser.isin(variants)
        exact = df[mask]
        if not exact.empty:
            return exact

    if prefix:
        for _, base in order:
            cols = [c for c in (base + "__NORM", base + "__STRIP", base) if c in df.columns]
            if not cols:
                continue
            mask = False
            for col in cols:
                ser = df[col].astype(str)
                m = False
                for v in variants:
                    m = m | ser.str.startswith(v)
                mask = mask | m
            pref = df[mask]
            if not pref.empty:
                return pref

    base = "CODICE_ATECO_2022__NORM" if "CODICE_ATECO_2022__NORM" in df.columns else "CODICE_ATECO_2022"
    ser = df[base].astype(str)
    m = False
    for v in variants:
        m = m | ser.str.startswith(v)
    return df[m]

def find_similar_codes(df: pd.DataFrame, code: str, limit: int = 5) -> List[Dict[str, str]]:
    """Trova codici simili quando la ricerca non produce risultati."""
    code_norm = normalize_code(code)
    all_codes = df["CODICE_ATECO_2022"].dropna().unique()
    all_codes_norm = [normalize_code(c) for c in all_codes]
    
    # Trova corrispondenze simili
    matches = get_close_matches(code_norm, all_codes_norm, n=limit, cutoff=0.6)
    
    suggestions = []
    for match in matches:
        idx = all_codes_norm.index(match)
        original_code = all_codes[idx]
        row = df[df["CODICE_ATECO_2022"] == original_code].iloc[0]
        suggestions.append({
            "code": original_code,
            "title": row.get("TITOLO_ATECO_2022", "")
        })
    
    return suggestions

# ----------------------- Output helpers --------------------------------------
def flatten(row: pd.Series) -> Dict[str, Optional[str]]:
    data: Dict[str, Optional[str]] = {}
    for k, v in row.items():
        if k.endswith("__NORM") or k.endswith("__STRIP"):
            continue
        data[k] = None if pd.isna(v) else v
    return data

def enrich(item: dict) -> dict:
    """
    Arricchisce un item ATECO con settore, normative e certificazioni
    basandosi sul mapping.yaml.
    """
    code = item.get("CODICE_ATECO_2022", "") or ""
    settore = None

    if code.startswith("20"):
        settore = "chimico"
    elif code.startswith("10") or code.startswith("11"):
        settore = "alimentare"
    elif code.startswith("21") or code.startswith("86"):
        settore = "sanitario"
    elif code.startswith("29") or code.startswith("45"):
        settore = "automotive"
    elif code.startswith("25") or code.startswith("28"):
        settore = "industriale"
    elif code.startswith("62"):
        settore = "ict"
    elif code.startswith("64") or code.startswith("66"):
        settore = "finance"

    if settore and settore in MAPPING.get("settori", {}):
        item["settore"] = settore
        item["normative"] = MAPPING["settori"][settore].get("normative", [])
        item["certificazioni"] = MAPPING["settori"][settore].get("certificazioni", [])
    else:
        item["settore"] = settore or "non mappato"
        item["normative"] = []
        item["certificazioni"] = []

    return item

# ----------------------- CLI / API -------------------------------------------
def run_cli(args):
    df = load_dataset(args.file, debug=args.debug)
    res = search_smart(df, args.code, prefer=args.prefer, prefix=args.prefix)
    if res.empty:
        if args.pretty:
            print("NOT FOUND")
            return
        print(json.dumps({"found": 0, "items": []}, ensure_ascii=False, indent=2))
        return

    if not args.prefix:
        res = res.head(1)

    items = [enrich(flatten(r)) for _, r in res.iterrows()]

    if args.pretty:
        it = items[0]
        pairs = [
            ("CODICE_ATECO_2022", "TITOLO_ATECO_2022"),
            ("CODICE_ATECO_2025_RAPPRESENTATIVO", "TITOLO_ATECO_2025_RAPPRESENTATIVO"),
            ("CODICE_ATECO_2025_RAPPRESENTATIVO_SISTEMA_CAMERALE",
             "TITOLO_ATECO_2025_RAPPRESENTATIVO_SISTEMA_CAMERALE"),
        ]
        code_out, title_out = None, None
        for ccol, tcol in pairs:
            if it.get(ccol) and it.get(tcol):
                code_out, title_out = it[ccol], it[tcol]
                break
        code_out = code_out or it.get("CODICE_ATECO_2022") or it.get("CODICE_ATECO_2025_RAPPRESENTATIVO") or ""
        title_out = title_out or it.get("TITOLO_ATECO_2022") or it.get("TITOLO_ATECO_2025_RAPPRESENTATIVO") or it.get("TITOLO_ATECO_2025_RAPPRESENTATIVO_SISTEMA_CAMERALE") or ""
        print(f"{code_out} — {title_out}")
        return

    print(json.dumps({"found": len(items), "items": items}, ensure_ascii=False, indent=2))

# Configurazione logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Import condizionale per VisuraExtractor dopo configurazione logger
visura_extraction_available = False
VisuraExtractor = None
VisuraExtractorPower = None
VisuraExtractorFixed = None
VisuraExtractorFinal = None

# Variabili di stato per tracking importazioni
visura_final_available = False
visura_fixed_available = False
visura_power_available = False
visura_available = False

# PRIORITÀ 0: Prova FINAL (versione STRICT - SOLO 3 CAMPI)
try:
    from visura_extractor_FINAL_embedded import VisuraExtractorFinal
    visura_final_available = True
    visura_extraction_available = True
    logger.info("✅ VisuraExtractorFinal importato - VERSIONE STRICT (SOLO 3 CAMPI)")
except ImportError as e:
    logger.warning(f"VisuraExtractorFinal non disponibile: {e}")
except Exception as e:
    logger.error(f"Errore import VisuraExtractorFinal: {e}")

# PRIORITÀ 1: Prova FIXED (versione corretta)
try:
    from visura_extractor_fixed import VisuraExtractorFixed
    visura_fixed_available = True
    visura_extraction_available = True
    logger.info("✅ VisuraExtractorFixed importato - VERSIONE CORRETTA")
except ImportError as e:
    logger.warning(f"VisuraExtractorFixed non disponibile: {e}")
except Exception as e:
    logger.error(f"Errore import VisuraExtractorFixed: {e}")

# PRIORITÀ 2: Fallback su POWER
try:
    from visura_extractor_power import VisuraExtractorPower
    visura_power_available = True
    if not visura_extraction_available:
        visura_extraction_available = True
    logger.info("✅ VisuraExtractorPower importato come fallback")
except ImportError as e:
    logger.warning(f"VisuraExtractorPower non disponibile: {e}")
except Exception as e:
    logger.error(f"Errore import VisuraExtractorPower: {e}")

# PRIORITÀ 3: Modulo base rimosso - non più necessario
visura_available = False
VisuraExtractor = None

# Log stato finale
if not visura_extraction_available:
    logger.error("❌ NESSUN estrattore visure disponibile!")
else:
    available = []
    if visura_fixed_available: available.append("Fixed")
    if visura_power_available: available.append("Power") 
    if visura_available: available.append("Base")
    logger.info(f"📊 Estrattori disponibili: {', '.join(available)}")

# Variabili globali per cache
_global_df = None
_df_hash = None

# Pydantic models for API endpoints (must be global for FastAPI)
class BatchRequest(BaseModel):
    codes: List[str]
    prefer: Optional[str] = None
    prefix: bool = False

def build_api(df: pd.DataFrame):
    if not FASTAPI_AVAILABLE:
        raise ImportError("FastAPI non disponibile. Installa con: pip install fastapi uvicorn")
    
    if not visura_extraction_available:
        logger.warning("VisuraExtractor non disponibile")
        # Verifica quale dipendenza manca
        try:
            import pdfplumber
            logger.info("pdfplumber è installato")
        except ImportError:
            logger.warning("pdfplumber NON è installato")
        try:
            import PyPDF2
            logger.info("PyPDF2 è installato")
        except ImportError:
            logger.warning("PyPDF2 NON è installato")

    app = FastAPI(title="ATECO Lookup", version="2.0")

    # CORS configurazione sicura - Solo domini autorizzati
    ALLOWED_ORIGINS = [
        # Vercel production deployments
        "https://syd-cyber-ui.vercel.app",
        "https://syd-cyber-dario.vercel.app",
        "https://syd-cyber-marcello.vercel.app",
        "https://syd-cyber-claudio.vercel.app",
        # Localhost per development (sicuro - non accessibile da internet)
        "http://localhost:5173",
        "http://localhost:5174",
        "http://localhost:5175",
        "http://localhost:3000",
    ]

    app.add_middleware(
        CORSMiddleware,
        allow_origins=ALLOWED_ORIGINS,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        allow_headers=["Content-Type", "Authorization", "Accept"],
        expose_headers=["Content-Length", "Content-Type"],
    )
    
    # Middleware personalizzato per garantire CORS su errori
    @app.middleware("http")
    async def catch_exceptions_middleware(request, call_next):
        try:
            response = await call_next(request)
            return response
        except Exception as e:
            logger.error(f"Errore non gestito: {str(e)}", exc_info=True)
            # Assicura che gli header CORS siano presenti anche su errori
            return JSONResponse(
                status_code=500,
                content={
                    "success": False,
                    "error": {
                        "code": "INTERNAL_ERROR",
                        "message": "Errore interno del server",
                        "details": str(e)
                    }
                },
                headers={
                    "Access-Control-Allow-Origin": "*",
                    "Access-Control-Allow-Credentials": "true",
                }
            )

    @app.get("/health")
    def health():
        logger.info("Health check requested")
        return {"status": "ok", "version": "2.0", "cache_enabled": True}

    @app.get("/health/database")
    def health_database():
        """Test connessione database PostgreSQL"""
        logger.info("Database health check requested")
        try:
            from database.config import check_database_connection, get_pool_status

            # Test connessione
            connection_ok = check_database_connection()

            if connection_ok:
                # Ottieni status pool
                pool_status = get_pool_status()
                return {
                    "status": "ok",
                    "database": "postgresql",
                    "connection": "active",
                    "pool": pool_status
                }
            else:
                return {
                    "status": "error",
                    "database": "postgresql",
                    "connection": "failed",
                    "message": "Cannot connect to database"
                }
        except ImportError:
            return {
                "status": "warning",
                "message": "Database module not installed yet",
                "hint": "Run: pip install sqlalchemy psycopg2-binary"
            }
        except Exception as e:
            logger.error(f"Database health check failed: {e}")
            return {
                "status": "error",
                "message": str(e)
            }

    @app.get("/team/hello")
    async def team_hello():
        """Endpoint per sistema multi-agente"""
        from datetime import datetime
        return {
            "agent": "Backend Railway",
            "message": "Ciao team! Sono il backend",
            "capabilities": ["ATECO", "Risk API", "Database"],
            "timestamp": datetime.now().isoformat(),
            "status": "operational",
            "endpoints_available": [
                "/lookup", "/autocomplete", "/batch",
                "/events/{category}", "/risk-assessment-fields",
                "/api/extract-visura"
            ]
        }

    # ENDPOINT RISK MANAGEMENT - CON LOGICA EXCEL REALE
    # Carica i dati Excel corretti
    try:
        with open('MAPPATURE_EXCEL_PERFETTE.json', 'r', encoding='utf-8') as f:
            risk_data = json.load(f)
            EXCEL_CATEGORIES = risk_data['mappature_categoria_eventi']
            EXCEL_DESCRIPTIONS = risk_data['vlookup_map']
    except FileNotFoundError:
        logger.warning("⚠️ MAPPATURE_EXCEL_PERFETTE.json non trovato, uso fallback")
        EXCEL_CATEGORIES = {
            "Damage_Danni": [],
            "Business_disruption": [],
            "Employment_practices_Dipendenti": [],
            "Execution_delivery_Problemi_di_produzione_o_consegna": [],
            "Clients_product_Clienti": [],
            "Internal_Fraud_Frodi_interne": [],
            "External_fraud_Frodi_esterne": []
        }
        EXCEL_DESCRIPTIONS = {}
    except json.JSONDecodeError as e:
        logger.error(f"❌ MAPPATURE_EXCEL_PERFETTE.json corrotto: {e}")
        raise
    except Exception as e:
        logger.error(f"❌ Errore inaspettato caricando MAPPATURE_EXCEL_PERFETTE.json: {e}")
        raise
    
    
    # ENDPOINT ZONE SISMICHE - Database completo comuni italiani
    # ENDPOINT ADMIN - Database Setup
    # =====================================================
    # LEGACY ENDPOINTS - Backward Compatibility Proxies
    # =====================================================

    @app.post("/api/extract-visura")
    async def extract_visura_legacy(file: UploadFile = File(...)):
        """
        LEGACY ENDPOINT - Proxy to /visura/extract
        Kept for backward compatibility with frontend
        """
        from app.routers.visura import get_visura_service, extract_visura as visura_extract
        logger.info("📞 Legacy endpoint /api/extract-visura called, proxying to /visura/extract")
        # Get the service instance and call the endpoint function
        service = get_visura_service()
        return await visura_extract(file, service)

    @app.get("/api/test-visura")
    def test_visura_legacy():
        """
        LEGACY ENDPOINT - Proxy to /visura/test
        Kept for backward compatibility
        """
        from app.routers.visura import get_visura_service, test_visura as visura_test
        logger.info("📞 Legacy endpoint /api/test-visura called, proxying to /visura/test")
        # Get the service instance and call the endpoint function
        service = get_visura_service()
        return visura_test(service)

    # Risk endpoints legacy proxies
    @app.get("/description/{event_code}")
    def get_event_description_legacy(event_code: str):
        """LEGACY ENDPOINT - Proxy to /risk/description/{event_code}"""
        from app.routers.risk import get_risk_service, get_event_description
        logger.info(f"📞 Legacy endpoint /description/{event_code} called, proxying to /risk/description/{event_code}")
        service = get_risk_service()
        return get_event_description(event_code, service)

    @app.get("/risk-assessment-fields")
    def get_risk_assessment_fields_legacy():
        """LEGACY ENDPOINT - Proxy to /risk/assessment-fields"""
        from app.routers.risk import get_risk_assessment_fields
        logger.info("📞 Legacy endpoint /risk-assessment-fields called, proxying to /risk/assessment-fields")
        return get_risk_assessment_fields()

    @app.post("/save-risk-assessment")
    def save_risk_assessment_legacy(data: dict):
        """LEGACY ENDPOINT - Proxy to /risk/save-assessment"""
        from app.routers.risk import get_risk_service, save_risk_assessment
        logger.info("📞 Legacy endpoint /save-risk-assessment called, proxying to /risk/save-assessment")
        service = get_risk_service()
        return save_risk_assessment(data, service)

    @app.post("/calculate-risk-assessment")
    def calculate_risk_assessment_legacy(data: dict):
        """LEGACY ENDPOINT - Proxy to /risk/calculate-assessment"""
        from app.routers.risk import get_risk_service, calculate_risk_assessment
        logger.info("📞 Legacy endpoint /calculate-risk-assessment called, proxying to /risk/calculate-assessment")
        service = get_risk_service()
        return calculate_risk_assessment(data, service)

    # =====================================================
    # SYD AGENT - Event Tracking Endpoints
    # =====================================================

    @app.post("/api/events")
    async def save_event(payload: dict = Body(...)):
        """
        Salva evento utente per Syd Agent tracking

        Event types supportati:
        - ateco_uploaded: Caricamento codice ATECO
        - visura_extracted: Estrazione dati da visura
        - category_selected: Selezione categoria rischio
        - risk_evaluated: Valutazione rischio completata
        - assessment_question_answered: Risposta domanda assessment
        - report_generated: Report generato

        Body JSON:
        {
            "user_id": "test@example.com",
            "session_id": "uuid",
            "event_type": "ateco_uploaded",
            "event_data": {"code": "62.01"}
        }
        """
        try:
            from database.config import get_engine
            from sqlalchemy import text
            from datetime import datetime
            import uuid

            # Estrai parametri dal payload
            user_id = payload.get("user_id")
            session_id = payload.get("session_id")
            event_type = payload.get("event_type")
            event_data = payload.get("event_data", {})

            if not user_id or not session_id or not event_type:
                return JSONResponse({
                    "success": False,
                    "error": "missing_fields",
                    "message": "user_id, session_id e event_type sono obbligatori"
                }, status_code=400)

            engine = get_engine()

            with engine.connect() as conn:
                trans = conn.begin()
                try:
                    # Verifica se session_id esiste, altrimenti crea sessione
                    result = conn.execute(text("""
                        SELECT id FROM user_sessions WHERE session_id = :session_id
                    """), {"session_id": session_id})

                    if not result.fetchone():
                        # Crea nuova sessione
                        conn.execute(text("""
                            INSERT INTO user_sessions (user_id, session_id, phase, progress)
                            VALUES (:user_id, :session_id, 'idle', 0)
                        """), {
                            "user_id": user_id,
                            "session_id": session_id
                        })

                    # Salva evento
                    event_data_json = json.dumps(event_data)
                    conn.execute(text("""
                        INSERT INTO session_events (user_id, session_id, event_type, event_data)
                        VALUES (:user_id, :session_id, :event_type, CAST(:event_data AS jsonb))
                    """), {
                        "user_id": user_id,
                        "session_id": session_id,
                        "event_type": event_type,
                        "event_data": event_data_json
                    })

                    trans.commit()

                    return JSONResponse({
                        "success": True,
                        "message": "Evento salvato con successo",
                        "event": {
                            "user_id": user_id,
                            "session_id": session_id,
                            "event_type": event_type,
                            "timestamp": datetime.now().isoformat()
                        }
                    })

                except Exception as e:
                    trans.rollback()
                    raise e

        except Exception as e:
            logger.error(f"Errore salvataggio evento: {str(e)}", exc_info=True)
            return JSONResponse({
                "success": False,
                "error": "save_failed",
                "message": "Impossibile salvare evento",
                "details": str(e)
            }, status_code=500)

    @app.get("/api/sessions/{user_id}")
    async def get_session_history(user_id: str):
        """
        Recupera cronologia completa sessione utente per Syd Agent

        Returns:
        - session: Dati sessione corrente (phase, progress, metadata)
        - events: Lista tutti eventi ordinati per timestamp
        - summary: Riassunto statistiche
        """
        try:
            from database.config import get_engine
            from sqlalchemy import text

            engine = get_engine()

            with engine.connect() as conn:
                # Recupera sessione corrente (più recente)
                result = conn.execute(text("""
                    SELECT session_id, phase, progress, start_time, last_activity, metadata
                    FROM user_sessions
                    WHERE user_id = :user_id
                    ORDER BY last_activity DESC
                    LIMIT 1
                """), {"user_id": user_id})

                session_row = result.fetchone()

                if not session_row:
                    return JSONResponse({
                        "success": False,
                        "error": "session_not_found",
                        "message": f"Nessuna sessione trovata per user {user_id}"
                    }, status_code=404)

                session = {
                    "session_id": str(session_row[0]),
                    "phase": session_row[1],
                    "progress": session_row[2],
                    "start_time": session_row[3].isoformat() if session_row[3] else None,
                    "last_activity": session_row[4].isoformat() if session_row[4] else None,
                    "metadata": session_row[5] if session_row[5] else {}
                }

                # Recupera tutti eventi della sessione
                result = conn.execute(text("""
                    SELECT event_type, event_data, timestamp
                    FROM session_events
                    WHERE session_id = :session_id
                    ORDER BY timestamp ASC
                """), {"session_id": session["session_id"]})

                events = []
                event_counts = {}

                for row in result:
                    event = {
                        "event_type": row[0],
                        "event_data": row[1],
                        "timestamp": row[2].isoformat() if row[2] else None
                    }
                    events.append(event)

                    # Conta eventi per tipo
                    event_counts[row[0]] = event_counts.get(row[0], 0) + 1

                return JSONResponse({
                    "success": True,
                    "user_id": user_id,
                    "session": session,
                    "events": events,
                    "summary": {
                        "total_events": len(events),
                        "event_counts": event_counts,
                        "first_event": events[0]["timestamp"] if events else None,
                        "last_event": events[-1]["timestamp"] if events else None
                    }
                })

        except Exception as e:
            logger.error(f"Errore recupero sessione: {str(e)}", exc_info=True)
            return JSONResponse({
                "success": False,
                "error": "fetch_failed",
                "message": "Impossibile recuperare cronologia",
                "details": str(e)
            }, status_code=500)

    @app.get("/api/sessions/{user_id}/summary")
    async def get_session_summary(user_id: str, limit: int = Query(default=10, description="Numero ultimi eventi")):
        """
        Riassunto ottimizzato sessione per ridurre costi Gemini API

        Returns:
        - Ultimi N eventi (dettaglio completo)
        - Statistiche aggregate eventi precedenti
        - Conteggi per tipo

        Questo endpoint è ottimizzato per context Syd Agent:
        invece di passare 1000+ eventi (50K tokens), passa solo
        ultimi 10 + summary (2.7K tokens) = 90% risparmio
        """
        try:
            from database.config import get_engine
            from sqlalchemy import text

            engine = get_engine()

            with engine.connect() as conn:
                # Recupera sessione corrente
                result = conn.execute(text("""
                    SELECT session_id, phase, progress, start_time, last_activity
                    FROM user_sessions
                    WHERE user_id = :user_id
                    ORDER BY last_activity DESC
                    LIMIT 1
                """), {"user_id": user_id})

                session_row = result.fetchone()

                if not session_row:
                    return JSONResponse({
                        "success": False,
                        "error": "session_not_found",
                        "message": f"Nessuna sessione trovata per user {user_id}"
                    }, status_code=404)

                session_id = str(session_row[0])

                # Conta totale eventi
                result = conn.execute(text("""
                    SELECT COUNT(*), MIN(timestamp), MAX(timestamp)
                    FROM session_events
                    WHERE session_id = :session_id
                """), {"session_id": session_id})

                count_row = result.fetchone()
                total_events = count_row[0]

                # Recupera ultimi N eventi (dettaglio)
                result = conn.execute(text("""
                    SELECT event_type, event_data, timestamp
                    FROM session_events
                    WHERE session_id = :session_id
                    ORDER BY timestamp DESC
                    LIMIT :limit
                """), {"session_id": session_id, "limit": limit})

                recent_events = []
                for row in result:
                    recent_events.append({
                        "event_type": row[0],
                        "event_data": row[1],
                        "timestamp": row[2].isoformat() if row[2] else None
                    })

                # Inverte ordine (più vecchio → più recente)
                recent_events.reverse()

                # Conta eventi per tipo (tutti)
                result = conn.execute(text("""
                    SELECT event_type, COUNT(*) as count
                    FROM session_events
                    WHERE session_id = :session_id
                    GROUP BY event_type
                    ORDER BY count DESC
                """), {"session_id": session_id})

                event_counts = {}
                for row in result:
                    event_counts[row[0]] = row[1]

                return JSONResponse({
                    "success": True,
                    "user_id": user_id,
                    "session": {
                        "session_id": session_id,
                        "phase": session_row[1],
                        "progress": session_row[2]
                    },
                    "recent_events": recent_events,
                    "summary": {
                        "total_events": total_events,
                        "recent_count": len(recent_events),
                        "older_count": total_events - len(recent_events),
                        "event_counts": event_counts,
                        "first_event": count_row[1].isoformat() if count_row[1] else None,
                        "last_event": count_row[2].isoformat() if count_row[2] else None
                    },
                    "optimization": {
                        "mode": "summary",
                        "tokens_saved": f"~{int((total_events - limit) * 50)} tokens",
                        "note": "Solo ultimi eventi + statistiche aggregate"
                    }
                })

        except Exception as e:
            logger.error(f"Errore recupero summary: {str(e)}", exc_info=True)
            return JSONResponse({
                "success": False,
                "error": "fetch_failed",
                "message": "Impossibile recuperare summary",
                "details": str(e)
            }, status_code=500)

    # ENDPOINT - Send Pre-Report PDF via Telegram
    @app.post("/api/send-prereport-pdf")
    async def send_prereport_pdf(request: dict = Body(...)):
        """
        Genera PDF dal pre-report ATECO e lo invia via Telegram

        Request body:
        {
            "atecoData": {...},  // Dati completi del report ATECO
            "telegramChatId": "5123398987"
        }
        """
        try:
            from datetime import datetime
            from io import BytesIO
            from reportlab.lib.pagesizes import A4
            from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
            from reportlab.lib.units import cm
            from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak
            from reportlab.lib.colors import HexColor
            from telegram import Bot

            ateco_data = request.get("atecoData")
            chat_id = request.get("telegramChatId")

            if not ateco_data or not chat_id:
                return JSONResponse({
                    "success": False,
                    "error": "missing_data",
                    "message": "atecoData e telegramChatId sono richiesti"
                }, status_code=400)

            lookup = ateco_data.get("lookup", {})
            arricchimento = ateco_data.get("arricchimento", "")
            normative = ateco_data.get("normative", [])
            certificazioni = ateco_data.get("certificazioni", [])
            rischi = ateco_data.get("rischi", {})

            # Step 1: Genera PDF con ReportLab
            pdf_buffer = BytesIO()
            doc = SimpleDocTemplate(pdf_buffer, pagesize=A4, topMargin=2*cm, bottomMargin=2*cm)

            # Stili
            styles = getSampleStyleSheet()
            title_style = ParagraphStyle('CustomTitle', parent=styles['Heading1'],
                                        textColor=HexColor('#0EA5E9'), fontSize=20, spaceAfter=12)
            heading_style = ParagraphStyle('CustomHeading', parent=styles['Heading2'],
                                          textColor=HexColor('#0284C7'), fontSize=14, spaceAfter=10)
            normal_style = styles['Normal']

            story = []

            # Titolo
            story.append(Paragraph("📊 PRE-REPORT ANALISI ATECO", title_style))
            story.append(Paragraph(f"<i>Generato da SYD CYBER il {datetime.now().strftime('%d/%m/%Y alle %H:%M')}</i>", normal_style))
            story.append(Spacer(1, 0.5*cm))

            # Lookup
            story.append(Paragraph("🔎 Lookup Diretto", heading_style))
            story.append(Paragraph(f"<b>Codice ATECO 2022:</b> {lookup.get('codice2022', 'N/A')}", normal_style))
            story.append(Paragraph(f"<b>Titolo 2022:</b> {lookup.get('titolo2022', 'N/A')}", normal_style))
            story.append(Paragraph(f"<b>Codice ATECO 2025:</b> {lookup.get('codice2025', 'N/A')}", normal_style))
            story.append(Paragraph(f"<b>Titolo 2025:</b> {lookup.get('titolo2025', 'N/A')}", normal_style))
            story.append(Spacer(1, 0.5*cm))

            # Arricchimento
            story.append(Paragraph("📌 Arricchimento Consulenziale", heading_style))
            story.append(Paragraph(arricchimento, normal_style))
            story.append(Spacer(1, 0.5*cm))

            # Normative
            story.append(Paragraph("📜 Normative UE e Nazionali Rilevanti", heading_style))
            for norm in normative:
                story.append(Paragraph(f"• {norm}", normal_style))
            story.append(Spacer(1, 0.5*cm))

            # Certificazioni
            story.append(Paragraph("📑 Certificazioni ISO / Schemi Tipici del Settore", heading_style))
            for cert in certificazioni:
                story.append(Paragraph(f"• {cert}", normal_style))
            story.append(Spacer(1, 0.5*cm))

            # Rischi
            story.append(Paragraph("⚠️ Rischi Principali da Gestire", heading_style))

            story.append(Paragraph("<b>Rischi Operativi</b>", normal_style))
            for risk in rischi.get('operativi', []):
                story.append(Paragraph(f"› {risk}", normal_style))
            story.append(Spacer(1, 0.3*cm))

            story.append(Paragraph("<b>Rischi di Compliance</b>", normal_style))
            for risk in rischi.get('compliance', []):
                story.append(Paragraph(f"› {risk}", normal_style))
            story.append(Spacer(1, 0.3*cm))

            story.append(Paragraph("<b>Rischi Cyber / OT</b>", normal_style))
            for risk in rischi.get('cyber', []):
                story.append(Paragraph(f"› {risk}", normal_style))
            story.append(Spacer(1, 0.3*cm))

            story.append(Paragraph("<b>Rischi Reputazionali</b>", normal_style))
            for risk in rischi.get('reputazionali', []):
                story.append(Paragraph(f"› {risk}", normal_style))
            story.append(Spacer(1, 0.5*cm))

            # Footer
            story.append(Spacer(1, 1*cm))
            story.append(Paragraph("<b>SYD CYBER</b> - Sistema di Valutazione Dinamica dei Rischi Operativi", normal_style))
            story.append(Paragraph("<i>Questo è un pre-report preliminare. Per l'analisi completa contattare il consulente.</i>", normal_style))

            # Build PDF
            doc.build(story)
            pdf_buffer.seek(0)

            # Step 2: Invia via Telegram
            TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "8487460592:AAEPO3TCVVVVe4s7yHRiQNt-NY0Y5yQB3Xk")
            bot = Bot(token=TELEGRAM_BOT_TOKEN)

            ateco_code = lookup.get('codice2025') or lookup.get('codice2022', 'UNKNOWN')
            filename = f"PreReport_ATECO_{ateco_code}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"

            await bot.send_document(
                chat_id=chat_id,
                document=pdf_buffer,
                filename=filename,
                caption=f"📊 Pre-Report ATECO {ateco_code}\n\nGenerato da SYD CYBER il {datetime.now().strftime('%d/%m/%Y alle %H:%M')}"
            )

            logger.info(f"✅ PDF inviato con successo a chat_id {chat_id}: {filename}")

            return JSONResponse({
                "success": True,
                "message": "Report inviato con successo su Telegram",
                "filename": filename,
                "chat_id": chat_id
            })

        except Exception as e:
            logger.error(f"❌ Errore send_prereport_pdf: {str(e)}", exc_info=True)
            return JSONResponse({
                "success": False,
                "error": "send_failed",
                "message": "Errore durante generazione o invio del report",
                "details": str(e)
            }, status_code=500)

    # ENDPOINT - Send Risk Assessment Report PDF via Telegram
    @app.post("/api/send-risk-report-pdf")
    async def send_risk_report_pdf(request: dict = Body(...)):
        """
        Genera PDF dal risk assessment report e lo invia via Telegram

        Request body:
        {
            "riskData": {
                "eventCode": "107",
                "category": "Damage_Danni",
                "inherentRisk": "High",
                "control": "Partially Adequate",
                "economicImpact": "...",
                "nonEconomicImpact": "...",
                "explanation": "...",
                "requiredAction": "...",
                "matrixPosition": "C2",
                "riskScore": 75
            },
            "telegramChatId": "5123398987"
        }
        """
        try:
            from datetime import datetime
            from io import BytesIO
            from reportlab.lib.pagesizes import A4
            from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
            from reportlab.lib.units import cm
            from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak
            from reportlab.lib.colors import HexColor
            from telegram import Bot
            import html

            risk_data = request.get("riskData")
            chat_id = request.get("telegramChatId")

            if not risk_data or not chat_id:
                return JSONResponse({
                    "success": False,
                    "error": "missing_data",
                    "message": "riskData e telegramChatId sono richiesti"
                }, status_code=400)

            # Estrai dati
            event_code = risk_data.get("eventCode", "N/A")
            category = risk_data.get("category", "N/A")
            inherent_risk = risk_data.get("inherentRisk", "N/A")
            control = risk_data.get("control", "N/A")
            economic_impact = risk_data.get("economicImpact", "N/A")
            non_economic_impact = risk_data.get("nonEconomicImpact", "N/A")
            explanation = risk_data.get("explanation", "N/A")
            required_action = risk_data.get("requiredAction", "N/A")
            matrix_position = risk_data.get("matrixPosition", "N/A")
            risk_score = risk_data.get("riskScore", 0)

            # Pulisci HTML dall'explanation
            if explanation and explanation != "N/A":
                explanation = html.unescape(explanation)
                explanation = explanation.replace('<br/>', '\n').replace('<strong>', '').replace('</strong>', '')
                explanation = explanation.replace('<div class="h-3"></div>', '\n')

            # Step 1: Genera PDF con ReportLab
            pdf_buffer = BytesIO()
            doc = SimpleDocTemplate(pdf_buffer, pagesize=A4, topMargin=2*cm, bottomMargin=2*cm)

            # Stili
            styles = getSampleStyleSheet()
            title_style = ParagraphStyle('CustomTitle', parent=styles['Heading1'],
                                        textColor=HexColor('#60A5FA'), fontSize=22, spaceAfter=12, alignment=1)
            heading_style = ParagraphStyle('CustomHeading', parent=styles['Heading2'],
                                          textColor=HexColor('#3B82F6'), fontSize=16, spaceAfter=10)
            subheading_style = ParagraphStyle('CustomSubheading', parent=styles['Heading3'],
                                             textColor=HexColor('#93C5FD'), fontSize=12, spaceAfter=8)
            normal_style = styles['Normal']

            # Colori risk
            risk_colors = {
                'Critical': '#EF4444',
                'High': '#F97316',
                'Medium': '#F59E0B',
                'Low': '#10B981'
            }
            risk_color = risk_colors.get(inherent_risk, '#F59E0B')

            story = []

            # Titolo
            story.append(Paragraph("📊 RISK ASSESSMENT REPORT", title_style))
            story.append(Paragraph(f"<i>Generato da SYD CYBER il {datetime.now().strftime('%d/%m/%Y alle %H:%M')}</i>",
                                 ParagraphStyle('Centered', parent=normal_style, alignment=1)))
            story.append(Spacer(1, 1*cm))

            # Evento
            story.append(Paragraph("🎯 EVENTO", heading_style))
            story.append(Paragraph(f"<b>Codice:</b> {event_code}", normal_style))
            story.append(Paragraph(f"<b>Categoria:</b> {category}", normal_style))
            story.append(Spacer(1, 0.5*cm))

            # Dati principali
            story.append(Paragraph("📊 VALUTAZIONE RISCHIO", heading_style))
            risk_style = ParagraphStyle('RiskLevel', parent=normal_style,
                                       textColor=HexColor(risk_color), fontSize=14, fontName='Helvetica-Bold')
            story.append(Paragraph(f"<b>Rischio Inerente:</b> <font color='{risk_color}'>{inherent_risk}</font>", normal_style))
            story.append(Paragraph(f"<b>Livello Controlli:</b> {control}", normal_style))
            story.append(Paragraph(f"<b>Posizione Matrice:</b> {matrix_position}", normal_style))
            story.append(Paragraph(f"<b>Risk Score:</b> {risk_score}/100", normal_style))
            story.append(Spacer(1, 0.5*cm))

            # Impatti
            story.append(Paragraph("💰 IMPATTO ECONOMICO", heading_style))
            story.append(Paragraph(economic_impact, normal_style))
            story.append(Spacer(1, 0.3*cm))

            story.append(Paragraph("📊 IMPATTO NON ECONOMICO", heading_style))
            story.append(Paragraph(non_economic_impact, normal_style))
            story.append(Spacer(1, 0.5*cm))

            # Spiegazione
            story.append(Paragraph("💡 PERCHÉ QUESTO RISULTATO", heading_style))
            # Dividi explanation in paragrafi per gestire testi lunghi
            explanation_paras = explanation.split('\n\n') if explanation != "N/A" else ["N/A"]
            for para in explanation_paras:
                if para.strip():
                    story.append(Paragraph(para.strip(), normal_style))
                    story.append(Spacer(1, 0.2*cm))
            story.append(Spacer(1, 0.5*cm))

            # Azione consigliata
            story.append(Paragraph("⚡ AZIONE CONSIGLIATA", heading_style))
            story.append(Paragraph(required_action, normal_style))
            story.append(Spacer(1, 1*cm))

            # Footer
            story.append(Spacer(1, 1*cm))
            story.append(Paragraph("<b>SYD CYBER</b> - Sistema di Valutazione Dinamica dei Rischi Operativi",
                                 ParagraphStyle('Footer', parent=normal_style, alignment=1)))
            story.append(Paragraph("<i>Report professionale di Risk Assessment</i>",
                                 ParagraphStyle('FooterItalic', parent=normal_style, alignment=1)))

            # Build PDF
            doc.build(story)
            pdf_buffer.seek(0)

            # Step 2: Invia via Telegram
            TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "8487460592:AAEPO3TCVVVVe4s7yHRiQNt-NY0Y5yQB3Xk")
            bot = Bot(token=TELEGRAM_BOT_TOKEN)

            event_code_clean = event_code.replace('/', '_').replace(' ', '_')
            filename = f"RiskReport_{event_code_clean}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"

            await bot.send_document(
                chat_id=chat_id,
                document=pdf_buffer,
                filename=filename,
                caption=f"📊 Risk Assessment Report - Evento {event_code}\n\nValutazione professionale completata\nRisk Score: {risk_score}/100\nPosizione Matrice: {matrix_position}\n\nGenerato da SYD CYBER il {datetime.now().strftime('%d/%m/%Y alle %H:%M')}"
            )

            logger.info(f"✅ Risk Report PDF inviato con successo a chat_id {chat_id}: {filename}")

            return JSONResponse({
                "success": True,
                "message": "Report inviato con successo su Telegram",
                "filename": filename,
                "chat_id": chat_id
            })

        except Exception as e:
            logger.error(f"❌ Errore send_risk_report_pdf: {str(e)}", exc_info=True)
            return JSONResponse({
                "success": False,
                "error": "send_failed",
                "message": "Errore durante generazione o invio del report",
                "details": str(e)
            }, status_code=500)

    # ============================================================================
    # ENDPOINT ADMIN - Create User Feedback Table
    # ============================================================================
    @app.post("/admin/create-feedback-table")
    async def create_feedback_table():
        """
        Crea tabella user_feedback nel database PostgreSQL

        SICUREZZA:
        - Questo endpoint è protetto (solo chiamata admin una tantum)
        - Usa IF NOT EXISTS per evitare errori se già esiste

        CHIAMATA UNA VOLTA SOLA:
        POST https://celerya-cyber-ateco-production.up.railway.app/admin/create-feedback-table
        """
        logger.info("🚀 ADMIN: Richiesta creazione tabella user_feedback")
        results = {"steps": []}

        try:
            from database.config import get_engine
            from sqlalchemy import text

            engine = get_engine()

            # SQL per creare la tabella (con IF NOT EXISTS per sicurezza)
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
                    # Esegui creazione tabella
                    conn.execute(text(sql_create_table))
                    trans.commit()
                    results["steps"].append("✅ Tabella user_feedback creata")
                    logger.info("✅ Tabella user_feedback creata con successo")

                    # Verifica tabella
                    result = conn.execute(text("""
                        SELECT column_name, data_type
                        FROM information_schema.columns
                        WHERE table_name = 'user_feedback'
                        ORDER BY ordinal_position;
                    """))
                    columns = result.fetchall()
                    results["steps"].append(f"✅ Trovate {len(columns)} colonne")

                    # Verifica indici
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

            return JSONResponse({
                "success": True,
                "message": "Tabella user_feedback creata con successo",
                "steps": results["steps"]
            })

        except Exception as e:
            logger.error(f"❌ Errore creazione tabella user_feedback: {str(e)}", exc_info=True)
            return JSONResponse({
                "success": False,
                "error": "table_creation_failed",
                "message": "Errore durante creazione tabella",
                "details": str(e),
                "steps": results.get("steps", [])
            }, status_code=500)

    # ============================================================================
    # ENDPOINT API - Submit User Feedback
    # ============================================================================
    @app.post("/api/feedback")
    async def submit_feedback(request: dict = Body(...)):
        """
        Riceve feedback utente e invia notifica Telegram

        Request body:
        {
            "sessionId": "uuid-session",
            "userId": "firebase-uid" (optional),
            "userEmail": "user@example.com" (optional),
            "impressionUI": 1-5,
            "impressionUtility": 1-5,
            "easeOfUse": 1-4,
            "innovation": 1-4,
            "sydHelpfulness": 1-4,
            "assessmentClarity": 1-4,
            "likedMost": "text",
            "improvements": "text"
        }
        """
        logger.info("📝 Ricezione feedback utente")

        try:
            from database.config import get_engine
            from sqlalchemy import text

            # Estrai dati dalla request
            session_id = request.get("sessionId")
            user_id = request.get("userId")
            user_email = request.get("userEmail")

            impression_ui = request.get("impressionUI")
            impression_utility = request.get("impressionUtility")
            ease_of_use = request.get("easeOfUse")
            innovation = request.get("innovation")
            syd_helpfulness = request.get("sydHelpfulness")
            assessment_clarity = request.get("assessmentClarity")

            liked_most = request.get("likedMost", "")
            improvements = request.get("improvements", "")

            if not session_id:
                return JSONResponse({
                    "success": False,
                    "error": "missing_session_id"
                }, status_code=400)

            # Salva nel database
            engine = get_engine()
            feedback_id = None

            try:
                with engine.connect() as conn:
                    trans = conn.begin()
                    try:
                        result = conn.execute(text("""
                            INSERT INTO user_feedback (
                                session_id, user_id, user_email,
                                impression_ui, impression_utility,
                                ease_of_use, innovation,
                                syd_helpfulness, assessment_clarity,
                                liked_most, improvements
                            )
                            VALUES (
                                :session_id, :user_id, :user_email,
                                :impression_ui, :impression_utility,
                                :ease_of_use, :innovation,
                                :syd_helpfulness, :assessment_clarity,
                                :liked_most, :improvements
                            )
                            RETURNING id;
                        """), {
                            "session_id": session_id,
                            "user_id": user_id,
                            "user_email": user_email,
                            "impression_ui": impression_ui,
                            "impression_utility": impression_utility,
                            "ease_of_use": ease_of_use,
                            "innovation": innovation,
                            "syd_helpfulness": syd_helpfulness,
                            "assessment_clarity": assessment_clarity,
                            "liked_most": liked_most,
                            "improvements": improvements
                        })

                        feedback_id = result.scalar()
                        trans.commit()

                        logger.info(f"✅ Feedback salvato nel database (ID: {feedback_id})")

                    except Exception as db_error:
                        trans.rollback()
                        logger.error(f"❌ Errore salvataggio database: {str(db_error)}")

                        # Gestisci errore di duplicato session_id
                        if "user_feedback_session_unique" in str(db_error) or "duplicate key" in str(db_error).lower():
                            return JSONResponse({
                                "success": False,
                                "error": "already_submitted",
                                "message": "Hai già inviato feedback per questa sessione. Grazie!"
                            }, status_code=409)

                        raise db_error

            except Exception as conn_error:
                # Gestisci QUALSIASI errore DB (PostgreSQL su Railway, non disponibile in locale)
                # NON bloccare - Telegram è prioritario
                logger.warning(f"⚠️ DB non disponibile in locale (Railway): {type(conn_error).__name__}")
                logger.warning(f"⚠️ Dettaglio: {str(conn_error)[:100]}")
                logger.warning("⚠️ Continuo con invio Telegram (priorità)")
                feedback_id = None  # Non salvato in DB, ma invieremo Telegram

            # Invia notifica Telegram
            try:
                from telegram import Bot
                from datetime import datetime

                logger.info("🔄 Tentativo invio Telegram feedback...")

                TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "8487460592:AAEPO3TCVVVVe4s7yHRiQNt-NY0Y5yQB3Xk")
                TELEGRAM_CHAT_ID = "5123398987"  # Team chat

                logger.info(f"Token presente: {TELEGRAM_BOT_TOKEN[:20]}...")

                # Converti scale in emoji e testo
                # Scala: 5 = molto positivo (5 stelle), 1 = molto negativo (1 stella)
                def rating_emoji(value, max_val=5):
                    if value is None:
                        return "N/A"
                    stars = "⭐" * value
                    return f"{stars} ({value}/{max_val})"

                message = f"""🎯 NUOVO FEEDBACK UTENTE

👤 Utente:
- Session: {session_id[:8]}...
- Email: {user_email or 'N/A'}

📊 Valutazioni:
- UI: {rating_emoji(impression_ui, 5)}
- Utilità: {rating_emoji(impression_utility, 5)}
- Facilità d'uso: {rating_emoji(ease_of_use, 4)}
- Innovazione: {rating_emoji(innovation, 4)}
- Syd Agent: {rating_emoji(syd_helpfulness, 4)}
- Chiarezza: {rating_emoji(assessment_clarity, 4)}

💬 Feedback aperto:
✅ Piaciuto: {liked_most[:200] if liked_most else 'N/A'}
🔧 Migliorare: {improvements[:200] if improvements else 'N/A'}

🕒 {datetime.now().strftime('%d/%m/%Y %H:%M')}"""

                bot = Bot(token=TELEGRAM_BOT_TOKEN)
                await bot.send_message(
                    chat_id=TELEGRAM_CHAT_ID,
                    text=message
                )

                logger.info(f"✅ Notifica Telegram inviata per feedback {f'ID {feedback_id}' if feedback_id else '(no DB)'}")

            except Exception as telegram_error:
                # Non bloccare se Telegram fallisce
                logger.warning(f"⚠️ Telegram notification failed: {str(telegram_error)}")

            return JSONResponse({
                "success": True,
                "message": "Feedback ricevuto con successo",
                "feedbackId": feedback_id if feedback_id else "not_saved_locally"
            })

        except Exception as e:
            logger.error(f"❌ Errore submit_feedback: {str(e)}", exc_info=True)
            return JSONResponse({
                "success": False,
                "error": "submission_failed",
                "message": "Errore durante invio feedback",
                "details": str(e)
            }, status_code=500)

    # ==================== MODULAR ROUTERS (Stories 2.3, 2.4, 2.5 & 2.6 - Refactoring) ====================
    # Register new modular routers - endpoints remain compatible with old ones
    # Registered at the end to avoid import/scope issues
    from app.routers import risk as risk_router
    from app.routers import visura as visura_router
    from app.routers import db_admin as db_admin_router
    from app.routers import seismic as seismic_router

    app.include_router(risk_router.router)

    # Setup Visura router dependencies (DataFrame and utility functions)
    visura_router.set_dependencies(
        ateco_df=df,
        search_smart_fn=search_smart,
        normalize_code_fn=normalize_code
    )
    app.include_router(visura_router.router)

    # Setup DB Admin router dependencies (DataFrame)
    db_admin_router.set_dependencies(ateco_df=df)
    app.include_router(db_admin_router.router)

    # Story 2.6: Seismic Zones router (no external dependencies)
    app.include_router(seismic_router.router)

    logger.info("✅ Modular routers registered: /risk/*, /visura/*, /db-admin/*, /seismic/*")
    # ===================================================================================

    return app


def main():
    ap = argparse.ArgumentParser(description="ATECO lookup offline / API")
    ap.add_argument("--file", required=True, type=Path, help="percorso Excel (xlsx)")
    ap.add_argument("--code", help="codice ATECO da cercare")
    ap.add_argument("--prefer", choices=["2022", "2025", "2025-camerale"], help="priorità colonna")
    ap.add_argument("--prefix", action="store_true", help="ricerca per prefisso")
    ap.add_argument("--limit", type=int, default=50, help="limite per risultati multipli")
    ap.add_argument("--debug", action="store_true")
    ap.add_argument("--serve", action="store_true", help="avvia API FastAPI")
    ap.add_argument("--host", default="127.0.0.1")
    ap.add_argument("--port", type=int, default=8000)
    ap.add_argument("--pretty", action="store_true", help="Stampa 1 riga: codice — descrizione")
    args = ap.parse_args()

    if args.serve:
        df = load_dataset(args.file, debug=args.debug)
        app = build_api(df)
        try:
            import uvicorn
        except ImportError:
            raise SystemExit("Per --serve installa: pip install fastapi uvicorn")
        uvicorn.run(app, host=args.host, port=args.port)
        return

    if not args.code:
        ap.error("--code è obbligatorio in modalità CLI (senza --serve)")

    run_cli(args)

# CREA APP PER RAILWAY (deve essere globale per uvicorn main:app)
excel_file = Path("tabella_ATECO.xlsx")
if not excel_file.exists():
    # Prova altri nomi possibili
    for possible in ["ateco_2025_mapping.xlsx", "ATECO.xlsx", "ateco.xlsx"]:
        if Path(possible).exists():
            excel_file = Path(possible)
            break

print(f"Caricamento {excel_file}...")
df = load_dataset(excel_file, debug=False)
app = build_api(df)

if __name__ == "__main__":
    # Se eseguito direttamente, usa main()
    main()
