# 🏗️ Architettura Sistema Celerya Cyber ATECO
## Documentazione Completa per Sviluppatori Frontend

---

## 📋 Overview del Sistema

Il sistema **Celerya Cyber ATECO** è una piattaforma completa per la gestione del rischio aziendale che integra:
1. **Ricerca e classificazione ATECO** per identificare l'attività economica
2. **Risk Assessment Matrix** per valutare rischi operativi (stile bancario)
3. **Estrazione automatica** dati da visure camerali PDF
4. **Calcolo Risk Score** con algoritmi di valutazione del rischio

### 🎯 Obiettivo
Fornire uno strumento completo per l'analisi del rischio aziendale partendo dall'identificazione dell'attività economica (codice ATECO) fino alla valutazione completa dei rischi operativi.

---

## 🚀 Come Avviare il Sistema

### Backend Principale (Python)
```bash
# Installare dipendenze
pip install -r requirements.txt

# Avviare il server principale
python ateco_lookup.py --file tabella_ATECO.xlsx --serve --port 8000

# Il server sarà disponibile su http://localhost:8000
```

### Server di Test (opzionale)
```bash
# Per test locali con mock data
python test_server.py
```

---

## 🏛️ Architettura del Sistema

```
┌─────────────────────────────────────────────┐
│              FRONTEND (UI)                  │
│         React/Vue/Angular/Vanilla           │
└──────────────────┬──────────────────────────┘
                   │ REST API
                   ▼
┌─────────────────────────────────────────────┐
│          BACKEND API (FastAPI)              │
│           ateco_lookup.py                   │
├─────────────────────────────────────────────┤
│  Modulo 1: ATECO Lookup                    │
│  - Ricerca codici ATECO                    │
│  - Mappatura normative/certificazioni      │
├─────────────────────────────────────────────┤
│  Modulo 2: Risk Assessment                 │
│  - Categorie rischio operative             │
│  - Eventi di rischio (191 eventi)          │
│  - Calcolo risk score                      │
├─────────────────────────────────────────────┤
│  Modulo 3: Visura Extractor               │
│  - Estrazione P.IVA                       │
│  - Estrazione codice ATECO                │
│  - Estrazione oggetto sociale             │
└─────────────────────────────────────────────┘
                   │
                   ▼
┌─────────────────────────────────────────────┐
│             DATA SOURCES                    │
├─────────────────────────────────────────────┤
│  • tabella_ATECO.xlsx (database ATECO)     │
│  • mapping.yaml (normative/certificazioni)  │
│  • MAPPATURE_EXCEL_PERFETTE.json (eventi)  │
└─────────────────────────────────────────────┘
```

---

## 📦 Moduli Principali

### 1. **ATECO Lookup Module**
**File:** `ateco_lookup.py` (parte principale)
**Funzionalità:**
- Ricerca codici ATECO 2022/2025
- Autocomplete per ricerca rapida
- Batch lookup per ricerche multiple
- Arricchimento con normative e certificazioni di settore

### 2. **Risk Assessment Module**
**File:** `ateco_lookup.py` (endpoints `/categories`, `/events`, `/calculate-risk-assessment`)
**Funzionalità:**
- 7 categorie di rischio operative bancarie
- 191 eventi di rischio mappati
- Sistema di scoring 0-100 punti
- Valutazione impatto finanziario e non economico

### 3. **Visura Extractor Module**
**File:** `visura_extractor_FINAL_embedded.py` (integrato in ateco_lookup.py)
**Funzionalità:**
- Estrazione STRICT di soli 3 campi fondamentali
- Sistema bulletproof con zero crash
- Confidence score reale basato su validazioni

---

## 🔌 API Endpoints Principali

### Base URL
```
Sviluppo: http://localhost:8000
Produzione: https://ateco-lookup.onrender.com
```

### Endpoints Disponibili

#### ATECO Services
- `GET /health` - Health check
- `GET /lookup` - Ricerca codice ATECO
- `GET /autocomplete` - Suggerimenti durante digitazione
- `POST /batch` - Ricerca multipla codici

#### Risk Assessment Services
- `GET /categories` - Lista categorie di rischio
- `GET /events/{category}` - Eventi per categoria
- `GET /description/{event_code}` - Descrizione evento
- `GET /risk-assessment-fields` - Struttura campi risk assessment
- `POST /save-risk-assessment` - Salva e calcola risk score
- `POST /calculate-risk-assessment` - Calcola risk assessment completo

#### Visura Services
- `GET /api/test-visura` - Test endpoint
- `POST /api/extract-visura` - Estrai dati da PDF

---

## 📊 Strutture Dati Principali

### Risk Assessment Data
```json
{
  "company": "Nome Azienda",
  "risk_category": "Clients_product_Clienti",
  "event": "501 - Mancato rispetto...",
  "financial_impact": "1-10k€",
  "economic_loss": "G",
  "image_impact": true,
  "regulatory_impact": false,
  "criminal_impact": false,
  "non_economic_loss": "Y",
  "control_level": "++",
  "control_description": "Adeguato"
}
```

### ATECO Response
```json
{
  "found": 1,
  "items": [{
    "CODICE_ATECO_2022": "62.01.0",
    "TITOLO_ATECO_2022": "Produzione di software",
    "settore": "ict",
    "normative": ["GDPR", "NIS2"],
    "certificazioni": ["ISO 27001"]
  }]
}
```

### Visura Extraction Response
```json
{
  "success": true,
  "data": {
    "partita_iva": "12345678901",
    "codice_ateco": "62.01",
    "oggetto_sociale": "Sviluppo software...",
    "confidence": {
      "score": 100,
      "assessment": "✅ Tutti e 3 i campi trovati"
    }
  }
}
```

---

## 🔧 File di Configurazione

### requirements.txt
```
pandas
openpyxl
pyyaml
fastapi
uvicorn
python-multipart
pdfplumber
PyPDF2
Pillow>=9.0.0
pdfminer.six>=20211012
```

### mapping.yaml
Contiene mappature settori → normative/certificazioni

### MAPPATURE_EXCEL_PERFETTE.json
Database eventi di rischio estratti dal file Excel del consulente

---

## 📝 Note per il Frontend Developer

### Best Practices
1. **Gestione errori**: Sempre implementare try/catch
2. **Null handling**: I campi possono essere null (specialmente da visure)
3. **Loading states**: Mostrare indicatori durante chiamate API
4. **Debouncing**: Per autocomplete, attendere 300ms dopo digitazione
5. **Cache**: Considerare cache locale per risultati frequenti

### Esempio Integrazione (JavaScript)
```javascript
// Servizio API base
const API_BASE = 'http://localhost:8000';

// Ricerca ATECO
async function searchATECO(code) {
  const response = await fetch(`${API_BASE}/lookup?code=${code}`);
  return response.json();
}

// Risk Assessment
async function getRiskCategories() {
  const response = await fetch(`${API_BASE}/categories`);
  return response.json();
}

// Estrazione Visura
async function extractVisura(pdfFile) {
  const formData = new FormData();
  formData.append('file', pdfFile);

  const response = await fetch(`${API_BASE}/api/extract-visura`, {
    method: 'POST',
    body: formData
  });
  return response.json();
}
```

---

## 🚨 Punti di Attenzione

### CORS
Il backend ha CORS abilitato per tutti gli origin (`*`). In produzione, configurare per domini specifici.

### Limiti
- Upload PDF: max 20MB
- Batch lookup: max 50 codici per richiesta
- Autocomplete: max 20 suggerimenti

### Performance
- Cache LRU attiva per ricerche frequenti
- Tempo risposta tipico: < 500ms
- Estrazione PDF: 1-3 secondi

---

## 📂 Struttura File Progetto

```
Celerya_Cyber_Ateco/
├── 📄 ateco_lookup.py                    # Server principale
├── 📄 visura_extractor_FINAL_embedded.py # Modulo estrazione
├── 📄 test_server.py                      # Server di test
├── 📄 analisi_precisa_1000.py            # Utility estrazione Excel
├── 📊 tabella_ATECO.xlsx                 # Database ATECO
├── 📊 MAPPATURE_EXCEL_PERFETTE.json      # Eventi rischio
├── ⚙️ mapping.yaml                       # Config normative
├── 📋 requirements.txt                   # Dipendenze Python
├── 📚 DOCUMENTAZIONE_ARCHITETTURA_GENERALE.md  # Questo file
├── 📚 DOCUMENTAZIONE_BACKEND_ATECO.md    # Dettagli modulo ATECO
├── 📚 DOCUMENTAZIONE_BACKEND_EXCEL.md    # Dettagli risk assessment
└── 📚 DOCUMENTAZIONE_BACKEND_VISURE.md   # Dettagli estrazione PDF
```

---

## 🔗 Link Utili

- **Repository**: [Da configurare]
- **API Produzione**: https://ateco-lookup.onrender.com
- **Documentazione Swagger**: http://localhost:8000/docs (quando server attivo)

---

## 📞 Supporto

Per domande tecniche sui moduli specifici, consultare:
- **ATECO**: DOCUMENTAZIONE_BACKEND_ATECO.md
- **Risk Assessment**: DOCUMENTAZIONE_BACKEND_EXCEL.md
- **Visure**: DOCUMENTAZIONE_BACKEND_VISURE.md

---

**Versione**: 3.0
**Data**: Dicembre 2024
**Team**: Celerya Development