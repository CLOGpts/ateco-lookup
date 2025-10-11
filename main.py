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
    
    class BatchRequest(BaseModel):
        codes: List[str]
        prefer: Optional[str] = None
        prefix: bool = False

    app = FastAPI(title="ATECO Lookup", version="2.0")

    # Abilita CORS con configurazione più permissiva per debug
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # in produzione meglio specificare solo il dominio della UI
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=["*"],  # Esponi tutti gli header
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

    @app.get("/lookup")
    def lookup(code: str = Query(..., description="Codice ATECO"),
               prefer: Optional[str] = Query(None, description="priorità: 2022 | 2025 | 2025-camerale"),
               prefix: bool = Query(False, description="ricerca per prefisso"),
               limit: int = Query(50)):
        logger.info(f"Lookup requested for code: {code}, prefer: {prefer}, prefix: {prefix}")
        
        # Validazione input
        if not code or len(code) < 2:
            logger.warning(f"Invalid code provided: {code}")
            raise HTTPException(
                status_code=400,
                detail={
                    "error": "INVALID_CODE",
                    "message": "Codice troppo corto (minimo 2 caratteri)"
                }
            )
        
        res = search_smart(df, code, prefer=prefer, prefix=prefix)
        
        if res.empty:
            logger.info(f"No results found for code: {code}")
            # Suggerisci alternative
            suggestions = find_similar_codes(df, code)
            return JSONResponse({
                "found": 0,
                "items": [],
                "suggestions": suggestions,
                "message": f"Nessun risultato per '{code}'. Prova con uno dei suggerimenti."
            })
        
        if prefix:
            res = res.head(limit)
        items = [enrich(flatten(r)) for _, r in res.iterrows()]
        logger.info(f"Found {len(items)} results for code: {code}")
        return JSONResponse({"found": len(items), "items": items})
    
    @app.post("/batch")
    def batch_lookup(request: BatchRequest):
        """Endpoint per lookup multipli in una singola richiesta."""
        logger.info(f"Batch lookup requested for {len(request.codes)} codes")
        
        if len(request.codes) > 50:
            raise HTTPException(
                status_code=400,
                detail={
                    "error": "TOO_MANY_CODES",
                    "message": "Massimo 50 codici per richiesta batch"
                }
            )
        
        results = []
        for code in request.codes:
            res = search_smart(df, code, prefer=request.prefer, prefix=request.prefix)
            if res.empty:
                results.append({
                    "code": code,
                    "found": 0,
                    "items": []
                })
            else:
                items = [enrich(flatten(r)) for _, r in res.head(1).iterrows()]
                results.append({
                    "code": code,
                    "found": len(items),
                    "items": items
                })
        
        return JSONResponse({
            "total_codes": len(request.codes),
            "results": results
        })
    
    @app.get("/autocomplete")
    def autocomplete(partial: str = Query(..., min_length=2, description="Codice parziale"),
                     limit: int = Query(5, le=20, description="Numero suggerimenti")):
        """Endpoint per suggerimenti autocomplete durante la digitazione."""
        logger.info(f"Autocomplete requested for: {partial}")
        
        partial_norm = normalize_code(partial)
        suggestions = []
        seen = set()
        
        # Cerca nei codici 2022
        for _, row in df.iterrows():
            code = normalize_code(row.get("CODICE_ATECO_2022", ""))
            if code and code.startswith(partial_norm) and code not in seen:
                seen.add(code)
                suggestions.append({
                    "code": row.get("CODICE_ATECO_2022", ""),
                    "title": row.get("TITOLO_ATECO_2022", ""),
                    "version": "2022"
                })
                if len(suggestions) >= limit:
                    break
        
        # Se non abbastanza risultati, cerca anche nei codici 2025
        if len(suggestions) < limit:
            for _, row in df.iterrows():
                code = normalize_code(row.get("CODICE_ATECO_2025_RAPPRESENTATIVO", ""))
                if code and code.startswith(partial_norm) and code not in seen:
                    seen.add(code)
                    suggestions.append({
                        "code": row.get("CODICE_ATECO_2025_RAPPRESENTATIVO", ""),
                        "title": row.get("TITOLO_ATECO_2025_RAPPRESENTATIVO", ""),
                        "version": "2025"
                    })
                    if len(suggestions) >= limit:
                        break
        
        return JSONResponse({
            "partial": partial,
            "suggestions": suggestions[:limit],
            "count": len(suggestions[:limit])
        })
    
    # ENDPOINT RISK MANAGEMENT - CON LOGICA EXCEL REALE
    # Carica i dati Excel corretti
    try:
        with open('MAPPATURE_EXCEL_PERFETTE.json', 'r', encoding='utf-8') as f:
            risk_data = json.load(f)
            EXCEL_CATEGORIES = risk_data['mappature_categoria_eventi']
            EXCEL_DESCRIPTIONS = risk_data['vlookup_map']
    except:
        # Fallback se il file non esiste
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
    
    @app.get("/events/{category}")
    def get_events(category: str):
        """Endpoint per ottenere eventi di rischio per categoria - LOGICA EXCEL REALE"""
        # Mappa alias comuni alle categorie Excel reali
        category_mapping = {
            "operational": "Execution_delivery_Problemi_di_produzione_o_consegna",
            "cyber": "Business_disruption",
            "compliance": "Clients_product_Clienti",
            "financial": "Internal_Fraud_Frodi_interne",
            "damage": "Damage_Danni",
            "employment": "Employment_practices_Dipendenti",
            "external_fraud": "External_fraud_Frodi_esterne"
        }
        
        # Usa categoria Excel reale se esiste, altrimenti prova mapping
        real_category = category
        if category in EXCEL_CATEGORIES:
            real_category = category
        elif category.lower() in category_mapping:
            real_category = category_mapping[category.lower()]
        elif category not in EXCEL_CATEGORIES:
            # Prova a trovare categoria simile
            for cat in EXCEL_CATEGORIES:
                if category.lower() in cat.lower():
                    real_category = cat
                    break
        
        if real_category not in EXCEL_CATEGORIES:
            return JSONResponse({
                "error": f"Category '{category}' not found",
                "available_categories": list(EXCEL_CATEGORIES.keys()),
                "category_mapping": category_mapping
            }, status_code=404)
        
        # Converti eventi Excel in formato frontend
        events = []
        for event_str in EXCEL_CATEGORIES[real_category]:
            # Estrai codice e nome dall'evento (formato: "101 - Nome evento")
            parts = event_str.split(' - ', 1)
            if len(parts) == 2:
                code = parts[0].strip()
                name = parts[1].strip()
                # Determina severity basandosi sul codice
                if code.startswith('1'):
                    severity = 'medium'
                elif code.startswith('2'):
                    severity = 'high'
                elif code.startswith('3'):
                    severity = 'low'
                elif code.startswith('4'):
                    severity = 'medium'
                elif code.startswith('5'):
                    severity = 'high'
                elif code.startswith('6') or code.startswith('7'):
                    severity = 'critical'
                else:
                    severity = 'medium'
                
                events.append({
                    "code": code,
                    "name": name,
                    "severity": severity
                })
        
        return JSONResponse({
            "category": real_category,
            "original_request": category,
            "events": events,
            "total": len(events)
        })
    
    @app.get("/description/{event_code}")  
    def get_event_description(event_code: str):
        """Endpoint per ottenere descrizione dettagliata di un evento - DATI EXCEL REALI"""
        # FIX: Gestisce sia codici semplici che oggetti serializzati
        # Se riceve [object Object] o JSON, estrai il codice
        import re
        
        # Pulisci event_code da caratteri strani
        if '[object' in event_code.lower() or '{' in event_code:
            # Frontend ha passato un oggetto invece del codice
            # Prova a estrarre un numero dal parametro
            numbers = re.findall(r'\d+', event_code)
            if numbers:
                event_code = numbers[0]
            else:
                return JSONResponse({
                    "error": "Invalid event code format",
                    "received": event_code,
                    "expected": "Event code like '101', '201', etc.",
                    "hint": "Frontend should pass event.code, not the entire event object"
                }, status_code=400)
        
        # Normalizza il codice (rimuovi spazi, trattini extra)
        event_code = event_code.strip()
        
        # PRIMA cerca l'evento nelle CATEGORIE (priorità massima)
        event_name = None
        event_full_string = None
        category_found = None
        for cat_name, cat_events in EXCEL_CATEGORIES.items():
            for event in cat_events:
                if event.startswith(event_code + ' - '):
                    event_full_string = event
                    event_name = event.split(' - ', 1)[1]
                    category_found = cat_name
                    break
            if event_name:
                break
        
        # POI cerca eventuali descrizioni aggiuntive VLOOKUP
        vlookup_description = EXCEL_DESCRIPTIONS.get(event_code)
        
        # Se l'evento esiste nelle categorie Excel
        if event_name:
            # Usa VLOOKUP se disponibile, altrimenti usa il nome dell'evento
            final_description = vlookup_description if vlookup_description else event_name
            
            # Determina impatto e probabilità basandosi sul codice
            if event_code.startswith('1'):
                impact = "Danni fisici e materiali"
                probability = "low"
            elif event_code.startswith('2'):
                impact = "Interruzione operativa e perdita dati"
                probability = "medium"
            elif event_code.startswith('3'):
                impact = "Problemi con dipendenti e clima aziendale"
                probability = "medium"
            elif event_code.startswith('4'):
                impact = "Errori di processo e consegna"
                probability = "high"
            elif event_code.startswith('5'):
                impact = "Perdita clienti e sanzioni"
                probability = "medium"
            elif event_code.startswith('6'):
                impact = "Frodi interne e perdite finanziarie"
                probability = "low"
            elif event_code.startswith('7'):
                impact = "Frodi esterne e attacchi cyber"
                probability = "medium"
            else:
                impact = "Da valutare caso per caso"
                probability = "unknown"
            
            # Determina controlli basandosi sulla categoria
            if event_code.startswith('1'):
                controls = ["Assicurazione danni", "Manutenzione preventiva", "Procedure di emergenza"]
            elif event_code.startswith('2'):
                controls = ["Backup e recovery", "Ridondanza sistemi", "Monitoring continuo"]
            elif event_code.startswith('3'):
                controls = ["HR policies", "Formazione continua", "Welfare aziendale"]
            elif event_code.startswith('4'):
                controls = ["Quality control", "Process automation", "KPI monitoring"]
            elif event_code.startswith('5'):
                controls = ["Customer satisfaction", "Compliance monitoring", "Legal review"]
            elif event_code.startswith('6'):
                controls = ["Audit interni", "Segregation of duties", "Whistleblowing"]
            elif event_code.startswith('7'):
                controls = ["Cybersecurity", "Fraud detection", "Identity verification"]
            else:
                controls = ["Controlli standard da definire"]
            
            return JSONResponse({
                "code": event_code,
                "name": event_name,
                "description": final_description,
                "category": category_found,
                "impact": impact,
                "probability": probability,
                "controls": controls,
                "source": "Excel Risk Mapping",
                "has_vlookup": vlookup_description is not None
            })
        
        # Se non trovato nell'Excel, ritorna descrizione generica
        return JSONResponse({
            "code": event_code,
            "name": "Evento non mappato",
            "description": f"Evento {event_code} non presente nel mapping Excel",
            "impact": "Da valutare",
            "probability": "unknown",
            "controls": ["Da definire in base all'analisi specifica"],
            "source": "Generic"
        })
    
    # NUOVO ENDPOINT: Fornisce i 5 campi di valutazione Risk Assessment
    @app.get("/risk-assessment-fields")
    def get_risk_assessment_fields():
        """Endpoint per ottenere la struttura dei 5 campi di Perdita Finanziaria Attesa"""
        return {
            "fields": [
                {
                    "id": "impatto_finanziario",
                    "column": "H",
                    "question": "Qual è l'impatto finanziario stimato?",
                    "type": "select",
                    "options": [
                        "N/A",
                        "0 - 1K€",
                        "1 - 10K€",
                        "10 - 50K€",
                        "50 - 100K€",
                        "100 - 500K€",
                        "500K€ - 1M€",
                        "1 - 3M€",
                        "3 - 5M€"
                    ],
                    "required": True
                },
                {
                    "id": "perdita_economica",
                    "column": "I",
                    "question": "Qual è il livello di perdita economica attesa?",
                    "type": "select_color",
                    "options": [
                        {"value": "G", "label": "Bassa/Nulla", "color": "green", "emoji": "🟢"},
                        {"value": "Y", "label": "Media", "color": "yellow", "emoji": "🟡"},
                        {"value": "O", "label": "Importante", "color": "orange", "emoji": "🟠"},
                        {"value": "R", "label": "Grave", "color": "red", "emoji": "🔴"}
                    ],
                    "required": True
                },
                {
                    "id": "impatto_immagine",
                    "column": "J",
                    "question": "L'evento ha impatto sull'immagine aziendale?",
                    "type": "boolean",
                    "options": ["Si", "No"],
                    "required": True
                },
                {
                    "id": "impatto_regolamentare",
                    "column": "L",
                    "question": "Ci sono possibili conseguenze regolamentari o legali civili?",
                    "type": "boolean",
                    "options": ["Si", "No"],
                    "description": "Multe, sanzioni amministrative, cause civili",
                    "required": True
                },
                {
                    "id": "impatto_criminale",
                    "column": "M",
                    "question": "Ci sono possibili conseguenze penali?",
                    "type": "boolean",
                    "options": ["Si", "No"],
                    "description": "Denunce penali, procedimenti criminali",
                    "required": True
                },
                {
                    "id": "perdita_non_economica",
                    "column": "V",
                    "question": "Qual è il livello di perdita non economica non attesa ma accadibile?",
                    "type": "select_color",
                    "options": [
                        {"value": "G", "label": "Bassa/Nulla - Impatto minimo o trascurabile", "color": "green", "emoji": "🟢"},
                        {"value": "Y", "label": "Media - Impatto moderato gestibile", "color": "yellow", "emoji": "🟡"},
                        {"value": "O", "label": "Importante - Impatto significativo che richiede attenzione", "color": "orange", "emoji": "🟠"},
                        {"value": "R", "label": "Grave - Impatto critico che richiede azione immediata", "color": "red", "emoji": "🔴"}
                    ],
                    "required": False
                },
                {
                    "id": "controllo",
                    "column": "W",
                    "question": "Qual è il livello di controllo?",
                    "type": "select",
                    "options": [
                        {"value": "++", "label": "++ Adeguato"},
                        {"value": "+", "label": "+ Sostanzialmente adeguato"},
                        {"value": "-", "label": "- Parzialmente Adeguato"},
                        {"value": "--", "label": "-- Non adeguato / assente"}
                    ],
                    "required": False,
                    "triggers": "descrizione_controllo"
                },
                {
                    "id": "descrizione_controllo",
                    "column": "X",
                    "question": "Descrizione del controllo",
                    "type": "readonly",
                    "autoPopulated": True,
                    "vlookupSource": "W",
                    "vlookupMap": {
                        "++": {
                            "titolo": "Adeguato",
                            "descrizione": "Il sistema di controllo interno è efficace ed adeguato (controlli 1 e 2 sono attivi e consolidati)"
                        },
                        "+": {
                            "titolo": "Sostanzialmente adeguato",
                            "descrizione": "Alcune correzioni potrebbero rendere soddisfacente il sistema di controllo interno (controlli 1 e 2 presenti ma parzialmente strutturati)"
                        },
                        "-": {
                            "titolo": "Parzialmente Adeguato",
                            "descrizione": "Il sistema di controllo interno deve essere migliorato e il processo dovrebbe essere più strettamente controllato (controlli 1 e 2 NON formalizzati)"
                        },
                        "--": {
                            "titolo": "Non adeguato / assente",
                            "descrizione": "Il sistema di controllo interno dei processi deve essere riorganizzato immediatamente (livelli di controllo 1 e 2 NON attivi)"
                        }
                    }
                }
            ]
        }
    
    # NUOVO ENDPOINT: Salva risk assessment e calcola score
    @app.post("/save-risk-assessment")
    def save_risk_assessment(data: dict):
        """Endpoint per salvare la valutazione del rischio e calcolare il risk score"""
        try:
            # Calcola risk score
            score = 0
            
            # Impatto finanziario (max 40 punti)
            impatto_map = {
                'N/A': 0, '0 - 1K€': 5, '1 - 10K€': 10, '10 - 50K€': 15,
                '50 - 100K€': 20, '100 - 500K€': 25, '500K€ - 1M€': 30,
                '1 - 3M€': 35, '3 - 5M€': 40
            }
            score += impatto_map.get(data.get('impatto_finanziario', 'N/A'), 0)
            
            # Perdita economica (max 30 punti)
            perdita_map = {'G': 5, 'Y': 15, 'O': 25, 'R': 30}
            score += perdita_map.get(data.get('perdita_economica', 'G'), 0)
            
            # Impatti booleani (10 punti ciascuno)
            if data.get('impatto_immagine') == 'Si': score += 10
            if data.get('impatto_regolamentare') == 'Si': score += 10
            if data.get('impatto_criminale') == 'Si': score += 10
            
            # Perdita non economica (V) - max 10 punti
            perdita_non_eco_map = {'G': 0, 'Y': 3, 'O': 6, 'R': 10}
            score += perdita_non_eco_map.get(data.get('perdita_non_economica', 'G'), 0)
            
            # Controllo (W) - influenza il moltiplicatore del rischio
            controllo_multiplier = {
                '++': 0.5,   # Riduce il rischio del 50%
                '+': 0.75,   # Riduce il rischio del 25%
                '-': 1.25,   # Aumenta il rischio del 25%
                '--': 1.5    # Aumenta il rischio del 50%
            }
            controllo = data.get('controllo', '+')
            if controllo in controllo_multiplier:
                score = int(score * controllo_multiplier[controllo])
            
            # Genera analisi
            if score >= 70:
                level = "CRITICO"
                action = "Richiede azione immediata"
            elif score >= 50:
                level = "ALTO"
                action = "Priorità alta, pianificare mitigazione"
            elif score >= 30:
                level = "MEDIO"
                action = "Monitorare e valutare opzioni"
            else:
                level = "BASSO"
                action = "Rischio accettabile, monitoraggio standard"
            
            analysis = f"Livello di rischio: {level} (Score: {score}/100). {action}"
            
            # Log dei dati ricevuti
            logging.info(f"Risk Assessment - Evento: {data.get('event_code')} - Score: {score}")
            
            return {
                "status": "success",
                "message": "Risk assessment salvato",
                "risk_score": score,
                "analysis": analysis
            }
            
        except Exception as e:
            logging.error(f"Errore in save_risk_assessment: {e}")
            return JSONResponse({
                "status": "error",
                "message": str(e)
            }, status_code=400)
    
    # NUOVO ENDPOINT: Calcola la matrice di rischio
    @app.post("/calculate-risk-assessment")
    def calculate_risk_assessment(data: dict):
        """Endpoint per calcolare la posizione nella matrice di rischio e il livello di rischio"""
        try:
            # Converti colori in valori numerici (dal sistema Excel)
            color_to_value = {'G': 4, 'Y': 3, 'O': 2, 'R': 1}
            
            # Estrai i valori dai dati ricevuti
            economic_value = color_to_value.get(data.get('economic_loss', 'G'), 4)
            non_economic_value = color_to_value.get(data.get('non_economic_loss', 'G'), 4)
            
            # Calcola rischio inerente (MIN dei due valori come da Excel)
            inherent_risk = min(economic_value, non_economic_value)
            
            # Mappa controllo a riga della matrice
            control_to_row = {
                '--': 1,  # Non adeguato -> riga 1
                '-': 2,   # Parzialmente adeguato -> riga 2
                '+': 3,   # Sostanzialmente adeguato -> riga 3
                '++': 4   # Adeguato -> riga 4
            }
            
            control_level = data.get('control_level', '+')
            row = control_to_row.get(control_level, 3)
            
            # Calcola colonna in base al rischio inerente
            # Rischio 4 (basso) -> colonna A, Rischio 1 (alto) -> colonna D
            column_map = {4: 'A', 3: 'B', 2: 'C', 1: 'D'}
            column = column_map.get(inherent_risk, 'B')
            
            # Posizione nella matrice (es. "A1", "B2", "C3", "D4")
            matrix_position = f"{column}{row}"
            
            # Determina livello di rischio basato sulla posizione
            risk_levels = {
                'A4': {'level': 'Low', 'color': 'green', 'value': 0},
                'A3': {'level': 'Low', 'color': 'green', 'value': 0},
                'B4': {'level': 'Low', 'color': 'green', 'value': 0},
                'A2': {'level': 'Medium', 'color': 'yellow', 'value': 0},
                'B3': {'level': 'Medium', 'color': 'yellow', 'value': 0},
                'C4': {'level': 'Medium', 'color': 'yellow', 'value': 0},
                'A1': {'level': 'High', 'color': 'orange', 'value': 0},
                'B2': {'level': 'High', 'color': 'orange', 'value': 0},
                'C3': {'level': 'High', 'color': 'orange', 'value': 0},
                'D4': {'level': 'High', 'color': 'orange', 'value': 0},
                'B1': {'level': 'Critical', 'color': 'red', 'value': 1},
                'C2': {'level': 'Critical', 'color': 'red', 'value': 1},
                'D3': {'level': 'Critical', 'color': 'red', 'value': 1},
                'C1': {'level': 'Critical', 'color': 'red', 'value': 1},
                'D2': {'level': 'Critical', 'color': 'red', 'value': 1},
                'D1': {'level': 'Critical', 'color': 'red', 'value': 1}
            }
            
            risk_info = risk_levels.get(matrix_position, {'level': 'Medium', 'color': 'yellow', 'value': 0})
            
            # Prepara risposta completa
            response = {
                'status': 'success',
                'matrix_position': matrix_position,
                'risk_level': risk_info['level'],
                'risk_color': risk_info['color'],
                'risk_value': risk_info['value'],
                'inherent_risk': {
                    'value': inherent_risk,
                    'label': {4: 'Low', 3: 'Medium', 2: 'High', 1: 'Critical'}[inherent_risk]
                },
                'control_effectiveness': {
                    'value': row,
                    'label': control_level,
                    'description': {
                        '++': 'Adeguato',
                        '+': 'Sostanzialmente adeguato',
                        '-': 'Parzialmente Adeguato',
                        '--': 'Non adeguato / assente'
                    }.get(control_level, 'Unknown')
                },
                'calculation_details': {
                    'economic_loss': data.get('economic_loss'),
                    'economic_value': economic_value,
                    'non_economic_loss': data.get('non_economic_loss'),
                    'non_economic_value': non_economic_value,
                    'min_value': inherent_risk,
                    'control_level': control_level,
                    'control_row': row,
                    'matrix_column': column
                },
                'recommendations': []
            }
            
            # Aggiungi raccomandazioni basate sul livello di rischio
            if risk_info['level'] == 'Critical':
                response['recommendations'] = [
                    'Azione immediata richiesta',
                    'Implementare controlli aggiuntivi urgentemente',
                    'Escalation al management richiesta'
                ]
            elif risk_info['level'] == 'High':
                response['recommendations'] = [
                    'Priorità alta per mitigazione',
                    'Rafforzare i controlli esistenti',
                    'Monitoraggio frequente richiesto'
                ]
            elif risk_info['level'] == 'Medium':
                response['recommendations'] = [
                    'Monitorare regolarmente',
                    'Valutare opportunità di miglioramento controlli',
                    'Documentare piani di contingenza'
                ]
            else:  # Low
                response['recommendations'] = [
                    'Rischio accettabile',
                    'Mantenere controlli attuali',
                    'Revisione periodica standard'
                ]
            
            # Log per debug
            logger.info(f"Risk calculation: {matrix_position} = {risk_info['level']} (Inherent: {inherent_risk}, Control: {row})")
            
            return JSONResponse(response)
            
        except Exception as e:
            logger.error(f"Errore in calculate_risk_assessment: {str(e)}", exc_info=True)
            return JSONResponse({
                'status': 'error',
                'message': f'Errore nel calcolo del rischio: {str(e)}',
                'error_details': str(e)
            }, status_code=500)
    
    # ENDPOINT ALTERNATIVO PER FRONTEND CHE INVIA OGGETTI
    @app.post("/description")
    def get_event_description_post(event: dict):
        """Endpoint POST per ricevere l'evento come JSON invece che come parametro URL"""
        # Estrai il codice dall'oggetto evento
        event_code = None
        
        # Prova diversi formati possibili
        if isinstance(event, dict):
            event_code = event.get('code') or event.get('event_code') or event.get('id')
        
        if not event_code:
            return JSONResponse({
                "error": "Event code not found in request",
                "received": event,
                "expected_format": {"code": "101"}
            }, status_code=400)
        
        # Usa la stessa logica dell'endpoint GET
        event_code = str(event_code).strip()
        
        # PRIMA cerca l'evento nelle CATEGORIE (come GET)
        event_name_from_excel = None
        category_found = None
        for cat_name, cat_events in EXCEL_CATEGORIES.items():
            for ev in cat_events:
                if ev.startswith(event_code + ' - '):
                    event_name_from_excel = ev.split(' - ', 1)[1]
                    category_found = cat_name
                    break
            if event_name_from_excel:
                break
        
        # Usa il nome dall'oggetto se disponibile, altrimenti quello dall'Excel
        event_name = event.get('name') or event_name_from_excel
        
        # Cerca descrizione VLOOKUP
        vlookup_description = EXCEL_DESCRIPTIONS.get(event_code)
        
        # Se l'evento esiste nell'Excel
        if event_name_from_excel:
            # Usa VLOOKUP se disponibile, altrimenti usa il nome
            final_description = vlookup_description if vlookup_description else event_name_from_excel
            
            # Determina impatto e probabilità
            if event_code.startswith('1'):
                impact = "Danni fisici e materiali"
                probability = "low"
                controls = ["Assicurazione danni", "Manutenzione preventiva", "Procedure di emergenza"]
            elif event_code.startswith('2'):
                impact = "Interruzione operativa e perdita dati"
                probability = "medium"
                controls = ["Backup e recovery", "Ridondanza sistemi", "Monitoring continuo"]
            elif event_code.startswith('3'):
                impact = "Problemi con dipendenti e clima aziendale"
                probability = "medium"
                controls = ["HR policies", "Formazione continua", "Welfare aziendale"]
            elif event_code.startswith('4'):
                impact = "Errori di processo e consegna"
                probability = "high"
                controls = ["Quality control", "Process automation", "KPI monitoring"]
            elif event_code.startswith('5'):
                impact = "Perdita clienti e sanzioni"
                probability = "medium"
                controls = ["Customer satisfaction", "Compliance monitoring", "Legal review"]
            elif event_code.startswith('6'):
                impact = "Frodi interne e perdite finanziarie"
                probability = "low"
                controls = ["Audit interni", "Segregation of duties", "Whistleblowing"]
            elif event_code.startswith('7'):
                impact = "Frodi esterne e attacchi cyber"
                probability = "medium"
                controls = ["Cybersecurity", "Fraud detection", "Identity verification"]
            else:
                impact = "Da valutare caso per caso"
                probability = "unknown"
                controls = ["Controlli standard da definire"]
            
            return JSONResponse({
                "code": event_code,
                "name": event_name,
                "description": final_description,
                "category": category_found,
                "impact": impact,
                "probability": probability,
                "controls": controls,
                "severity": event.get('severity', 'medium'),
                "source": "Excel Risk Mapping",
                "has_vlookup": vlookup_description is not None
            })
        
        # Se non trovato nell'Excel
        return JSONResponse({
            "code": event_code,
            "name": event.get('name', 'Evento non mappato'),
            "description": f"Evento {event_code} non presente nel mapping Excel",
            "impact": "Da valutare",
            "probability": "unknown",
            "controls": ["Da definire in base all'analisi specifica"],
            "source": "Generic"
        })
    
    @app.get("/api/test-visura")
    def test_visura():
        """Endpoint di test per verificare che l'API funzioni"""
        return JSONResponse({
            "success": True,
            "message": "API funzionante! VisuraExtractorPower disponibile: " + str(VisuraExtractorPower is not None),
            "data": {
                "denominazione": "TEST CELERYA SRL",
                "partita_iva": "12345678901",
                "pec": "test@pec.it",
                "codici_ateco": [
                    {"codice": "62.01", "descrizione": "Produzione software", "principale": True}
                ],
                "sede_legale": {
                    "comune": "Torino",
                    "provincia": "TO"
                },
                "confidence": 0.99
            }
        })
    
    @app.post("/api/extract-visura")
    async def extract_visura(file: UploadFile = File(...)):
        """
        Estrae SOLO 3 campi STRICT da visura PDF
        
        Returns:
            JSON con P.IVA, ATECO, Oggetto Sociale (o null)
        """
        logger.info(f"📄 Ricevuto file: {file.filename}")
        
        # Inizializza risultato vuoto
        result = {
            'success': True,
            'data': {
                'partita_iva': None,
                'codice_ateco': None,
                'oggetto_sociale': None,
                'codici_ateco': [],
                'confidence': {
                    'score': 0,
                    'details': {}
                }
            },
            'method': 'backend'
        }
        
        # ESTRAZIONE ROBUSTA CON GESTIONE ERRORI TOTALE
        tmp_path = None
        try:
            # 1. SALVA FILE TEMPORANEO
            with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as tmp:
                content = await file.read()
                if not content:
                    logger.warning("File vuoto")
                    return JSONResponse(result)
                tmp.write(content)
                tmp_path = tmp.name
                logger.info(f"File salvato: {tmp_path} ({len(content)} bytes)")
            
            # 2. ESTRAI TESTO DAL PDF (con retry e fallback multipli)
            text = ""
            max_retries = 2

            # Funzione helper per estrarre con retry
            def extract_with_retry(extractor_fn, name, retries=max_retries):
                for attempt in range(1, retries + 1):
                    try:
                        logger.info(f"🔄 Tentativo {attempt}/{retries} con {name}")
                        result = extractor_fn()
                        if result:
                            logger.info(f"✅ {name} riuscito al tentativo {attempt}")
                            return result
                    except Exception as e:
                        if attempt < retries:
                            logger.warning(f"⚠️ {name} fallito (tentativo {attempt}): {e}, riprovo...")
                            import time
                            time.sleep(0.5)  # Breve pausa prima del retry
                        else:
                            logger.error(f"❌ {name} fallito dopo {retries} tentativi: {e}")
                return None

            # Prova con pdfplumber (con retry)
            def try_pdfplumber():
                import pdfplumber
                text_result = ""
                with pdfplumber.open(tmp_path) as pdf:
                    for page in pdf.pages:
                        page_text = page.extract_text()
                        if page_text:
                            text_result += page_text + "\n"
                return text_result if text_result else None

            text = extract_with_retry(try_pdfplumber, "pdfplumber")

            # Fallback su PyPDF2 se pdfplumber ha fallito
            if not text:
                logger.warning("pdfplumber fallito, provo PyPDF2...")

                def try_pypdf2():
                    import PyPDF2
                    text_result = ""
                    with open(tmp_path, 'rb') as pdf_file:
                        pdf_reader = PyPDF2.PdfReader(pdf_file)
                        for page in pdf_reader.pages:
                            page_text = page.extract_text()
                            if page_text:
                                text_result += page_text + "\n"
                    return text_result if text_result else None

                text = extract_with_retry(try_pypdf2, "PyPDF2")

            # Fallback su Tesseract OCR se pdfplumber e PyPDF2 hanno fallito (PDF scansionato)
            if not text:
                logger.warning("pdfplumber e PyPDF2 falliti, provo Tesseract OCR (PDF scansionato)...")

                def try_tesseract_ocr():
                    """
                    Estrae testo da PDF scansionato usando Tesseract OCR

                    Processo:
                    1. Converte PDF in immagini
                    2. Applica OCR su ogni immagine
                    3. Concatena tutto il testo estratto
                    """
                    try:
                        from pdf2image import convert_from_path
                        import pytesseract

                        # Converti PDF in immagini (DPI 300 per qualità OCR)
                        images = convert_from_path(tmp_path, dpi=300)

                        if not images:
                            logger.warning("⚠️ Nessuna immagine estratta dal PDF")
                            return None

                        text_result = ""
                        for i, image in enumerate(images, 1):
                            logger.info(f"🔍 OCR su pagina {i}/{len(images)}...")
                            # Estrai testo con Tesseract (lingua italiana + inglese)
                            page_text = pytesseract.image_to_string(image, lang='ita+eng')
                            if page_text:
                                text_result += page_text + "\n"

                        return text_result if text_result.strip() else None

                    except ImportError as e:
                        logger.error(f"❌ Tesseract non installato: {e}")
                        return None
                    except Exception as e:
                        logger.error(f"❌ Errore OCR: {e}")
                        return None

                text = extract_with_retry(try_tesseract_ocr, "Tesseract OCR")

            # Se TUTTI i metodi falliscono dopo retry, ritorna vuoto
            if not text:
                logger.error("❌ TUTTI i metodi di estrazione PDF hanno fallito dopo retry")
                return JSONResponse(result)
            
            # 3. NORMALIZZA TESTO (rimuovi spazi/newline extra per matching robusto)
            import re
            text_normalized = re.sub(r'\s+', ' ', text)  # Sostituisci multipli spazi/newline con singolo spazio
            logger.info(f"📝 Testo estratto: {len(text)} caratteri, normalizzato: {len(text_normalized)} caratteri")

            # 🔍 DEBUG: Stampa primi 2000 caratteri del testo estratto (per analisi pattern)
            logger.info("="*80)
            logger.info("🔍 DEBUG TESTO ESTRATTO (primi 2000 char):")
            logger.info(text[:2000])
            logger.info("="*80)

            # 4. ESTRAI I 3 CAMPI STRICT

            # PARTITA IVA (11 cifre)
            piva_patterns = [
                r'(?:Partita IVA|P\.?\s?IVA|VAT)[\s:]+(\d{11})',
                r'(?:Codice Fiscale|C\.F\.)[\s:]+(\d{11})',
                r'\b(\d{11})\b'
            ]
            partita_iva = None
            for pattern in piva_patterns:
                match = re.search(pattern, text_normalized, re.IGNORECASE)
                if match:
                    piva = match.group(1)
                    if re.match(r'^\d{11}$', piva):
                        partita_iva = piva
                        logger.info(f"✅ P.IVA trovata: {partita_iva}")
                        break
            
            # CODICE ATECO - Estrae 2022 o 2025, poi converte a 2025 usando il database
            # IMPORTANTE: Cerca prima 6 cifre (più specifico), poi 4 cifre (meno specifico)
            # NOTA: L'ultima parte può essere 1-2 cifre (es: 64.99.1 o 64.99.10)
            ateco_patterns = [
                # ========== ATECO 2025 (5-6 cifre: XX.XX.X o XX.XX.XX) - PRIORITÀ MASSIMA ==========
                # Pattern con label esplicita + 5-6 cifre (es: "Codice ATECO 64.99.1")
                r'(?:Codice ATECO|ATECO|Attività prevalente|Codice attività)[\s:]+(\d{2}[\s.]\d{2}[\s.]\d{1,2})',
                # Pattern generico 5-6 cifre con label "Codice:" (es: "Codice: 64.99.1")
                r'Codice[\s:]+(\d{2}\.?\d{2}\.?\d{1,2})\s*-',
                # Pattern generico 5-6 cifre (cattura anche senza label, MA solo se non è una data)
                # Negative lookahead per escludere date tipo 27.06.2022
                r'\b(\d{2}\.\d{2}\.\d{1,2})(?!\d)\b',

                # ========== ATECO 2022 (4 cifre: XX.XX) - FALLBACK ==========
                # Pattern con label esplicita + 4 cifre
                r'(?:Codice ATECO|ATECO|Attività prevalente|Codice attività)[\s:]+(\d{2}[\s.]\d{2})(?!\s*\.\s*\d)',
                # Pattern generico 4 cifre (escludi se seguito da altro .XX)
                r'\b(\d{2}\.\d{2})(?!\s*\.\s*\d)\b'
            ]
            codice_ateco = None
            codice_ateco_raw = None  # Codice estratto dal PDF (potrebbe essere 2022)

            for pattern in ateco_patterns:
                match = re.search(pattern, text_normalized, re.IGNORECASE)
                if match:
                    ateco = match.group(1)
                    codice_ateco_raw = re.sub(r'\s+', '.', ateco)

                    # Escludi anni (19.xx, 20.xx, 21.xx)
                    first_part = int(codice_ateco_raw.split('.')[0])
                    if first_part in [19, 20, 21]:
                        continue

                    logger.info(f"📋 ATECO estratto dal PDF: {codice_ateco_raw}")

                    # Se è già formato 2025 (5-6 cifre: XX.XX.X o XX.XX.XX), usa direttamente
                    if re.match(r'^\d{2}\.\d{2}\.\d{1,2}$', codice_ateco_raw):
                        codice_ateco = codice_ateco_raw
                        logger.info(f"✅ ATECO 2025 trovato direttamente: {codice_ateco}")
                        break
                    # Se è formato 2022 (4 cifre: XX.XX), converti usando il database
                    elif re.match(r'^\d{2}\.\d{2}$', codice_ateco_raw):
                        logger.info(f"🔄 ATECO 2022 trovato: {codice_ateco_raw}, conversione a 2025...")
                        try:
                            # Usa la funzione search_smart del database per ottenere il 2025
                            result_df = search_smart(df, codice_ateco_raw, prefer='2025')
                            if not result_df.empty:
                                row = result_df.iloc[0]
                                codice_2025 = row.get('CODICE_ATECO_2025_RAPPRESENTATIVO', '')
                                if codice_2025:
                                    codice_ateco = normalize_code(codice_2025)
                                    logger.info(f"✅ Conversione riuscita: {codice_ateco_raw} → {codice_ateco}")
                                else:
                                    logger.warning(f"⚠️ Nessun corrispondente 2025 per {codice_ateco_raw}")
                            else:
                                logger.warning(f"⚠️ Codice {codice_ateco_raw} non trovato nel database")
                        except Exception as e:
                            logger.error(f"❌ Errore conversione ATECO: {e}")
                        break
            
            # OGGETTO SOCIALE (min 30 caratteri con parole business)
            # NOTA: Cattura TUTTO il testo multiriga (fino a 2000 caratteri)
            oggetto_patterns = [
                r'(?:OGGETTO SOCIALE|Oggetto sociale|Oggetto)[\s:]+(.{30,2000})',
                r'(?:Attività|ATTIVITA)[\s:]+(.{30,2000})',
            ]
            oggetto_sociale = None
            business_words = ['produzione', 'commercio', 'servizi', 'consulenza',
                            'vendita', 'gestione', 'prestazione', 'attività', 'investiment']
            for pattern in oggetto_patterns:
                match = re.search(pattern, text_normalized, re.IGNORECASE | re.DOTALL)
                if match:
                    oggetto = match.group(1).strip()
                    # Pulisci newline multipli e spazi eccessivi
                    oggetto = re.sub(r'\s+', ' ', oggetto)
                    if len(oggetto) >= 30:
                        has_business = any(w in oggetto.lower() for w in business_words)
                        if has_business:
                            if len(oggetto) > 2000:
                                oggetto = oggetto[:2000] + '...'
                            oggetto_sociale = oggetto
                            logger.info(f"✅ Oggetto trovato ({len(oggetto)} caratteri): {oggetto_sociale[:80]}...")
                            break

            # SEDE LEGALE (Comune + Provincia) - CRITICO per zona sismica!
            sede_legale = None
            # Pattern per estrarre sede legale dalle visure camerali
            sede_patterns = [
                # Pattern completo con comune e provincia
                r'(?:SEDE LEGALE|Sede legale|Sede)[\s:]+([A-Z][A-Za-z\s]+?)\s*\(([A-Z]{2})\)',
                r'(?:SEDE|Sede)[\s:]+(?:in\s+)?([A-Z][A-Za-z\s]+?)\s*\(([A-Z]{2})\)',
                # Pattern con Via + Comune + Provincia
                r'[Vv]ia\s+[^,]+,\s*([A-Z][A-Za-z\s]+?)\s*\(([A-Z]{2})\)',
                # Pattern generico: Comune (Provincia)
                r'\b([A-Z][A-Za-z\s]{3,30}?)\s*\(([A-Z]{2})\)\b'
            ]

            for pattern in sede_patterns:
                matches = re.finditer(pattern, text_normalized)
                for match in matches:
                    comune = match.group(1).strip()
                    provincia = match.group(2).strip()

                    # Validazione comune (no parole comuni)
                    common_words = ['VIA', 'VIALE', 'PIAZZA', 'CORSO', 'STRADA', 'LOCALITÀ',
                                  'FRAZIONE', 'PRESSO', 'ITALY', 'ITALIA']
                    if comune.upper() not in common_words and len(comune) > 3:
                        # Rimuovi "di" all'inizio (es: "di TORINO" → "TORINO")
                        if comune.lower().startswith('di '):
                            comune = comune[3:]

                        sede_legale = {
                            'comune': comune.title(),  # Prima lettera maiuscola
                            'provincia': provincia.upper()
                        }
                        logger.info(f"✅ Sede legale trovata: {comune} ({provincia})")
                        break

                if sede_legale:
                    break

            # 4. CALCOLA CONFIDENCE REALE
            score = 0
            if partita_iva:
                score += 33
                result['data']['partita_iva'] = partita_iva
                result['data']['confidence']['details']['partita_iva'] = 'valid'
            if codice_ateco:
                score += 33
                result['data']['codice_ateco'] = codice_ateco
                # Aggiungi anche in formato array per compatibilità
                result['data']['codici_ateco'] = [{
                    'codice': codice_ateco,
                    'descrizione': '',
                    'principale': True
                }]
                result['data']['confidence']['details']['ateco'] = 'valid'
            if oggetto_sociale:
                score += 25
                result['data']['oggetto_sociale'] = oggetto_sociale
                result['data']['confidence']['details']['oggetto_sociale'] = 'valid'
            if sede_legale:
                score += 25  # Molto importante per zona sismica!
                result['data']['sede_legale'] = sede_legale
                result['data']['confidence']['details']['sede_legale'] = 'valid'
            else:
                result['data']['confidence']['details']['sede_legale'] = 'not_found'

            result['data']['confidence']['score'] = min(score, 100)  # Cap a 100%
            logger.info(f"📊 Estrazione completata: {score}% confidence (P.IVA: {bool(partita_iva)}, ATECO: {bool(codice_ateco)}, Oggetto: {bool(oggetto_sociale)}, Sede: {bool(sede_legale)})")
            
        except Exception as e:
            logger.error(f"❌ Errore estrazione: {str(e)}")
            # In caso di QUALSIASI errore, ritorna risultato vuoto (non crasha)
        
        finally:
            # Pulisci file temporaneo
            if tmp_path:
                try:
                    os.unlink(tmp_path)
                except:
                    pass
        
        return JSONResponse(result)

    # ENDPOINT ZONE SISMICHE - Database completo comuni italiani
    @app.get("/seismic-zone/{comune}")
    async def get_seismic_zone(comune: str, provincia: Optional[str] = None):
        """
        Restituisce la zona sismica di un comune italiano

        Args:
            comune: Nome del comune (case-insensitive)
            provincia: Sigla provincia opzionale per disambiguare comuni omonimi

        Returns:
            Dati zona sismica: zona, ag, risk_level, description
        """
        try:
            # Carica database zone sismiche
            db_path = Path('zone_sismiche_comuni.json')
            if not db_path.exists():
                logger.error("Database zone sismiche non trovato")
                return JSONResponse({
                    "error": "database_not_found",
                    "message": "Database zone sismiche non disponibile"
                }, status_code=500)

            with open(db_path, 'r', encoding='utf-8') as f:
                db = json.load(f)

            # Normalizza input comune
            comune_upper = comune.upper().strip()
            comune_clean = comune_upper.replace("'", "'").replace("À", "A").replace("È", "E").replace("É", "E").replace("Ì", "I").replace("Ò", "O").replace("Ù", "U")

            # RICERCA ESATTA
            if comune_upper in db['comuni']:
                zona_data = db['comuni'][comune_upper]

                # Se provincia specificata, verifica match
                if provincia and zona_data['provincia'] != provincia.upper():
                    return JSONResponse({
                        "error": "comune_provincia_mismatch",
                        "message": f"Comune {comune} non trovato in provincia {provincia}",
                        "suggestion": f"{comune} trovato in provincia {zona_data['provincia']}"
                    }, status_code=404)

                # Descrizione dettagliata zona
                zona = zona_data['zona_sismica']
                descriptions = {
                    1: "Zona 1 - Sismicità alta: È la zona più pericolosa, dove possono verificarsi fortissimi terremoti",
                    2: "Zona 2 - Sismicità media: Zona dove possono verificarsi forti terremoti",
                    3: "Zona 3 - Sismicità bassa: Zona che può essere soggetta a scuotimenti modesti",
                    4: "Zona 4 - Sismicità molto bassa: È la zona meno pericolosa"
                }

                return JSONResponse({
                    "comune": comune_upper,
                    "provincia": zona_data['provincia'],
                    "regione": zona_data.get('regione', 'N/D'),
                    "zona_sismica": zona,
                    "accelerazione_ag": zona_data['accelerazione_ag'],
                    "risk_level": zona_data['risk_level'],
                    "description": descriptions.get(zona, "N/D"),
                    "normativa": "OPCM 3519/2006",
                    "source": "database_match",
                    "confidence": 1.0
                })

            # RICERCA FUZZY CON SIMILARITÀ
            from difflib import get_close_matches

            # Cerca comuni simili
            all_comuni = list(db['comuni'].keys())
            matches = get_close_matches(comune_clean, all_comuni, n=5, cutoff=0.6)

            if matches:
                # Se solo 1 match con alta confidenza, ritorna quello
                if len(matches) == 1 or len(matches) > 0:
                    best_match = matches[0]
                    zona_data = db['comuni'][best_match]

                    # Se provincia specificata, filtra per provincia
                    if provincia:
                        provincia_matches = [m for m in matches if db['comuni'][m]['provincia'] == provincia.upper()]
                        if provincia_matches:
                            best_match = provincia_matches[0]
                            zona_data = db['comuni'][best_match]
                        else:
                            return JSONResponse({
                                "error": "no_match_in_provincia",
                                "message": f"Nessun comune simile a '{comune}' trovato in provincia {provincia}",
                                "suggestions": [{"comune": m, "provincia": db['comuni'][m]['provincia']} for m in matches[:3]]
                            }, status_code=404)

                    zona = zona_data['zona_sismica']
                    descriptions = {
                        1: "Zona 1 - Sismicità alta: È la zona più pericolosa, dove possono verificarsi fortissimi terremoti",
                        2: "Zona 2 - Sismicità media: Zona dove possono verificarsi forti terremoti",
                        3: "Zona 3 - Sismicità bassa: Zona che può essere soggetta a scuotimenti modesti",
                        4: "Zona 4 - Sismicità molto bassa: È la zona meno pericolosa"
                    }

                    # Calcola confidence basata su similarità
                    from difflib import SequenceMatcher
                    confidence = SequenceMatcher(None, comune_clean, best_match).ratio()

                    return JSONResponse({
                        "comune": best_match,
                        "input_comune": comune_upper,
                        "provincia": zona_data['provincia'],
                        "regione": zona_data.get('regione', 'N/D'),
                        "zona_sismica": zona,
                        "accelerazione_ag": zona_data['accelerazione_ag'],
                        "risk_level": zona_data['risk_level'],
                        "description": descriptions.get(zona, "N/D"),
                        "normativa": "OPCM 3519/2006",
                        "source": "fuzzy_match",
                        "confidence": round(confidence, 2),
                        "note": f"Match approssimato: '{comune}' -> '{best_match}'"
                    })

            # NESSUN MATCH - Stima basata su provincia/regione
            # Logica: comuni non mappati ereditano zona media della provincia
            provincia_estimation = None
            if provincia:
                # Trova zona più comune nella provincia
                comuni_provincia = {k: v for k, v in db['comuni'].items() if v['provincia'] == provincia.upper()}
                if comuni_provincia:
                    zone_counts = {}
                    for data in comuni_provincia.values():
                        z = data['zona_sismica']
                        zone_counts[z] = zone_counts.get(z, 0) + 1
                    zona_stimata = max(zone_counts, key=zone_counts.get)
                    provincia_estimation = {
                        "zona_sismica": zona_stimata,
                        "accelerazione_ag": db["metadata"]["ag_reference"][f"zona_{zona_stimata}"],
                        "risk_level": ["Molto Alta", "Alta", "Media", "Bassa"][zona_stimata-1]
                    }

            if provincia_estimation:
                zona = provincia_estimation['zona_sismica']
                descriptions = {
                    1: "Zona 1 - Sismicità alta: È la zona più pericolosa, dove possono verificarsi fortissimi terremoti",
                    2: "Zona 2 - Sismicità media: Zona dove possono verificarsi forti terremoti",
                    3: "Zona 3 - Sismicità bassa: Zona che può essere soggetta a scuotimenti modesti",
                    4: "Zona 4 - Sismicità molto bassa: È la zona meno pericolosa"
                }

                return JSONResponse({
                    "comune": comune_upper,
                    "provincia": provincia.upper(),
                    "zona_sismica": zona,
                    "accelerazione_ag": provincia_estimation['accelerazione_ag'],
                    "risk_level": provincia_estimation['risk_level'],
                    "description": descriptions.get(zona, "N/D"),
                    "normativa": "OPCM 3519/2006",
                    "source": "provincia_estimation",
                    "confidence": 0.5,
                    "note": f"Stima basata sulla zona prevalente della provincia {provincia}"
                })

            # ULTIMO FALLBACK - Ritorna suggerimenti
            suggestions = []
            if matches:
                for match in matches[:5]:
                    suggestions.append({
                        "comune": match,
                        "provincia": db['comuni'][match]['provincia'],
                        "zona_sismica": db['comuni'][match]['zona_sismica']
                    })

            return JSONResponse({
                "error": "comune_not_found",
                "message": f"Comune '{comune}' non trovato nel database",
                "suggestions": suggestions if suggestions else [],
                "suggestion_text": "Verifica il nome del comune o fornisci la sigla provincia"
            }, status_code=404)

        except Exception as e:
            logger.error(f"Errore in seismic-zone endpoint: {str(e)}", exc_info=True)
            return JSONResponse({
                "error": "internal_error",
                "message": "Errore interno del server",
                "details": str(e)
            }, status_code=500)

    # ENDPOINT ADMIN - Database Setup
    @app.get("/admin/setup-database")
    async def setup_database():
        """
        Esegue setup tabelle Syd Agent tracking
        IMPORTANTE: Usa questo endpoint SOLO per inizializzare database
        """
        try:
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
                return JSONResponse(results, status_code=500)
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
                return JSONResponse(results, status_code=500)

            # Step 3: Execute SQL
            results["steps"].append({"step": 3, "name": "Esegui SQL", "status": "running"})
            engine = get_engine()
            try:
                execute_sql(engine, sql_content)
                results["steps"][-1]["status"] = "completed"
            except Exception as e:
                results["steps"][-1]["status"] = "failed"
                results["steps"][-1]["error"] = str(e)
                return JSONResponse(results, status_code=500)

            # Step 4: Verify tables
            results["steps"].append({"step": 4, "name": "Verifica tabelle", "status": "running"})
            if not verify_tables(engine):
                results["steps"][-1]["status"] = "failed"
                results["steps"][-1]["error"] = "Tabelle non create"
                return JSONResponse(results, status_code=500)
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

            return JSONResponse(results)

        except Exception as e:
            logger.error(f"Errore in setup-database endpoint: {str(e)}", exc_info=True)
            return JSONResponse({
                "success": False,
                "error": "internal_error",
                "message": "Errore durante setup database",
                "details": str(e),
                "steps": results.get("steps", [])
            }, status_code=500)

    # ENDPOINT ADMIN - Check Tables Status
    @app.get("/admin/check-tables")
    async def check_tables_status():
        """
        Verifica quali tabelle esistono nel database
        SOLO LETTURA - non modifica nulla
        """
        try:
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

            return JSONResponse(results)

        except Exception as e:
            logger.error(f"Errore in check-tables endpoint: {str(e)}", exc_info=True)
            return JSONResponse({
                "status": "error",
                "message": "Errore durante verifica tabelle",
                "details": str(e)
            }, status_code=500)

    # ENDPOINT ADMIN - Create Missing Tables
    @app.post("/admin/create-tables")
    async def create_missing_tables():
        """
        Crea le 6 tabelle mancanti nel database PostgreSQL

        SICUREZZA:
        - Non cancella tabelle esistenti
        - Non modifica dati esistenti
        - Usa SQLAlchemy create_all (idempotente)

        Tabelle create:
        1. users (consultanti)
        2. companies (aziende)
        3. assessments (valutazioni)
        4. risk_events (191 eventi)
        5. ateco_codes (25K codici)
        6. seismic_zones (8K comuni)
        """
        try:
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

            return JSONResponse(results)

        except Exception as e:
            logger.error(f"Errore in create-tables endpoint: {str(e)}", exc_info=True)
            return JSONResponse({
                "success": False,
                "error": "internal_error",
                "message": "Errore durante creazione tabelle",
                "details": str(e),
                "steps": results.get("steps", [])
            }, status_code=500)

    # ENDPOINT ADMIN - Migrate Risk Events
    @app.post("/admin/migrate-risk-events")
    async def migrate_risk_events():
        """
        Migra 191 eventi rischio da MAPPATURE_EXCEL_PERFETTE.json → PostgreSQL

        SICUREZZA:
        - Skip eventi già esistenti (no duplicati)
        - Transazione atomica (rollback su errore)
        - Report dettagliato step-by-step
        """
        try:
            from database.config import get_db_session
            from database.models import RiskEvent
            import json
            from pathlib import Path

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

            json_path = Path(__file__).parent / "MAPPATURE_EXCEL_PERFETTE.json"

            if not json_path.exists():
                results["steps"][-1]["status"] = "failed"
                results["steps"][-1]["error"] = f"File non trovato: {json_path}"
                return JSONResponse(results, status_code=404)

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

            # Category mapping
            category_mapping = {
                "Damage_Danni": "Damage/Danni",
                "Business_disruption": "Business Disruption",
                "Employment_practices_Dipendenti": "Employment Practices",
                "Execution_delivery_Problemi_di_produzione_o_consegna": "Execution & Delivery",
                "Clients_product_Clienti": "Clients & Products",
                "Internal_Fraud_Frodi_interne": "Internal Fraud",
                "External_fraud_Frodi_esterne": "External Fraud"
            }

            # Severity mapping
            def get_severity(code: str) -> str:
                code_num = int(code)
                if code_num < 200:
                    return "low"
                elif code_num < 300:
                    return "medium"
                elif code_num < 500:
                    return "high"
                else:
                    return "critical"

            # Parse events
            events_to_insert = []
            parse_errors = []

            for category_key, events_list in data.get('mappature_categoria_eventi', {}).items():
                category_name = category_mapping.get(category_key, category_key)

                for event_line in events_list:
                    # Parse: "101 - Disastro naturale: fuoco"
                    parts = event_line.split(" - ", 1)

                    if len(parts) != 2:
                        parse_errors.append(f"Formato non valido: {event_line}")
                        continue

                    code = parts[0].strip()
                    name = parts[1].strip()
                    severity = get_severity(code)

                    events_to_insert.append({
                        "code": code,
                        "name": name,
                        "category": category_name,
                        "severity": severity
                    })

            results["steps"][-1]["status"] = "completed"
            results["steps"][-1]["total_events"] = len(events_to_insert)
            results["steps"][-1]["parse_errors"] = len(parse_errors)

            if parse_errors:
                results["steps"][-1]["errors"] = parse_errors[:5]  # First 5 errors

            # Step 3: Insert into database
            results["steps"].append({
                "step": 3,
                "name": "Inserisci eventi nel database",
                "status": "running"
            })

            inserted = 0
            skipped = 0
            errors = []

            # Remove duplicates from events_to_insert BEFORE inserting
            seen_codes = set()
            unique_events = []
            duplicates = []

            for event_data in events_to_insert:
                if event_data["code"] in seen_codes:
                    duplicates.append(event_data["code"])
                    skipped += 1
                    continue

                seen_codes.add(event_data["code"])
                unique_events.append(event_data)

            with get_db_session() as session:
                for event_data in unique_events:
                    # Check if exists in database
                    existing = session.query(RiskEvent).filter_by(code=event_data["code"]).first()

                    if existing:
                        skipped += 1
                        continue

                    # Insert new event
                    risk_event = RiskEvent(
                        code=event_data["code"],
                        name=event_data["name"],
                        category=event_data["category"],
                        description=None,
                        severity=event_data["severity"],
                        suggested_controls=None
                    )

                    session.add(risk_event)
                    inserted += 1

                # Commit all at once
                session.commit()

            results["steps"][-1]["status"] = "completed"
            results["steps"][-1]["inserted"] = inserted
            results["steps"][-1]["skipped"] = skipped
            if duplicates:
                results["steps"][-1]["duplicates_found"] = duplicates

            # Step 4: Verify
            results["steps"].append({
                "step": 4,
                "name": "Verifica dati inseriti",
                "status": "running"
            })

            with get_db_session() as session:
                total_count = session.query(RiskEvent).count()

            results["steps"][-1]["status"] = "completed"
            results["steps"][-1]["total_in_db"] = total_count

            # Success
            results["success"] = True
            results["message"] = f"✅ Migrazione completata! {inserted} eventi inseriti, {skipped} già esistenti"
            results["summary"] = {
                "total_events": len(events_to_insert),
                "inserted": inserted,
                "skipped": skipped,
                "total_in_db": total_count,
                "expected": 191
            }

            if total_count != 191:
                results["warning"] = f"Attesi 191 eventi, trovati {total_count}"

            return JSONResponse(results)

        except Exception as e:
            logger.error(f"Errore in migrate-risk-events endpoint: {str(e)}", exc_info=True)
            return JSONResponse({
                "success": False,
                "error": "internal_error",
                "message": "Errore durante migrazione eventi",
                "details": str(e),
                "steps": results.get("steps", [])
            }, status_code=500)

    # ENDPOINT ADMIN - Migrate ATECO Codes
    @app.post("/admin/migrate-ateco")
    async def migrate_ateco_codes():
        """
        Migra ~25K codici ATECO da tabella_ATECO.xlsx → PostgreSQL

        SICUREZZA:
        - Skip codici già esistenti (no duplicati)
        - Batch insert (1000 righe per volta)
        - Transazione atomica (rollback su errore)
        """
        try:
            from database.config import get_db_session
            from database.models import ATECOCode
            import pandas as pd
            from pathlib import Path

            results = {
                "steps": [],
                "success": False
            }

            # Step 1: Load Excel file
            results["steps"].append({
                "step": 1,
                "name": "Carica tabella_ATECO.xlsx",
                "status": "running"
            })

            excel_path = Path(__file__).parent / "tabella_ATECO.xlsx"

            if not excel_path.exists():
                results["steps"][-1]["status"] = "failed"
                results["steps"][-1]["error"] = f"File non trovato: {excel_path}"
                return JSONResponse(results, status_code=404)

            # Load Excel with existing function
            df = load_dataset(excel_path, debug=False)

            results["steps"][-1]["status"] = "completed"
            results["steps"][-1]["total_rows"] = len(df)

            # Step 2: Parse and prepare data
            results["steps"].append({
                "step": 2,
                "name": "Parse codici ATECO",
                "status": "running"
            })

            codes_to_insert = []
            parse_errors = []

            for idx, row in df.iterrows():
                try:
                    # Extract fields (handle NaN)
                    code_2022 = str(row.get("CODICE_ATECO_2022", "")).strip()
                    if code_2022 == "nan" or not code_2022:
                        code_2022 = None

                    code_2025 = str(row.get("CODICE_ATECO_2025_RAPPRESENTATIVO", "")).strip()
                    if code_2025 == "nan" or not code_2025:
                        continue  # Skip if no 2025 code

                    code_2025_camerale = str(row.get("CODICE_ATECO_2025_RAPPRESENTATIVO_SISTEMA_CAMERALE", "")).strip()
                    if code_2025_camerale == "nan" or not code_2025_camerale:
                        code_2025_camerale = None

                    title_2022 = str(row.get("TITOLO_ATECO_2022", "")).strip()
                    if title_2022 == "nan" or not title_2022:
                        title_2022 = None

                    title_2025 = str(row.get("TITOLO_ATECO_2025_RAPPRESENTATIVO", "")).strip()
                    if title_2025 == "nan" or not title_2025:
                        title_2025 = code_2025  # Fallback to code

                    hierarchy = str(row.get("GERARCHIA_ATECO_2022", "")).strip()
                    if hierarchy == "nan" or not hierarchy:
                        hierarchy = None

                    codes_to_insert.append({
                        "code_2022": code_2022,
                        "code_2025": code_2025,
                        "code_2025_camerale": code_2025_camerale,
                        "title_2022": title_2022,
                        "title_2025": title_2025,
                        "hierarchy": hierarchy,
                        "sector": None,  # TODO: Add sector mapping if needed
                        "regulations": None,
                        "certifications": None
                    })

                except Exception as e:
                    parse_errors.append(f"Row {idx}: {str(e)}")

            results["steps"][-1]["status"] = "completed"
            results["steps"][-1]["total_codes"] = len(codes_to_insert)
            results["steps"][-1]["parse_errors"] = len(parse_errors)

            if parse_errors:
                results["steps"][-1]["errors"] = parse_errors[:5]

            # Step 3: Remove duplicates
            results["steps"].append({
                "step": 3,
                "name": "Rimuovi duplicati",
                "status": "running"
            })

            seen_codes = set()
            unique_codes = []
            duplicates = []

            for code_data in codes_to_insert:
                code_2025 = code_data["code_2025"]
                if code_2025 in seen_codes:
                    duplicates.append(code_2025)
                    continue

                seen_codes.add(code_2025)
                unique_codes.append(code_data)

            results["steps"][-1]["status"] = "completed"
            results["steps"][-1]["unique_codes"] = len(unique_codes)
            results["steps"][-1]["duplicates"] = len(duplicates)

            # Step 4: Insert into database (batch insert for performance)
            results["steps"].append({
                "step": 4,
                "name": "Inserisci nel database (batch 1000)",
                "status": "running"
            })

            inserted = 0
            skipped = 0
            batch_size = 1000

            with get_db_session() as session:
                for i in range(0, len(unique_codes), batch_size):
                    batch = unique_codes[i:i+batch_size]

                    for code_data in batch:
                        # Check if exists
                        existing = session.query(ATECOCode).filter_by(code_2025=code_data["code_2025"]).first()

                        if existing:
                            skipped += 1
                            continue

                        # Insert new code
                        ateco_code = ATECOCode(
                            code_2022=code_data["code_2022"],
                            code_2025=code_data["code_2025"],
                            code_2025_camerale=code_data["code_2025_camerale"],
                            title_2022=code_data["title_2022"],
                            title_2025=code_data["title_2025"],
                            hierarchy=code_data["hierarchy"],
                            sector=code_data["sector"],
                            regulations=code_data["regulations"],
                            certifications=code_data["certifications"]
                        )

                        session.add(ateco_code)
                        inserted += 1

                    # Commit each batch
                    session.commit()
                    logger.info(f"Batch {i//batch_size + 1}: {inserted} inseriti, {skipped} saltati")

            results["steps"][-1]["status"] = "completed"
            results["steps"][-1]["inserted"] = inserted
            results["steps"][-1]["skipped"] = skipped

            # Step 5: Verify
            results["steps"].append({
                "step": 5,
                "name": "Verifica dati inseriti",
                "status": "running"
            })

            with get_db_session() as session:
                total_count = session.query(ATECOCode).count()

            results["steps"][-1]["status"] = "completed"
            results["steps"][-1]["total_in_db"] = total_count

            # Success
            results["success"] = True
            results["message"] = f"✅ Migrazione ATECO completata! {inserted} codici inseriti"
            results["summary"] = {
                "total_in_excel": len(df),
                "parsed": len(codes_to_insert),
                "unique": len(unique_codes),
                "inserted": inserted,
                "skipped": skipped,
                "total_in_db": total_count
            }

            return JSONResponse(results)

        except Exception as e:
            logger.error(f"Errore in migrate-ateco endpoint: {str(e)}", exc_info=True)
            return JSONResponse({
                "success": False,
                "error": "internal_error",
                "message": "Errore durante migrazione ATECO",
                "details": str(e),
                "steps": results.get("steps", [])
            }, status_code=500)

    # ENDPOINT ADMIN - Migrate Seismic Zones
    @app.post("/admin/migrate-seismic-zones")
    async def migrate_seismic_zones():
        """
        Migra 8K comuni italiani + zone sismiche da zone_sismiche_comuni.json → PostgreSQL

        SICUREZZA:
        - Skip comuni già esistenti (no duplicati)
        - Batch insert (500 righe per volta)
        - Transazione atomica (rollback su errore)
        """
        try:
            from database.config import get_db_session
            from database.models import SeismicZone
            import json
            from pathlib import Path
            from decimal import Decimal

            results = {
                "steps": [],
                "success": False
            }

            # Step 1: Load JSON file
            results["steps"].append({
                "step": 1,
                "name": "Carica zone_sismiche_comuni.json",
                "status": "running"
            })

            json_path = Path(__file__).parent / "zone_sismiche_comuni.json"

            if not json_path.exists():
                results["steps"][-1]["status"] = "failed"
                results["steps"][-1]["error"] = f"File non trovato: {json_path}"
                return JSONResponse(results, status_code=404)

            with open(json_path, 'r', encoding='utf-8') as f:
                data = json.load(f)

            results["steps"][-1]["status"] = "completed"
            results["steps"][-1]["file_size"] = len(json.dumps(data))
            results["steps"][-1]["metadata"] = data.get("metadata", {})

            # Step 2: Parse comuni
            results["steps"].append({
                "step": 2,
                "name": "Parse comuni e zone sismiche",
                "status": "running"
            })

            comuni_to_insert = []
            parse_errors = []

            for comune_name, comune_data in data.get("comuni", {}).items():
                try:
                    provincia = comune_data.get("provincia", "").strip()
                    regione = comune_data.get("regione", "").strip()
                    zona_sismica = int(comune_data.get("zona_sismica", 0))
                    accelerazione_ag = float(comune_data.get("accelerazione_ag", 0.0))
                    risk_level = comune_data.get("risk_level", "").strip()

                    if not provincia or not regione or zona_sismica == 0:
                        parse_errors.append(f"{comune_name}: campi mancanti")
                        continue

                    comuni_to_insert.append({
                        "comune": comune_name.upper(),
                        "provincia": provincia.upper(),
                        "regione": regione.upper(),
                        "zona_sismica": zona_sismica,
                        "accelerazione_ag": Decimal(str(accelerazione_ag)),
                        "risk_level": risk_level
                    })

                except Exception as e:
                    parse_errors.append(f"{comune_name}: {str(e)}")

            results["steps"][-1]["status"] = "completed"
            results["steps"][-1]["total_comuni"] = len(comuni_to_insert)
            results["steps"][-1]["parse_errors"] = len(parse_errors)

            if parse_errors:
                results["steps"][-1]["errors"] = parse_errors[:5]

            # Step 3: Remove duplicates
            results["steps"].append({
                "step": 3,
                "name": "Rimuovi duplicati",
                "status": "running"
            })

            seen_comuni = set()
            unique_comuni = []
            duplicates = []

            for comune_data in comuni_to_insert:
                key = (comune_data["comune"], comune_data["provincia"])
                if key in seen_comuni:
                    duplicates.append(f"{comune_data['comune']} ({comune_data['provincia']})")
                    continue

                seen_comuni.add(key)
                unique_comuni.append(comune_data)

            results["steps"][-1]["status"] = "completed"
            results["steps"][-1]["unique_comuni"] = len(unique_comuni)
            results["steps"][-1]["duplicates"] = len(duplicates)

            # Step 4: Insert into database (batch insert)
            results["steps"].append({
                "step": 4,
                "name": "Inserisci nel database (batch 500)",
                "status": "running"
            })

            inserted = 0
            skipped = 0
            batch_size = 500

            with get_db_session() as session:
                for i in range(0, len(unique_comuni), batch_size):
                    batch = unique_comuni[i:i+batch_size]

                    for comune_data in batch:
                        # Check if exists
                        existing = session.query(SeismicZone).filter_by(
                            comune=comune_data["comune"],
                            provincia=comune_data["provincia"]
                        ).first()

                        if existing:
                            skipped += 1
                            continue

                        # Insert new comune
                        seismic_zone = SeismicZone(
                            comune=comune_data["comune"],
                            provincia=comune_data["provincia"],
                            regione=comune_data["regione"],
                            zona_sismica=comune_data["zona_sismica"],
                            accelerazione_ag=comune_data["accelerazione_ag"],
                            risk_level=comune_data["risk_level"]
                        )

                        session.add(seismic_zone)
                        inserted += 1

                    # Commit each batch
                    session.commit()
                    logger.info(f"Batch {i//batch_size + 1}: {inserted} inseriti, {skipped} saltati")

            results["steps"][-1]["status"] = "completed"
            results["steps"][-1]["inserted"] = inserted
            results["steps"][-1]["skipped"] = skipped

            # Step 5: Verify
            results["steps"].append({
                "step": 5,
                "name": "Verifica dati inseriti",
                "status": "running"
            })

            with get_db_session() as session:
                total_count = session.query(SeismicZone).count()

            results["steps"][-1]["status"] = "completed"
            results["steps"][-1]["total_in_db"] = total_count

            # Success
            results["success"] = True
            results["message"] = f"✅ Migrazione zone sismiche completata! {inserted} comuni inseriti"
            results["summary"] = {
                "total_in_json": len(data.get("comuni", {})),
                "parsed": len(comuni_to_insert),
                "unique": len(unique_comuni),
                "inserted": inserted,
                "skipped": skipped,
                "total_in_db": total_count
            }

            return JSONResponse(results)

        except Exception as e:
            logger.error(f"Errore in migrate-seismic-zones endpoint: {str(e)}", exc_info=True)
            return JSONResponse({
                "success": False,
                "error": "internal_error",
                "message": "Errore durante migrazione zone sismiche",
                "details": str(e),
                "steps": results.get("steps", [])
            }, status_code=500)

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
