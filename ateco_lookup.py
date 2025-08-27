#!/usr/bin/env python3
"""
ATECO Lookup – offline & API-ready (no ISTAT APIs)

Obiettivo: dato un codice ATECO, restituire subito tutte le informazioni (descrizioni 2022/2025,
ricodifiche, gerarchie). Funziona:
  • in locale via CLI
  • come micro‑API FastAPI (per uso esterno dalla chat in futuro)

Dipendenze minime: pandas, openpyxl
Opzionali per API: fastapi, uvicorn

Installazione (Windows/macOS/Linux):
  pip install pandas openpyxl
  # API opzionali
  pip install fastapi uvicorn

Esempi CLI:
  python ateco_lookup.py --file tabella_ATECO.xlsx --code 01.11.0
  python ateco_lookup.py --file tabella_ATECO.xlsx --code 01.11 --prefix
  python ateco_lookup.py --file tabella_ATECO.xlsx --code 01.11.00 --prefer 2025-camerale

Avvio API locali:
  python ateco_lookup.py --file tabella_ATECO.xlsx --serve --host 127.0.0.1 --port 8000
  # poi GET http://127.0.0.1:8000/lookup?code=01.11.0

Nota: rileva automaticamente il foglio con i dati (se esiste "Tabella operativa" lo usa, altrimenti il primo).
"""
from __future__ import annotations
import argparse
import json
from pathlib import Path
from typing import Dict, List, Optional, Union

import pandas as pd

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

def search_smart(df: pd.DataFrame, code: str, prefer: Optional[str] = None, prefix: bool = False) -> pd.DataFrame:
    variants = code_variants(code)
    # costruisci priorità
    order = SEARCH_ORDER.copy()
    if prefer:
        order.sort(key=lambda x: 0 if x[0] == prefer else 1)

    # 1) match esatto (norm/strip/raw)
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

    # 2) se non trovato, prefix search
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

    # 3) fallback: famiglia gerarchica dal 2022 se il codice è un prefisso palese
    base = "CODICE_ATECO_2022__NORM" if "CODICE_ATECO_2022__NORM" in df.columns else "CODICE_ATECO_2022"
    ser = df[base].astype(str)
    m = False
    for v in variants:
        m = m | ser.str.startswith(v)
    return df[m]

# ----------------------- Output helpers --------------------------------------
HUMAN_KEYS = [
    "CODICE_ATECO_2022", "TITOLO_ATECO_2022", "GERARCHIA_ATECO_2022",
    "CODICE_ATECO_2025_RAPPRESENTATIVO", "TITOLO_ATECO_2025_RAPPRESENTATIVO",
    "CODICE_ATECO_2025_RAPPRESENTATIVO_SISTEMA_CAMERALE",
    "TITOLO_ATECO_2025_RAPPRESENTATIVO_SISTEMA_CAMERALE",
]

def flatten(row: pd.Series) -> Dict[str, Optional[str]]:
    data: Dict[str, Optional[str]] = {}
    for k, v in row.items():
        if k.endswith("__NORM") or k.endswith("__STRIP"):
            continue
        data[k] = None if pd.isna(v) else v
    return data

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

    # Se non è una ricerca per prefisso, consideriamo solo il 1° match (più naturale per codice esatto)
    if not args.prefix:
        res = res.head(1)

    items = [flatten(r) for _, r in res.iterrows()]

    if args.pretty:
        # Scegli la coppia codice/titolo corretta in base alla colonna matchata
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
                # scegli la prima coppia completa
                code_out, title_out = it[ccol], it[tcol]
                break
        # fallback se necessario
        code_out = code_out or it.get("CODICE_ATECO_2022") or it.get("CODICE_ATECO_2025_RAPPRESENTATIVO") or ""
        title_out = title_out or it.get("TITOLO_ATECO_2022") or it.get("TITOLO_ATECO_2025_RAPPRESENTATIVO") or it.get("TITOLO_ATECO_2025_RAPPRESENTATIVO_SISTEMA_CAMERALE") or ""
        print(f"{code_out} — {title_out}")
        return

    # JSON “pulito” unico
    print(json.dumps({"found": len(items), "items": items}, ensure_ascii=False, indent=2))


def build_api(df: pd.DataFrame):
    from fastapi import FastAPI, Query
    from fastapi.responses import JSONResponse

    app = FastAPI(title="ATECO Lookup", version="1.0")

    @app.get("/health")
    def health():
        return {"status": "ok"}

    @app.get("/lookup")
    def lookup(code: str = Query(..., description="Codice ATECO"),
               prefer: Optional[str] = Query(None, description="priorità: 2022 | 2025 | 2025-camerale"),
               prefix: bool = Query(False, description="ricerca per prefisso"),
               limit: int = Query(50)):
        res = search_smart(df, code, prefer=prefer, prefix=prefix)
        if res.empty:
            return JSONResponse({"found": 0, "items": []})
        if prefix:
            res = res.head(limit)
        items = [flatten(r) for _, r in res.iterrows()]
        return JSONResponse({"found": len(items), "items": items})

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
        # Avvio API
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
