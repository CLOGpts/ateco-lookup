#!/usr/bin/env python3
"""
API Backend per Railway - VERSIONE MINIMAL TESTATA
"""
import os
import json
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

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
    with open("MAPPATURE_EXCEL_PERFETTE.json", 'r', encoding='utf-8') as f:
        data = json.load(f)
        EXCEL_CATEGORIES = data.get('mappature_categoria_eventi', {})
        EXCEL_DESCRIPTIONS = data.get('vlookup_map', {})
except:
    pass

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

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=port)