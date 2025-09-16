#!/usr/bin/env python3
"""
Main API per Railway - Versione standalone senza dipendenze locali
"""

import os
import json
import logging
import tempfile
import re
from pathlib import Path
from typing import Dict, List, Optional, Union
from difflib import get_close_matches

# FastAPI imports
from fastapi import FastAPI, Query, HTTPException, UploadFile, File
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# Data processing
import pandas as pd
import yaml

# Configurazione logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# ============= FUNZIONI HELPER DA ATECO_LOOKUP =============

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
    variants = {c, "".join(parts)}
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

ALIASES = {
    "ORDINE_CODICE_ATECO_2022": ["ORDINE_CODICE_ATECO_2022", "ORDINE_CODICE"],
    "CODICE_ATECO_2022": ["CODICE_ATECO_2022", "CODICE ATECO 2022", "CODICE_ATECO"],
    "TITOLO_ATECO_2022": ["TITOLO_ATECO_2022", "TITOLO ATECO 2022", "TITOLO_2022", "TITOLO_ATECO"],
    "CODICE_ATECO_2025_RAPPRESENTATIVO": ["CODICE_ATECO_2025_RAPPRESENTATIVO", "CODICE ATECO 2025 RAPPRESENTATIVO"],
    "TITOLO_ATECO_2025_RAPPRESENTATIVO": ["TITOLO_ATECO_2025_RAPPRESENTATIVO", "TITOLO ATECO 2025 RAPPRESENTATIVO"],
    "CODICE_ATECO_2025_RAPPRESENTATIVO_SISTEMA_CAMERALE": ["CODICE_ATECO_2025_RAPPRESENTATIVO_SISTEMA_CAMERALE", "CODICE 2025 SISTEMA CAMERALE"],
    "TITOLO_ATECO_2025_RAPPRESENTATIVO_SISTEMA_CAMERALE": ["TITOLO_ATECO_2025_RAPPRESENTATIVO_SISTEMA_CAMERALE", "TITOLO 2025 SISTEMA CAMERALE"],
}
HEADER_RESOLVE: Dict[str, str] = {opt.lower(): std for std, lst in ALIASES.items() for opt in lst}

def normalize_headers(df: pd.DataFrame) -> pd.DataFrame:
    mapping: Dict[str, str] = {}
    for col in df.columns:
        mapping[col] = HEADER_RESOLVE.get(str(col).strip().lower(), col)
    return df.rename(columns=mapping)

def load_dataset(path: Path, debug: bool = False) -> pd.DataFrame:
    if not path.exists():
        raise FileNotFoundError(f"File non trovato: {path}")
    xls = pd.ExcelFile(path)
    sheet_to_use = xls.sheet_names[0]
    for s in ["Tabella operativa", "tabella operativa", "Foglio1", "Sheet1"]:
        if s in xls.sheet_names:
            sheet_to_use = s
            break
    df = pd.read_excel(xls, sheet_name=sheet_to_use, dtype=str)
    df = normalize_headers(df)
    for key in ["CODICE_ATECO_2022", "CODICE_ATECO_2025_RAPPRESENTATIVO", "CODICE_ATECO_2025_RAPPRESENTATIVO_SISTEMA_CAMERALE"]:
        if key in df.columns:
            df[key + "__NORM"] = df[key].apply(normalize_code)
            df[key + "__STRIP"] = df[key].apply(strip_code)
    return df

SEARCH_ORDER = [
    ("2022", "CODICE_ATECO_2022"),
    ("2025", "CODICE_ATECO_2025_RAPPRESENTATIVO"),
    ("2025-camerale", "CODICE_ATECO_2025_RAPPRESENTATIVO_SISTEMA_CAMERALE"),
]

def search_smart(df: pd.DataFrame, code: str, prefer: Optional[str] = None, prefix: bool = False) -> pd.DataFrame:
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
    code_norm = normalize_code(code)
    all_codes = df["CODICE_ATECO_2022"].dropna().unique()
    all_codes_norm = [normalize_code(c) for c in all_codes]
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

def flatten(row: pd.Series) -> Dict[str, Optional[str]]:
    data: Dict[str, Optional[str]] = {}
    for k, v in row.items():
        if k.endswith("__NORM") or k.endswith("__STRIP"):
            continue
        data[k] = None if pd.isna(v) else v
    return data

def enrich(item: dict) -> dict:
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

    item["settore"] = settore or "non mappato"
    item["normative"] = []
    item["certificazioni"] = []

    # Carica mapping se esiste
    if Path("mapping.yaml").exists():
        try:
            with open("mapping.yaml", "r", encoding="utf-8") as f:
                mapping = yaml.safe_load(f) or {}
            if settore and settore in mapping.get("settori", {}):
                item["normative"] = mapping["settori"][settore].get("normative", [])
                item["certificazioni"] = mapping["settori"][settore].get("certificazioni", [])
        except:
            pass

    return item

# ============= INIZIALIZZAZIONE APP =============

app = FastAPI(
    title="Celerya Cyber ATECO API",
    version="3.0",
    description="API unificate per ATECO lookup e Risk Management"
)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"]
)

# Middleware per gestione errori
@app.middleware("http")
async def catch_exceptions_middleware(request, call_next):
    try:
        response = await call_next(request)
        return response
    except Exception as e:
        logger.error(f"Errore non gestito: {str(e)}", exc_info=True)
        return JSONResponse(
            status_code=500,
            content={"error": "Internal server error", "message": str(e)},
            headers={"Access-Control-Allow-Origin": "*"}
        )

# ============= CARICAMENTO DATI =============

# Carica dataset ATECO
df = None
ATECO_FILE = None
for name in ["tabella_ATECO.xlsx", "Tabella_ATECO.xlsx", "TABELLA_ATECO.xlsx", "tabella_ateco.xlsx"]:
    if Path(name).exists():
        ATECO_FILE = Path(name)
        break

if ATECO_FILE:
    try:
        logger.info(f"Caricamento dataset ATECO da {ATECO_FILE}")
        df = load_dataset(ATECO_FILE)
        logger.info(f"Dataset caricato: {len(df)} righe")
    except Exception as e:
        logger.error(f"Errore caricamento ATECO: {e}")
        df = None
else:
    logger.warning("File ATECO non trovato")

# Carica mappature Risk Management
EXCEL_CATEGORIES = {}
EXCEL_DESCRIPTIONS = {}
if Path("MAPPATURE_EXCEL_PERFETTE.json").exists():
    try:
        with open("MAPPATURE_EXCEL_PERFETTE.json", 'r', encoding='utf-8') as f:
            risk_data = json.load(f)
            EXCEL_CATEGORIES = risk_data.get('mappature_categoria_eventi', {})
            EXCEL_DESCRIPTIONS = risk_data.get('vlookup_map', {})
        logger.info(f"Mappature Risk caricate: {len(EXCEL_CATEGORIES)} categorie")
    except Exception as e:
        logger.error(f"Errore caricamento mappature: {e}")

# ============= ENDPOINTS =============

@app.get("/")
def root():
    return {
        "service": "Celerya Cyber ATECO API",
        "version": "3.0",
        "status": "online",
        "ateco_loaded": df is not None,
        "risk_loaded": len(EXCEL_CATEGORIES) > 0
    }

@app.get("/health")
def health():
    return {"status": "healthy"}

# ATECO Endpoints
class BatchRequest(BaseModel):
    codes: List[str]
    prefer: Optional[str] = None
    prefix: bool = False

@app.get("/lookup")
def lookup(
    code: str = Query(..., description="Codice ATECO"),
    prefer: Optional[str] = Query(None),
    prefix: bool = Query(False),
    limit: int = Query(50)
):
    if df is None:
        raise HTTPException(status_code=503, detail="Dataset ATECO non caricato")

    if not code or len(code) < 2:
        raise HTTPException(status_code=400, detail="Codice troppo corto")

    res = search_smart(df, code, prefer=prefer, prefix=prefix)

    if res.empty:
        suggestions = find_similar_codes(df, code)
        return {"found": 0, "items": [], "suggestions": suggestions}

    if prefix:
        res = res.head(limit)
    items = [enrich(flatten(r)) for _, r in res.iterrows()]
    return {"found": len(items), "items": items}

@app.post("/batch")
def batch_lookup(request: BatchRequest):
    if df is None:
        raise HTTPException(status_code=503, detail="Dataset ATECO non caricato")

    results = []
    for code in request.codes[:50]:
        res = search_smart(df, code, prefer=request.prefer, prefix=request.prefix)
        if res.empty:
            results.append({"code": code, "found": 0, "items": []})
        else:
            items = [enrich(flatten(r)) for _, r in res.head(1).iterrows()]
            results.append({"code": code, "found": len(items), "items": items})

    return {"total_codes": len(request.codes), "results": results}

@app.get("/autocomplete")
def autocomplete(partial: str = Query(..., min_length=2), limit: int = Query(5, le=20)):
    if df is None:
        raise HTTPException(status_code=503, detail="Dataset non caricato")

    partial_norm = normalize_code(partial)
    suggestions = []
    seen = set()

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

    return {"partial": partial, "suggestions": suggestions, "count": len(suggestions)}

# Risk Management Endpoints
@app.get("/categories")
def get_categories():
    return {"categories": list(EXCEL_CATEGORIES.keys()), "total": len(EXCEL_CATEGORIES)}

@app.get("/events/{category}")
def get_events(category: str):
    category_mapping = {
        "operational": "Execution_delivery_Problemi_di_produzione_o_consegna",
        "cyber": "Business_disruption",
        "compliance": "Clients_product_Clienti",
        "financial": "Internal_Fraud_Frodi_interne",
        "damage": "Damage_Danni",
        "employment": "Employment_practices_Dipendenti",
        "external_fraud": "External_fraud_Frodi_esterne"
    }

    real_category = category
    if category.lower() in category_mapping:
        real_category = category_mapping[category.lower()]

    if real_category not in EXCEL_CATEGORIES:
        for cat in EXCEL_CATEGORIES:
            if category.lower() in cat.lower():
                real_category = cat
                break

    if real_category not in EXCEL_CATEGORIES:
        return JSONResponse({"error": f"Category '{category}' not found"}, status_code=404)

    events = []
    for event_str in EXCEL_CATEGORIES[real_category]:
        parts = event_str.split(' - ', 1)
        if len(parts) == 2:
            code = parts[0].strip()
            name = parts[1].strip()
            severity = 'medium'
            if code.startswith('2') or code.startswith('5'):
                severity = 'high'
            elif code.startswith('3'):
                severity = 'low'
            elif code.startswith(('6', '7')):
                severity = 'critical'
            events.append({"code": code, "name": name, "severity": severity})

    return {"category": real_category, "events": events, "total": len(events)}

@app.get("/description/{event_code}")
def get_event_description(event_code: str):
    if '[object' in event_code.lower() or '{' in event_code:
        numbers = re.findall(r'\d+', event_code)
        if numbers:
            event_code = numbers[0]
        else:
            return JSONResponse({"error": "Invalid event code"}, status_code=400)

    event_code = event_code.strip()
    event_name = None
    category_found = None

    for cat_name, cat_events in EXCEL_CATEGORIES.items():
        for event in cat_events:
            if event.startswith(event_code + ' - '):
                event_name = event.split(' - ', 1)[1]
                category_found = cat_name
                break
        if event_name:
            break

    vlookup_description = EXCEL_DESCRIPTIONS.get(event_code)

    if event_name:
        final_description = vlookup_description if vlookup_description else event_name

        if event_code.startswith('1'):
            impact = "Danni fisici e materiali"
            probability = "low"
            controls = ["Assicurazione danni", "Manutenzione preventiva"]
        elif event_code.startswith('2'):
            impact = "Interruzione operativa"
            probability = "medium"
            controls = ["Backup e recovery", "Ridondanza sistemi"]
        elif event_code.startswith('3'):
            impact = "Problemi con dipendenti"
            probability = "medium"
            controls = ["HR policies", "Formazione continua"]
        elif event_code.startswith('4'):
            impact = "Errori di processo"
            probability = "high"
            controls = ["Quality control", "Process automation"]
        elif event_code.startswith('5'):
            impact = "Perdita clienti"
            probability = "medium"
            controls = ["Customer satisfaction", "Compliance monitoring"]
        elif event_code.startswith('6'):
            impact = "Frodi interne"
            probability = "low"
            controls = ["Audit interni", "Segregation of duties"]
        elif event_code.startswith('7'):
            impact = "Frodi esterne"
            probability = "medium"
            controls = ["Cybersecurity", "Fraud detection"]
        else:
            impact = "Da valutare"
            probability = "unknown"
            controls = ["Da definire"]

        return {
            "code": event_code,
            "name": event_name,
            "description": final_description,
            "category": category_found,
            "impact": impact,
            "probability": probability,
            "controls": controls
        }

    return {
        "code": event_code,
        "name": "Evento non mappato",
        "description": f"Evento {event_code} non presente",
        "impact": "Da valutare",
        "probability": "unknown",
        "controls": ["Da definire"]
    }

# Risk Assessment Endpoints
@app.get("/risk-assessment-fields")
def get_risk_assessment_fields():
    return {
        "fields": [
            {
                "id": "impatto_finanziario",
                "question": "Qual è l'impatto finanziario stimato?",
                "type": "select",
                "options": ["N/A", "0 - 1K€", "1 - 10K€", "10 - 50K€", "50 - 100K€", "100 - 500K€", "500K€ - 1M€", "1 - 3M€", "3 - 5M€"],
                "required": True
            },
            {
                "id": "perdita_economica",
                "question": "Qual è il livello di perdita economica attesa?",
                "type": "select_color",
                "options": [
                    {"value": "G", "label": "Bassa/Nulla", "color": "green"},
                    {"value": "Y", "label": "Media", "color": "yellow"},
                    {"value": "O", "label": "Importante", "color": "orange"},
                    {"value": "R", "label": "Grave", "color": "red"}
                ],
                "required": True
            },
            {
                "id": "impatto_immagine",
                "question": "L'evento ha impatto sull'immagine aziendale?",
                "type": "boolean",
                "options": ["Si", "No"],
                "required": True
            },
            {
                "id": "impatto_regolamentare",
                "question": "Ci sono possibili conseguenze regolamentari?",
                "type": "boolean",
                "options": ["Si", "No"],
                "required": True
            },
            {
                "id": "impatto_criminale",
                "question": "Ci sono possibili conseguenze penali?",
                "type": "boolean",
                "options": ["Si", "No"],
                "required": True
            }
        ]
    }

@app.post("/save-risk-assessment")
def save_risk_assessment(data: dict):
    try:
        score = 0
        impatto_map = {'N/A': 0, '0 - 1K€': 5, '1 - 10K€': 10, '10 - 50K€': 15, '50 - 100K€': 20, '100 - 500K€': 25, '500K€ - 1M€': 30, '1 - 3M€': 35, '3 - 5M€': 40}
        score += impatto_map.get(data.get('impatto_finanziario', 'N/A'), 0)

        perdita_map = {'G': 5, 'Y': 15, 'O': 25, 'R': 30}
        score += perdita_map.get(data.get('perdita_economica', 'G'), 0)

        if data.get('impatto_immagine') == 'Si': score += 10
        if data.get('impatto_regolamentare') == 'Si': score += 10
        if data.get('impatto_criminale') == 'Si': score += 10

        if score >= 70:
            level = "CRITICO"
        elif score >= 50:
            level = "ALTO"
        elif score >= 30:
            level = "MEDIO"
        else:
            level = "BASSO"

        return {"status": "success", "risk_score": score, "level": level}
    except Exception as e:
        logger.error(f"Errore: {e}")
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/calculate-risk-assessment")
def calculate_risk_assessment(data: dict):
    try:
        color_to_value = {'G': 4, 'Y': 3, 'O': 2, 'R': 1}
        economic_value = color_to_value.get(data.get('economic_loss', 'G'), 4)
        non_economic_value = color_to_value.get(data.get('non_economic_loss', 'G'), 4)
        inherent_risk = min(economic_value, non_economic_value)

        control_to_row = {'--': 1, '-': 2, '+': 3, '++': 4}
        control_level = data.get('control_level', '+')
        row = control_to_row.get(control_level, 3)

        column_map = {4: 'A', 3: 'B', 2: 'C', 1: 'D'}
        column = column_map.get(inherent_risk, 'B')
        matrix_position = f"{column}{row}"

        risk_levels = {
            'A4': 'Low', 'A3': 'Low', 'B4': 'Low',
            'A2': 'Medium', 'B3': 'Medium', 'C4': 'Medium',
            'A1': 'High', 'B2': 'High', 'C3': 'High', 'D4': 'High',
            'B1': 'Critical', 'C2': 'Critical', 'D3': 'Critical',
            'C1': 'Critical', 'D2': 'Critical', 'D1': 'Critical'
        }

        return {
            'status': 'success',
            'matrix_position': matrix_position,
            'risk_level': risk_levels.get(matrix_position, 'Medium')
        }
    except Exception as e:
        logger.error(f"Errore: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Visura Extraction
@app.post("/api/extract-visura")
async def extract_visura(file: UploadFile = File(...)):
    logger.info(f"Ricevuto file: {file.filename}")
    result = {
        'success': True,
        'data': {'partita_iva': None, 'codice_ateco': None, 'oggetto_sociale': None}
    }

    tmp_path = None
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as tmp:
            content = await file.read()
            if not content:
                return JSONResponse(result)
            tmp.write(content)
            tmp_path = tmp.name

        text = ""
        try:
            import pdfplumber
            with pdfplumber.open(tmp_path) as pdf:
                for page in pdf.pages:
                    page_text = page.extract_text()
                    if page_text:
                        text += page_text + "\n"
        except:
            try:
                import PyPDF2
                with open(tmp_path, 'rb') as pdf_file:
                    pdf_reader = PyPDF2.PdfReader(pdf_file)
                    for page in pdf_reader.pages:
                        text += page.extract_text() + "\n"
            except:
                return JSONResponse(result)

        # Estrai P.IVA
        piva_patterns = [r'(?:Partita IVA|P\.?\s?IVA)[\s:]+(\d{11})', r'\b(\d{11})\b']
        for pattern in piva_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                piva = match.group(1)
                if re.match(r'^\d{11}$', piva):
                    result['data']['partita_iva'] = piva
                    break

        # Estrai ATECO
        ateco_patterns = [r'(?:Codice ATECO|ATECO)[\s:]+(\d{2}[.\s]\d{2}(?:[.\s]\d{1,2})?)', r'\b(\d{2}\.\d{2}(?:\.\d{1,2})?)\b']
        for pattern in ateco_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                ateco = re.sub(r'\s+', '.', match.group(1))
                if re.match(r'^\d{2}\.\d{2}(?:\.\d{1,2})?$', ateco):
                    result['data']['codice_ateco'] = ateco
                    break

    except Exception as e:
        logger.error(f"Errore: {e}")
    finally:
        if tmp_path:
            try:
                os.unlink(tmp_path)
            except:
                pass

    return JSONResponse(result)

# Entry point
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    logger.info(f"Starting server on port {port}")

    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=port)