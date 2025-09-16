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

# NON serve if __name__ == "__main__" per Railway
# Railway usa il Procfile per avviare uvicorn