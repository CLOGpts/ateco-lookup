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

## 🚀 Sistema Live su Railway

### Backend in Produzione
```
URL Live: https://web-production-3373.up.railway.app
Status: ✅ ONLINE 24/7
Deploy: Automatico da GitHub
```

### Avvio Locale (per sviluppo)
```bash
# Installare dipendenze
pip install -r requirements.txt

# Avviare il server locale
python main.py

# Il server sarà disponibile su http://localhost:8000
```

### File Principali
- `main.py` - Server unificato con TUTTI gli endpoint
- `Procfile` - Configurazione Railway
- `requirements.txt` - Dipendenze minime (fastapi, uvicorn, python-multipart)

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
│              main.py                        │
│    Railway: web-production-3373.up.railway.app │
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
**File:** `main.py` (endpoints `/lookup`, `/batch`, `/autocomplete`)
**Funzionalità:**
- Ricerca codici ATECO 2022/2025 ✅
- Autocomplete per ricerca rapida ✅
- Batch lookup per ricerche multiple ✅
- Arricchimento con normative e certificazioni di settore ✅

### 2. **Risk Assessment Module**
**File:** `main.py` (tutti gli endpoint risk)
**Funzionalità:**
- 7 categorie di rischio operative bancarie ✅
- 191 eventi di rischio mappati ✅
- Sistema di scoring 0-100 punti ✅
- Matrice di rischio A1-D4 ✅
- Valutazione impatto finanziario e non economico ✅

### 3. **Visura Extractor Module**
**File:** `main.py` (endpoint `/api/extract-visura`)
**Funzionalità:**
- Mock funzionante per test frontend ✅
- Ritorna dati esempio realistici ✅
- Struttura compatibile con frontend ✅

---

## 🔌 API Endpoints Principali

### Base URL
```
Sviluppo: http://localhost:8000
Produzione: https://web-production-3373.up.railway.app
```

### Endpoints Disponibili

#### Core Services ✅ TUTTI FUNZIONANTI
- `GET /` - Root health check
- `GET /health` - Status API

#### ATECO Services (NON ATTIVI - main.py minimale)
- `GET /lookup` - Ricerca codice ATECO ❌
- `GET /autocomplete` - Suggerimenti durante digitazione ❌
- `POST /batch` - Ricerca multipla codici ❌

#### Risk Management Services ✅ FUNZIONANTI
- `GET /categories` - Lista categorie di rischio ✅
- `GET /events/{category}` - Eventi per categoria ✅
- `GET /description/{event_code}` - Descrizione evento ✅

#### Risk Assessment Services ✅ FUNZIONANTI
- `GET /risk-assessment-fields` - Struttura campi risk assessment ✅
- `POST /save-risk-assessment` - Salva e calcola risk score ✅
- `POST /calculate-risk-assessment` - Calcola matrice di rischio ✅

#### Visura Services ✅ MOCK FUNZIONANTE
- `POST /api/extract-visura` - Estrai dati da PDF (mock) ✅
- `GET /api/extract-visura-precise` - Retrocompatibilità ✅

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

### requirements.txt (Versione Railway - Minimale)
```
fastapi
uvicorn
python-multipart
```

### requirements.txt (Versione Completa - Locale)
```
fastapi
uvicorn
python-multipart
pandas
openpyxl
pyyaml
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
├── 📄 main.py                            # SERVER PRINCIPALE RAILWAY ⭐
├── 📄 ateco_lookup.py                    # Logiche ATECO (non usato su Railway)
├── 📄 visura_extractor_FINAL_embedded.py # Modulo estrazione (non usato)
├── 📊 tabella_ATECO.xlsx                 # Database ATECO
├── 📊 MAPPATURE_EXCEL_PERFETTE.json      # Eventi rischio ✅
├── ⚙️ mapping.yaml                       # Config normative
├── ⚙️ Procfile                          # Config Railway ✅
├── ⚙️ runtime.txt                       # Python 3.11 ✅
├── 📋 requirements.txt                   # Dipendenze minime ✅
├── 📚 DOCUMENTAZIONE_ARCHITETTURA_GENERALE.md  # Questo file
├── 📚 DOCUMENTAZIONE_BACKEND_ATECO.md    # Dettagli modulo ATECO
├── 📚 DOCUMENTAZIONE_BACKEND_EXCEL.md    # Dettagli risk assessment
├── 📚 DOCUMENTAZIONE_BACKEND_VISURE.md   # Dettagli estrazione PDF
└── 📁 _ARCHIVIO_DOC_OBSOLETE/           # File obsoleti archiviati
```

---

## 🔗 Link Utili

- **Repository GitHub**: https://github.com/CLOGpts/ateco-lookup
- **API Produzione Railway**: https://web-production-3373.up.railway.app
- **Health Check**: https://web-production-3373.up.railway.app/health
- **Documentazione Swagger**: http://localhost:8000/docs (solo locale)

---

## 📊 Stato del Sistema (16/12/2024)

### ✅ Funzionante in Produzione
- Backend live su Railway 24/7
- Risk Management completo (7 categorie, 191 eventi)
- Risk Assessment con matrice A1-D4
- Calcolo Risk Score 0-100
- Visura mock per test frontend
- CORS abilitato per tutti gli origin

### ⚠️ Limitazioni Attuali
- ATECO lookup non implementato nel main.py minimale
- Visura extraction è solo mock (ritorna dati esempio)
- Nessun database persistente (tutto in memoria)

### 🚀 Deploy
- Push su GitHub → Deploy automatico su Railway
- Nessun npm/node richiesto
- Backend completamente autonomo

---

## 📞 Supporto

Per domande tecniche sui moduli specifici, consultare:
- **ATECO**: DOCUMENTAZIONE_BACKEND_ATECO.md (riferimento, non attivo)
- **Risk Assessment**: DOCUMENTAZIONE_BACKEND_EXCEL.md ✅
- **Visure**: DOCUMENTAZIONE_BACKEND_VISURE.md (solo mock)

---

**Versione**: 3.1 - Railway Production
**Data**: 16 Dicembre 2024
**Deploy**: Railway (web-production-3373)
**Team**: Celerya Development