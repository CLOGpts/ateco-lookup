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

# Variabili globali per cache
_global_df = None
_df_hash = None

def build_api(df: pd.DataFrame):
    from fastapi import FastAPI, Query, HTTPException, UploadFile, File
    from fastapi.responses import JSONResponse
    from fastapi.middleware.cors import CORSMiddleware
    from pydantic import BaseModel
    from typing import List
    
    # Import condizionale per VisuraExtractor
    try:
        from visura_extractor import VisuraExtractor
        visura_extraction_available = True
    except ImportError:
        logger.warning("VisuraExtractor non disponibile - installa pdfplumber")
        visura_extraction_available = False
    
    class BatchRequest(BaseModel):
        codes: List[str]
        prefer: Optional[str] = None
        prefix: bool = False

    app = FastAPI(title="ATECO Lookup", version="2.0")

    # Abilita CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # in produzione meglio specificare solo il dominio della UI
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.get("/health")
    def health():
        logger.info("Health check requested")
        return {"status": "ok", "version": "2.0", "cache_enabled": True}

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
    
    @app.post("/api/extract-visura")
    async def extract_visura(file: UploadFile = File(...)):
        """
        Estrae dati strutturati da una visura camerale PDF
        
        Returns:
            JSON con codici ATECO, oggetto sociale, sedi e tipo business
        """
        logger.info(f"Ricevuto file per estrazione: {file.filename}")
        
        # Verifica che VisuraExtractor sia disponibile
        if not visura_extraction_available:
            logger.error("VisuraExtractor non disponibile")
            return JSONResponse({
                'success': False,
                'error': {
                    'code': 'MODULE_NOT_AVAILABLE',
                    'message': 'Modulo estrazione PDF non disponibile',
                    'details': 'Installa pdfplumber: pip install pdfplumber'
                }
            }, status_code=503)
        
        # Validazione tipo file
        if not file.filename.endswith('.pdf'):
            logger.warning(f"File non PDF ricevuto: {file.filename}")
            raise HTTPException(
                status_code=400,
                detail={
                    "code": "INVALID_FILE_TYPE",
                    "message": "Solo file PDF sono accettati",
                    "details": f"File ricevuto: {file.filename}"
                }
            )
        
        # Validazione dimensione (20MB max)
        if file.size and file.size > 20 * 1024 * 1024:
            logger.warning(f"File troppo grande: {file.size} bytes")
            raise HTTPException(
                status_code=400,
                detail={
                    "code": "FILE_TOO_LARGE",
                    "message": "File troppo grande (max 20MB)",
                    "details": f"Dimensione: {file.size} bytes"
                }
            )
        
        # Salva temporaneamente il file
        with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as tmp:
            content = await file.read()
            tmp.write(content)
            tmp_path = tmp.name
            logger.info(f"File salvato temporaneamente: {tmp_path}")
        
        try:
            # Estrai dati usando VisuraExtractor
            extractor = VisuraExtractor()
            result = extractor.extract_from_pdf(tmp_path)
            
            # Se estrazione riuscita e ci sono codici ATECO, arricchisci con dati ATECO
            if result.get('success') and result.get('data', {}).get('codici_ateco'):
                ateco_enrichment = []
                for code in result['data']['codici_ateco']:
                    # Usa la funzione lookup esistente per arricchire
                    lookup_result = ateco_lookup(df, code, prefer="2025-camerale")
                    if lookup_result:
                        ateco_enrichment.append({
                            'code': code,
                            'description': lookup_result.get('TITOLO_ATECO_2025_RAPPRESENTATIVO') or 
                                         lookup_result.get('TITOLO_ATECO_2022') or 
                                         "Descrizione non trovata",
                            'normative': lookup_result.get('normative', []),
                            'certificazioni': lookup_result.get('certificazioni', [])
                        })
                
                # Aggiungi arricchimento al risultato
                result['data']['ateco_details'] = ateco_enrichment
                logger.info(f"Arricchiti {len(ateco_enrichment)} codici ATECO")
            
            logger.info(f"Estrazione completata con successo: {result.get('data', {}).get('confidence', 0):.0%} confidence")
            return JSONResponse(result)
            
        except Exception as e:
            logger.error(f"Errore durante estrazione: {str(e)}")
            return JSONResponse({
                'success': False,
                'error': {
                    'code': 'EXTRACTION_ERROR',
                    'message': 'Errore durante estrazione dati dal PDF',
                    'details': str(e)
                }
            }, status_code=500)
            
        finally:
            # Pulisci file temporaneo
            try:
                os.unlink(tmp_path)
                logger.debug(f"File temporaneo eliminato: {tmp_path}")
            except:
                pass

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

if __name__ == "__main__":
    main()
