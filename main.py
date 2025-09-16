#!/usr/bin/env python3
"""
API Backend per Railway - VERSIONE MINIMAL TESTATA
"""
import os
import json
import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Crea app
app = FastAPI(title="Celerya API", version="1.0")

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]
)

# Carica dati Risk se esistono
EXCEL_CATEGORIES = {}
EXCEL_DESCRIPTIONS = {}
try:
    logger.info("Tentativo caricamento MAPPATURE_EXCEL_PERFETTE.json...")
    with open("MAPPATURE_EXCEL_PERFETTE.json", 'r', encoding='utf-8') as f:
        data = json.load(f)
        EXCEL_CATEGORIES = data.get('mappature_categoria_eventi', {})
        EXCEL_DESCRIPTIONS = data.get('vlookup_map', {})
    logger.info(f"Caricati {len(EXCEL_CATEGORIES)} categorie e {len(EXCEL_DESCRIPTIONS)} descrizioni")
except Exception as e:
    logger.warning(f"Impossibile caricare mappature: {e}")
    EXCEL_CATEGORIES = {}
    EXCEL_DESCRIPTIONS = {}

@app.get("/")
def root():
    return {"status": "ok", "message": "API Running"}

@app.get("/health")
def health():
    return {"status": "healthy"}

@app.get("/categories")
def categories():
    return {
        "categories": list(EXCEL_CATEGORIES.keys()),
        "total": len(EXCEL_CATEGORIES)
    }

@app.get("/events/{category}")
def events(category: str):
    if category not in EXCEL_CATEGORIES:
        return {"error": "Category not found", "available": list(EXCEL_CATEGORIES.keys())}

    events = []
    for event_str in EXCEL_CATEGORIES[category]:
        parts = event_str.split(' - ', 1)
        if len(parts) == 2:
            events.append({
                "code": parts[0].strip(),
                "name": parts[1].strip()
            })

    return {"category": category, "events": events, "total": len(events)}

@app.get("/description/{event_code}")
def description(event_code: str):
    desc = EXCEL_DESCRIPTIONS.get(event_code)
    if desc:
        return {"code": event_code, "description": desc}
    return {"code": event_code, "description": "Not found"}

# ============= RISK ASSESSMENT ENDPOINTS MANCANTI =============

@app.get("/risk-assessment-fields")
def get_risk_assessment_fields():
    """Endpoint per ottenere i campi del form di risk assessment"""
    return {
        "fields": [
            {
                "id": "impatto_finanziario",
                "column": "H",
                "question": "Qual è l'impatto finanziario stimato?",
                "type": "select",
                "options": ["N/A", "0 - 1K€", "1 - 10K€", "10 - 50K€", "50 - 100K€", "100 - 500K€", "500K€ - 1M€", "1 - 3M€", "3 - 5M€"],
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
    """Endpoint per salvare la valutazione del rischio"""
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

        # Determina livello
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
            "message": "Risk assessment salvato",
            "risk_score": score,
            "risk_level": level,
            "action": action
        }
    except Exception as e:
        logger.error(f"Errore in save_risk_assessment: {e}")
        return {"status": "error", "message": str(e)}

@app.post("/calculate-risk-assessment")
def calculate_risk_assessment(data: dict):
    """Endpoint per calcolare la matrice di rischio"""
    try:
        # Mappa colori in valori
        color_to_value = {'G': 4, 'Y': 3, 'O': 2, 'R': 1}

        economic_value = color_to_value.get(data.get('economic_loss', 'G'), 4)
        non_economic_value = color_to_value.get(data.get('non_economic_loss', 'G'), 4)

        inherent_risk = min(economic_value, non_economic_value)

        # Mappa controllo a riga
        control_to_row = {'--': 1, '-': 2, '+': 3, '++': 4}
        control_level = data.get('control_level', '+')
        row = control_to_row.get(control_level, 3)

        # Calcola colonna
        column_map = {4: 'A', 3: 'B', 2: 'C', 1: 'D'}
        column = column_map.get(inherent_risk, 'B')

        matrix_position = f"{column}{row}"

        # Determina livello di rischio
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
            'inherent_risk': inherent_risk,
            'control_effectiveness': row
        }
    except Exception as e:
        logger.error(f"Errore in calculate_risk_assessment: {e}")
        return {"status": "error", "message": str(e)}

# ============= VISURA EXTRACTION ENDPOINT =============

from fastapi import UploadFile, File
import tempfile

@app.post("/api/extract-visura")
async def extract_visura(file: UploadFile = File(...)):
    """Estrazione dati da PDF visura - versione mock per ora"""
    logger.info(f"Ricevuto file visura: {file.filename}")

    # Per ora ritorna dati mock - possiamo aggiungere estrazione reale dopo
    return {
        'success': True,
        'data': {
            'partita_iva': '12345678901',
            'codice_ateco': '62.01',
            'oggetto_sociale': 'Sviluppo software e consulenza informatica',
            'denominazione': 'ESEMPIO SRL',
            'codici_ateco': [
                {
                    'codice': '62.01',
                    'descrizione': 'Produzione di software',
                    'principale': True
                }
            ],
            'confidence': {
                'score': 75,
                'details': {
                    'partita_iva': 'found',
                    'ateco': 'found',
                    'oggetto_sociale': 'found'
                }
            }
        },
        'method': 'backend'
    }

@app.get("/api/extract-visura-precise")
def extract_visura_precise():
    """Versione precisa estrazione - per retrocompatibilità"""
    return {
        "status": "ok",
        "message": "Use POST /api/extract-visura instead"
    }

# NON serve if __name__ == "__main__" per Railway
# Railway usa il Procfile per avviare uvicorn