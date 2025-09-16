#!/usr/bin/env python3
"""
Main API unificato per Railway
Combina ateco_lookup.py e gli endpoint di test_server.py
"""

from __future__ import annotations
import os
import json
import logging
from pathlib import Path
from typing import Dict, List, Optional
import tempfile

# FastAPI imports
from fastapi import FastAPI, Query, HTTPException, UploadFile, File
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# Import funzioni da ateco_lookup
from ateco_lookup import (
    load_dataset,
    search_smart,
    flatten,
    enrich,
    find_similar_codes,
    normalize_code,
    MAPPING
)

# Configurazione logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Inizializza FastAPI
app = FastAPI(
    title="Celerya Cyber ATECO API",
    version="3.0",
    description="API unificate per ATECO lookup e Risk Management"
)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In produzione sostituire con dominio specifico
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"]
)

# Middleware per gestione errori con CORS
@app.middleware("http")
async def catch_exceptions_middleware(request, call_next):
    try:
        response = await call_next(request)
        return response
    except Exception as e:
        logger.error(f"Errore non gestito: {str(e)}", exc_info=True)
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

# Carica dataset ATECO
ATECO_FILE = Path("tabella_ATECO.xlsx")
if not ATECO_FILE.exists():
    # Prova altri nomi comuni
    for name in ["Tabella_ATECO.xlsx", "TABELLA_ATECO.xlsx", "tabella_ateco.xlsx"]:
        if Path(name).exists():
            ATECO_FILE = Path(name)
            break

if ATECO_FILE.exists():
    logger.info(f"Caricamento dataset ATECO da {ATECO_FILE}")
    df = load_dataset(ATECO_FILE)
    logger.info(f"Dataset caricato: {len(df)} righe")
else:
    logger.warning("File ATECO non trovato - alcuni endpoint non funzioneranno")
    df = None

# Carica mappature Excel per Risk Management
MAPPATURE_FILE = Path("MAPPATURE_EXCEL_PERFETTE.json")
if MAPPATURE_FILE.exists():
    with open(MAPPATURE_FILE, 'r', encoding='utf-8') as f:
        risk_data = json.load(f)
        EXCEL_CATEGORIES = risk_data.get('mappature_categoria_eventi', {})
        EXCEL_DESCRIPTIONS = risk_data.get('vlookup_map', {})
    logger.info(f"Mappature Risk caricate: {len(EXCEL_CATEGORIES)} categorie")
else:
    logger.warning("File mappature non trovato - endpoint Risk limitati")
    EXCEL_CATEGORIES = {}
    EXCEL_DESCRIPTIONS = {}

# ============= HEALTH CHECK =============
@app.get("/")
def root():
    return {
        "service": "Celerya Cyber ATECO API",
        "version": "3.0",
        "status": "online",
        "endpoints": {
            "ateco": "/lookup, /batch, /autocomplete",
            "risk": "/categories, /events/{category}, /description/{event_code}",
            "assessment": "/risk-assessment-fields, /save-risk-assessment, /calculate-risk-assessment",
            "visura": "/api/extract-visura"
        }
    }

@app.get("/health")
def health():
    return {
        "status": "healthy",
        "ateco_loaded": df is not None,
        "risk_loaded": len(EXCEL_CATEGORIES) > 0
    }

# ============= ATECO ENDPOINTS =============
class BatchRequest(BaseModel):
    codes: List[str]
    prefer: Optional[str] = None
    prefix: bool = False

@app.get("/lookup")
def lookup(
    code: str = Query(..., description="Codice ATECO"),
    prefer: Optional[str] = Query(None, description="priorità: 2022 | 2025 | 2025-camerale"),
    prefix: bool = Query(False, description="ricerca per prefisso"),
    limit: int = Query(50)
):
    if df is None:
        raise HTTPException(status_code=503, detail="Dataset ATECO non caricato")

    if not code or len(code) < 2:
        raise HTTPException(
            status_code=400,
            detail={"error": "INVALID_CODE", "message": "Codice troppo corto"}
        )

    res = search_smart(df, code, prefer=prefer, prefix=prefix)

    if res.empty:
        suggestions = find_similar_codes(df, code)
        return {
            "found": 0,
            "items": [],
            "suggestions": suggestions,
            "message": f"Nessun risultato per '{code}'"
        }

    if prefix:
        res = res.head(limit)
    items = [enrich(flatten(r)) for _, r in res.iterrows()]
    return {"found": len(items), "items": items}

@app.post("/batch")
def batch_lookup(request: BatchRequest):
    if df is None:
        raise HTTPException(status_code=503, detail="Dataset ATECO non caricato")

    if len(request.codes) > 50:
        raise HTTPException(
            status_code=400,
            detail={"error": "TOO_MANY_CODES", "message": "Massimo 50 codici"}
        )

    results = []
    for code in request.codes:
        res = search_smart(df, code, prefer=request.prefer, prefix=request.prefix)
        if res.empty:
            results.append({"code": code, "found": 0, "items": []})
        else:
            items = [enrich(flatten(r)) for _, r in res.head(1).iterrows()]
            results.append({"code": code, "found": len(items), "items": items})

    return {"total_codes": len(request.codes), "results": results}

@app.get("/autocomplete")
def autocomplete(
    partial: str = Query(..., min_length=2),
    limit: int = Query(5, le=20)
):
    if df is None:
        raise HTTPException(status_code=503, detail="Dataset ATECO non caricato")

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

    return {
        "partial": partial,
        "suggestions": suggestions[:limit],
        "count": len(suggestions[:limit])
    }

# ============= RISK MANAGEMENT ENDPOINTS =============
@app.get("/categories")
def get_categories():
    """Ottieni tutte le categorie di rischio disponibili"""
    return {
        "categories": list(EXCEL_CATEGORIES.keys()),
        "total": len(EXCEL_CATEGORIES)
    }

@app.get("/events/{category}")
def get_events(category: str):
    """Eventi di rischio per categoria"""
    # Mapping alias
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
        # Prova match parziale
        for cat in EXCEL_CATEGORIES:
            if category.lower() in cat.lower():
                real_category = cat
                break

    if real_category not in EXCEL_CATEGORIES:
        return JSONResponse({
            "error": f"Category '{category}' not found",
            "available_categories": list(EXCEL_CATEGORIES.keys())
        }, status_code=404)

    # Converti eventi in formato frontend
    events = []
    for event_str in EXCEL_CATEGORIES[real_category]:
        parts = event_str.split(' - ', 1)
        if len(parts) == 2:
            code = parts[0].strip()
            name = parts[1].strip()

            # Determina severity
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
            elif code.startswith(('6', '7')):
                severity = 'critical'
            else:
                severity = 'medium'

            events.append({
                "code": code,
                "name": name,
                "severity": severity
            })

    return {
        "category": real_category,
        "events": events,
        "total": len(events)
    }

@app.get("/description/{event_code}")
def get_event_description(event_code: str):
    """Descrizione dettagliata di un evento"""
    import re

    # Pulisci event_code
    if '[object' in event_code.lower() or '{' in event_code:
        numbers = re.findall(r'\d+', event_code)
        if numbers:
            event_code = numbers[0]
        else:
            return JSONResponse({
                "error": "Invalid event code format",
                "received": event_code
            }, status_code=400)

    event_code = event_code.strip()

    # Cerca nelle categorie
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

    # Cerca descrizione VLOOKUP
    vlookup_description = EXCEL_DESCRIPTIONS.get(event_code)

    if event_name:
        final_description = vlookup_description if vlookup_description else event_name

        # Determina impatto e controlli
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

        return {
            "code": event_code,
            "name": event_name,
            "description": final_description,
            "category": category_found,
            "impact": impact,
            "probability": probability,
            "controls": controls,
            "source": "Excel Risk Mapping"
        }

    return {
        "code": event_code,
        "name": "Evento non mappato",
        "description": f"Evento {event_code} non presente nel mapping",
        "impact": "Da valutare",
        "probability": "unknown",
        "controls": ["Da definire"],
        "source": "Generic"
    }

# ============= RISK ASSESSMENT ENDPOINTS =============
@app.get("/risk-assessment-fields")
def get_risk_assessment_fields():
    """Struttura dei campi di valutazione rischio"""
    return {
        "fields": [
            {
                "id": "impatto_finanziario",
                "column": "H",
                "question": "Qual è l'impatto finanziario stimato?",
                "type": "select",
                "options": [
                    "N/A", "0 - 1K€", "1 - 10K€", "10 - 50K€",
                    "50 - 100K€", "100 - 500K€", "500K€ - 1M€",
                    "1 - 3M€", "3 - 5M€"
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
                "required": True
            },
            {
                "id": "impatto_criminale",
                "column": "M",
                "question": "Ci sono possibili conseguenze penali?",
                "type": "boolean",
                "options": ["Si", "No"],
                "required": True
            },
            {
                "id": "perdita_non_economica",
                "column": "V",
                "question": "Qual è il livello di perdita non economica?",
                "type": "select_color",
                "options": [
                    {"value": "G", "label": "Bassa/Nulla", "color": "green", "emoji": "🟢"},
                    {"value": "Y", "label": "Media", "color": "yellow", "emoji": "🟡"},
                    {"value": "O", "label": "Importante", "color": "orange", "emoji": "🟠"},
                    {"value": "R", "label": "Grave", "color": "red", "emoji": "🔴"}
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
                "required": False
            }
        ]
    }

@app.post("/save-risk-assessment")
def save_risk_assessment(data: dict):
    """Salva valutazione rischio e calcola score"""
    try:
        score = 0

        # Impatto finanziario
        impatto_map = {
            'N/A': 0, '0 - 1K€': 5, '1 - 10K€': 10, '10 - 50K€': 15,
            '50 - 100K€': 20, '100 - 500K€': 25, '500K€ - 1M€': 30,
            '1 - 3M€': 35, '3 - 5M€': 40
        }
        score += impatto_map.get(data.get('impatto_finanziario', 'N/A'), 0)

        # Perdita economica
        perdita_map = {'G': 5, 'Y': 15, 'O': 25, 'R': 30}
        score += perdita_map.get(data.get('perdita_economica', 'G'), 0)

        # Impatti booleani
        if data.get('impatto_immagine') == 'Si': score += 10
        if data.get('impatto_regolamentare') == 'Si': score += 10
        if data.get('impatto_criminale') == 'Si': score += 10

        # Controllo
        controllo_multiplier = {
            '++': 0.5, '+': 0.75, '-': 1.25, '--': 1.5
        }
        controllo = data.get('controllo', '+')
        if controllo in controllo_multiplier:
            score = int(score * controllo_multiplier[controllo])

        # Analisi
        if score >= 70:
            level = "CRITICO"
            action = "Richiede azione immediata"
        elif score >= 50:
            level = "ALTO"
            action = "Priorità alta"
        elif score >= 30:
            level = "MEDIO"
            action = "Monitorare"
        else:
            level = "BASSO"
            action = "Rischio accettabile"

        return {
            "status": "success",
            "risk_score": score,
            "analysis": f"Livello: {level} (Score: {score}/100). {action}"
        }

    except Exception as e:
        logger.error(f"Errore in save_risk_assessment: {e}")
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/calculate-risk-assessment")
def calculate_risk_assessment(data: dict):
    """Calcola posizione nella matrice di rischio"""
    try:
        color_to_value = {'G': 4, 'Y': 3, 'O': 2, 'R': 1}

        economic_value = color_to_value.get(data.get('economic_loss', 'G'), 4)
        non_economic_value = color_to_value.get(data.get('non_economic_loss', 'G'), 4)

        inherent_risk = min(economic_value, non_economic_value)

        control_to_row = {
            '--': 1, '-': 2, '+': 3, '++': 4
        }

        control_level = data.get('control_level', '+')
        row = control_to_row.get(control_level, 3)

        column_map = {4: 'A', 3: 'B', 2: 'C', 1: 'D'}
        column = column_map.get(inherent_risk, 'B')

        matrix_position = f"{column}{row}"

        risk_levels = {
            'A4': {'level': 'Low', 'color': 'green'},
            'A3': {'level': 'Low', 'color': 'green'},
            'B4': {'level': 'Low', 'color': 'green'},
            'A2': {'level': 'Medium', 'color': 'yellow'},
            'B3': {'level': 'Medium', 'color': 'yellow'},
            'C4': {'level': 'Medium', 'color': 'yellow'},
            'A1': {'level': 'High', 'color': 'orange'},
            'B2': {'level': 'High', 'color': 'orange'},
            'C3': {'level': 'High', 'color': 'orange'},
            'D4': {'level': 'High', 'color': 'orange'},
            'B1': {'level': 'Critical', 'color': 'red'},
            'C2': {'level': 'Critical', 'color': 'red'},
            'D3': {'level': 'Critical', 'color': 'red'},
            'C1': {'level': 'Critical', 'color': 'red'},
            'D2': {'level': 'Critical', 'color': 'red'},
            'D1': {'level': 'Critical', 'color': 'red'}
        }

        risk_info = risk_levels.get(matrix_position, {'level': 'Medium', 'color': 'yellow'})

        return {
            'status': 'success',
            'matrix_position': matrix_position,
            'risk_level': risk_info['level'],
            'risk_color': risk_info['color'],
            'inherent_risk': {
                'value': inherent_risk,
                'label': {4: 'Low', 3: 'Medium', 2: 'High', 1: 'Critical'}[inherent_risk]
            },
            'control_effectiveness': {
                'value': row,
                'label': control_level
            }
        }

    except Exception as e:
        logger.error(f"Errore calculate_risk_assessment: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# ============= VISURA EXTRACTION ENDPOINT =============
@app.post("/api/extract-visura")
async def extract_visura(file: UploadFile = File(...)):
    """Estrazione dati da visura PDF"""
    logger.info(f"Ricevuto file: {file.filename}")

    result = {
        'success': True,
        'data': {
            'partita_iva': None,
            'codice_ateco': None,
            'oggetto_sociale': None,
            'codici_ateco': [],
            'confidence': {'score': 0, 'details': {}}
        },
        'method': 'backend'
    }

    tmp_path = None
    try:
        # Salva file temporaneo
        with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as tmp:
            content = await file.read()
            if not content:
                return JSONResponse(result)
            tmp.write(content)
            tmp_path = tmp.name

        # Estrai testo
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

        if not text:
            return JSONResponse(result)

        import re

        # Estrai P.IVA
        piva_patterns = [
            r'(?:Partita IVA|P\.?\s?IVA|VAT)[\s:]+(\d{11})',
            r'(?:Codice Fiscale|C\.F\.)[\s:]+(\d{11})',
            r'\b(\d{11})\b'
        ]
        for pattern in piva_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                piva = match.group(1)
                if re.match(r'^\d{11}$', piva):
                    result['data']['partita_iva'] = piva
                    result['data']['confidence']['score'] += 33
                    break

        # Estrai ATECO
        ateco_patterns = [
            r'(?:Codice ATECO|ATECO|Attività prevalente)[\s:]+(\d{2}[.\s]\d{2}(?:[.\s]\d{1,2})?)',
            r'\b(\d{2}\.\d{2}(?:\.\d{1,2})?)\b'
        ]
        for pattern in ateco_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                ateco = re.sub(r'\s+', '.', match.group(1))
                if re.match(r'^\d{2}\.\d{2}(?:\.\d{1,2})?$', ateco):
                    first_part = int(ateco.split('.')[0])
                    if first_part not in [19, 20, 21]:
                        result['data']['codice_ateco'] = ateco
                        result['data']['codici_ateco'] = [{
                            'codice': ateco,
                            'descrizione': '',
                            'principale': True
                        }]
                        result['data']['confidence']['score'] += 33
                        break

        # Estrai Oggetto Sociale
        oggetto_patterns = [
            r'(?:OGGETTO SOCIALE|Oggetto sociale|Oggetto)[\s:]+([^\n]{30,})',
            r'(?:Attività|ATTIVITA)[\s:]+([^\n]{30,})'
        ]
        business_words = ['produzione', 'commercio', 'servizi', 'consulenza',
                         'vendita', 'gestione', 'prestazione', 'attività']
        for pattern in oggetto_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                oggetto = match.group(1).strip()
                if len(oggetto) >= 30:
                    if any(w in oggetto.lower() for w in business_words):
                        if len(oggetto) > 500:
                            oggetto = oggetto[:500] + '...'
                        result['data']['oggetto_sociale'] = oggetto
                        result['data']['confidence']['score'] += 34
                        break

    except Exception as e:
        logger.error(f"Errore estrazione: {e}")

    finally:
        if tmp_path:
            try:
                os.unlink(tmp_path)
            except:
                pass

    return JSONResponse(result)

# Entry point per Railway
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))

    # Per sviluppo locale
    if os.environ.get("ENV") != "production":
        import uvicorn
        uvicorn.run(app, host="0.0.0.0", port=port)