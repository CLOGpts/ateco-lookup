# Documentazione Modulo ATECO Lookup
## Sistema Completo di Ricerca e Classificazione Attività Economiche

---

## 🎯 Panoramica del Sistema

### Cosa fa questo modulo
Il modulo **ATECO Lookup** è il cuore del sistema di identificazione aziendale che:
1. **Cerca codici ATECO** (classificazione attività economiche italiane 2022/2025)
2. **Gestisce transizione ATECO** 2022 → 2025 con mappature ufficiali
3. **Arricchisce dati aziendali** con normative e certificazioni di settore
4. **Estrae dati da visure** camerali PDF (integrato con modulo visure)
5. **Suggerisce codici simili** quando non trova corrispondenze esatte
6. **Supporta ricerche batch** per elaborazione multipla (fino a 50 codici)
7. **Integra con Risk Assessment** per valutazione rischi di settore

### Architettura del Modulo
```
┌───────────────────────────────┐
│      ATECO Lookup Module      │
│       (ateco_lookup.py)       │
├───────────────────────────────┤
│ • Ricerca ATECO 2022/2025     │
│ • Autocomplete intelligente   │
│ • Batch processing           │
│ • Cache LRU per performance  │
├─────────────┬─────────────────┤
│ Data Sources │ Enrichment      │
├─────────────┼─────────────────┤
│ tabella_ATECO│ mapping.yaml    │
│ .xlsx        │ (normative)     │
└─────────────┴─────────────────┘
```

### Stack Tecnologico
- **Python 3.7+**: Linguaggio principale
- **FastAPI**: Framework REST API ad alte prestazioni
- **Pandas**: Gestione database ATECO Excel
- **Cache LRU**: Ottimizzazione ricerche frequenti (500+ entries)
- **PyYAML**: Configurazione mappature settori
- **CORS**: Configurabile per multi-domain
- **Uvicorn**: ASGI server per produzione

---

## 🚀 API REST Disponibili

### Base URL
```
Sviluppo: http://localhost:8000
Produzione: https://ateco-lookup.onrender.com
```

### 1. Health Check
**Endpoint:** `GET /health`

**Descrizione:** Verifica che il server sia attivo

**Risposta:**
```json
{
  "status": "ok",
  "version": "2.0",
  "cache_enabled": true
}
```

### 2. Ricerca ATECO (Core)
**Endpoint:** `GET /lookup`

**Parametri Query:**
| Parametro | Tipo | Obbligatorio | Descrizione | Default | Esempio |
|-----------|------|--------------|-------------|---------|------|
| `code` | string | ✅ | Codice ATECO da cercare | - | `62.01`, `20.14` |
| `prefer` | string | ❌ | Versione preferita | `2022` | `2025` |
| `prefix` | boolean | ❌ | Ricerca per prefisso | `false` | `true` |
| `limit` | integer | ❌ | Max risultati | `50` | `10` |

**Esempi di chiamate:**

1. **Ricerca esatta di un codice:**
```
GET /lookup?code=01.11.0
```

2. **Ricerca per prefisso (tutti i codici che iniziano con "20"):**
```
GET /lookup?code=20&prefix=true&limit=10
```

3. **Ricerca con preferenza versione 2025:**
```
GET /lookup?code=62.01&prefer=2025
```

**Risposta (ricerca esatta):**
```json
{
  "found": 1,
  "items": [
    {
      "CODICE_ATECO_2022": "62.01.0",
      "TITOLO_ATECO_2022": "Produzione di software non connesso all'edizione",
      "CODICE_ATECO_2025_RAPPRESENTATIVO": "62.01.00",
      "TITOLO_ATECO_2025_RAPPRESENTATIVO": "Produzione di software non connesso all'edizione",
      "TIPO_RICODIFICA": "1 a 1",
      "settore": "ict",
      "normative": [
        "GDPR (Reg. UE 2016/679)",
        "NIS2 (Direttiva UE 2022/2555)",
        "Cyber Resilience Act",
        "AI Act (quando applicabile)"
      ],
      "certificazioni": [
        "ISO 27001",
        "ISO 9001",
        "SOC 2",
        "ISO 27701"
      ]
    }
  ]
}
```

**Risposta (nessun risultato con suggerimenti):**
```json
{
  "found": 0,
  "items": [],
  "suggestions": [
    {
      "code": "62.02.0",
      "title": "Consulenza nel settore delle tecnologie dell'informatica",
      "similarity": 0.85
    },
    {
      "code": "62.03.0",
      "title": "Gestione di strutture e apparecchiature informatiche",
      "similarity": 0.72
    }
  ],
  "message": "Nessun risultato esatto. Ecco alcuni suggerimenti basati sulla ricerca."
}
```

### 3. Ricerca Batch (Multipla)
**Endpoint:** `POST /batch`

**Descrizione:** Permette di cercare più codici ATECO in una singola richiesta

**Corpo richiesta:**
```json
{
  "codes": ["20.14.0", "62.01", "10.11"],
  "prefer": "2025",
  "prefix": false
}
```

**Parametri:**
| Parametro | Tipo | Obbligatorio | Descrizione |
|-----------|------|--------------|-------------|
| `codes` | array | ✅ | Lista di codici ATECO da cercare (max 50) |
| `prefer` | string | ❌ | Priorità versione: `2022`, `2025`, `2025-camerale` |
| `prefix` | boolean | ❌ | Se `true`, cerca per prefisso |

**Risposta:**
```json
{
  "total_codes": 3,
  "results": [
    {
      "code": "20.14.0",
      "found": 1,
      "items": [/* dettagli ATECO */]
    },
    {
      "code": "62.01",
      "found": 1,
      "items": [/* dettagli ATECO */]
    },
    {
      "code": "10.11",
      "found": 0,
      "items": []
    }
  ]
}
```

### 4. Autocomplete
**Endpoint:** `GET /autocomplete`

**Descrizione:** Fornisce suggerimenti mentre l'utente digita un codice ATECO

**Parametri Query:**
| Parametro | Tipo | Obbligatorio | Descrizione | Default |
|-----------|------|--------------|-------------|---------|
| `partial` | string | ✅ | Codice parziale (min 2 caratteri) | - |
| `limit` | integer | ❌ | Numero massimo di suggerimenti (max 20) | 5 |

**Esempio chiamata:**
```
GET /autocomplete?partial=20.1&limit=10
```

**Risposta:**
```json
{
  "partial": "20.1",
  "suggestions": [
    {
      "code": "20.11.0",
      "title": "Fabbricazione di gas industriali",
      "version": "2022"
    },
    {
      "code": "20.14.0",
      "title": "Fabbricazione di altri prodotti chimici di base organici",
      "version": "2022"
    }
  ],
  "count": 2
}
```

### 5. Health Check
**Endpoint:** `GET /health`

**Descrizione:** Verifica stato del servizio e versione

**Risposta:**
```json
{
  "success": true,
  "message": "API funzionante! VisuraExtractorPower disponibile: true",
  "data": {
    "denominazione": "TEST CELERYA SRL",
    "partita_iva": "12345678901",
    "pec": "test@pec.it",
    "codici_ateco": [
      {"codice": "62.01", "descrizione": "Produzione software", "principale": true}
    ],
    "sede_legale": {
      "comune": "Torino",
      "provincia": "TO"
    },
    "confidence": 0.99
  }
}
```

### 6. Estrazione Visura Camerale [Integrato]
**Endpoint:** `POST /api/extract-visura`

**Descrizione:** Estrae P.IVA, codice ATECO e oggetto sociale da PDF visura

**Content-Type:** `multipart/form-data`

**Parametri:**
| Parametro | Tipo | Obbligatorio | Descrizione |
|-----------|------|--------------|-------------|
| `file` | file | ✅ | PDF visura camerale (max 20MB) |

**Note:** Vedi DOCUMENTAZIONE_BACKEND_VISURE.md per dettagli completi

**Esempio chiamata (JavaScript):**
```javascript
const formData = new FormData();
formData.append('file', pdfFile);

const response = await fetch('http://127.0.0.1:8000/api/extract-visura', {
  method: 'POST',
  body: formData
});
```

**Risposta (successo):**
```json
{
  "success": true,
  "data": {
    "codici_ateco": ["62.01.00", "62.02.00"],
    "oggetto_sociale": "Sviluppo software e consulenza informatica",
    "sede_legale": {
      "indirizzo": "Via Roma 1",
      "cap": "00100",
      "comune": "Roma",
      "provincia": "RM"
    },
    "tipo_business": "technology",
    "confidence": 0.95,
    "ateco_details": [
      {
        "code": "62.01.00",
        "description": "Produzione di software non connesso all'edizione",
        "normative": ["GDPR", "NIS2"],
        "certificazioni": ["ISO 27001", "ISO 9001"]
      }
    ]
  }
}
```

**Risposta (errore):**
```json
{
  "success": false,
  "error": {
    "code": "EXTRACTION_ERROR",
    "message": "Errore durante estrazione dati dal PDF",
    "details": "Dettagli specifici dell'errore"
  }
}
```

**Codici di errore possibili:**
- `INVALID_FILE_TYPE`: File non PDF
- `FILE_TOO_LARGE`: File supera 20MB
- `EMPTY_FILE`: File PDF vuoto
- `MODULE_NOT_AVAILABLE`: Dipendenze mancanti per estrazione PDF
- `EXTRACTION_ERROR`: Errore generico durante l'estrazione

**Note importanti:**
1. Il sistema usa priorità di fallback per gli estrattori:
   - Prima prova `visura_extractor_fixed.py` (versione corretta)
   - Se non disponibile, usa `visura_extractor_power.py`
   - Come ultimo fallback usa `visura_extractor.py` base
2. Richiede l'installazione di dipendenze aggiuntive:
```bash
pip install pdfplumber PyPDF2 Pillow pdfminer.six python-multipart
```

---

## 📊 Struttura Dati Risposta

### Campi principali ritornati per ogni codice ATECO:

| Campo | Tipo | Descrizione |
|-------|------|-------------|
| `CODICE_ATECO_2022` | string | Codice ATECO versione 2022 |
| `TITOLO_ATECO_2022` | string | Descrizione attività versione 2022 |
| `GERARCHIA_ATECO_2022` | string | Gerarchia classificazione (es: C.20.14.0) |
| `CODICE_ATECO_2025_RAPPRESENTATIVO` | string | Codice ATECO versione 2025 |
| `TITOLO_ATECO_2025_RAPPRESENTATIVO` | string | Descrizione attività versione 2025 |
| `TIPO_RICODIFICA` | string | Tipo di mappatura tra versioni (es: "1 a 1", "1 a molti") |
| `settore` | string | Settore identificato (chimico, alimentare, sanitario, etc.) |
| `normative` | array | Lista normative applicabili al settore |
| `certificazioni` | array | Lista certificazioni consigliate per il settore |

### Settori Mappati e Normative

| Settore | Prefissi ATECO | Normative Principali | Certificazioni |
|---------|----------------|---------------------|----------------|
| **ICT** | 62, 63 | GDPR, NIS2, CRA, AI Act | ISO 27001, SOC 2 |
| **Chimico** | 20 | REACH, CLP, Seveso III | ISO 14001, 45001 |
| **Alimentare** | 10, 11 | HACCP, Reg. 178/2002 | ISO 22000, BRC |
| **Sanitario** | 21, 86 | MDR, IVDR, GMP | ISO 13485, 9001 |
| **Automotive** | 29, 45 | UNECE, TISAX | IATF 16949, ISO 26262 |
| **Finance** | 64, 66 | DORA, PSD2, MiFID II | ISO 27001, PCI DSS |
| **Industriale** | 25, 28 | Macchine 2006/42/CE | ISO 9001, 45001 |

---

## 🛠️ Installazione e Avvio

### Prerequisiti
- Python 3.7 o superiore
- pip (gestore pacchetti Python)

### 1. Installazione dipendenze
```bash
pip install -r requirements.txt
```

Oppure manualmente (dipendenze base):
```bash
pip install pandas openpyxl pyyaml fastapi uvicorn python-multipart
```

Per funzionalità complete (inclusa estrazione PDF):
```bash
pip install pandas openpyxl pyyaml fastapi uvicorn python-multipart pdfplumber PyPDF2 Pillow pdfminer.six
```

### 2. File necessari
Assicurati di avere nella stessa cartella:
- `ateco_lookup.py` (script principale)
- `tabella_ATECO.xlsx` (database codici ATECO)
- `mapping.yaml` (mappatura settori/normative)
- `requirements.txt` (dipendenze)
- `visura_extractor_fixed.py` (opzionale, per estrazione PDF - versione consigliata)
- `visura_extractor_power.py` (opzionale, per estrazione PDF - fallback)
- `visura_extractor.py` (opzionale, per estrazione PDF - fallback base)

### 3. Avvio del server API
```bash
python ateco_lookup.py --file tabella_ATECO.xlsx --serve
```

Opzioni avanzate:
```bash
# Cambiare porta e host
python ateco_lookup.py --file tabella_ATECO.xlsx --serve --host 0.0.0.0 --port 8080

# Con debug attivo
python ateco_lookup.py --file tabella_ATECO.xlsx --serve --debug
```

**Nota:** Il parametro `--debug` abilita logging dettagliato per troubleshooting.

### 4. Verifica funzionamento
Apri il browser e vai a:
- `http://127.0.0.1:8000/health` - dovrebbe rispondere `{"status": "ok", "version": "2.0", "cache_enabled": true}`
- `http://127.0.0.1:8000/docs` - documentazione interattiva Swagger UI (generata automaticamente da FastAPI)

---

## 🧪 Testing delle API

### Con cURL (command line)
```bash
# Health check
curl http://127.0.0.1:8000/health

# Ricerca codice specifico
curl "http://127.0.0.1:8000/lookup?code=20.14.0"

# Ricerca per prefisso
curl "http://127.0.0.1:8000/lookup?code=62&prefix=true&limit=5"

# Autocomplete
curl "http://127.0.0.1:8000/autocomplete?partial=20.1&limit=5"

# Batch (richiede POST)
curl -X POST http://127.0.0.1:8000/batch \
  -H "Content-Type: application/json" \
  -d '{"codes": ["20.14.0", "62.01"], "prefer": "2025"}'

# Estrazione visura (richiede file PDF)
curl -X POST http://127.0.0.1:8000/api/extract-visura \
  -F "file=@visura.pdf"
```

### Con JavaScript/Fetch (dal frontend)
```javascript
// Esempio ricerca codice ATECO
async function cercaATECO(codice) {
    try {
        const response = await fetch(`http://127.0.0.1:8000/lookup?code=${codice}`);
        const data = await response.json();
        
        if (data.found > 0) {
            console.log('Trovato:', data.items[0]);
            console.log('Settore:', data.items[0].settore);
            console.log('Normative:', data.items[0].normative);
        } else {
            console.log('Nessun risultato trovato');
            if (data.suggestions) {
                console.log('Suggerimenti:', data.suggestions);
            }
        }
    } catch (error) {
        console.error('Errore nella chiamata API:', error);
    }
}

// Esempio ricerca per prefisso
async function cercaPerPrefisso(prefisso) {
    const response = await fetch(
        `http://127.0.0.1:8000/lookup?code=${prefisso}&prefix=true&limit=10`
    );
    const data = await response.json();
    console.log(`Trovati ${data.found} risultati`);
    return data.items;
}

// Esempio autocomplete
async function getAutocompleteSuggestions(partial) {
    const response = await fetch(
        `http://127.0.0.1:8000/autocomplete?partial=${partial}&limit=5`
    );
    const data = await response.json();
    return data.suggestions;
}

// Esempio batch lookup
async function cercaMultipli(codes) {
    const response = await fetch('http://127.0.0.1:8000/batch', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({
            codes: codes,
            prefer: '2025'
        })
    });
    const data = await response.json();
    return data.results;
}

// Esempio estrazione visura
async function estraiDatiVisura(pdfFile) {
    const formData = new FormData();
    formData.append('file', pdfFile);
    
    const response = await fetch('http://127.0.0.1:8000/api/extract-visura', {
        method: 'POST',
        body: formData
    });
    
    const data = await response.json();
    if (data.success) {
        console.log('Codici ATECO estratti:', data.data.codici_ateco);
        console.log('Dettagli ATECO:', data.data.ateco_details);
        return data.data;
    } else {
        console.error('Errore estrazione:', data.error);
        throw new Error(data.error.message);
    }
}
```

### Con Axios (React/Vue)
```javascript
import axios from 'axios';

const API_BASE = 'http://127.0.0.1:8000';

// Servizio per le chiamate API
const atecoService = {
    // Ricerca singolo codice
    async lookup(code, options = {}) {
        const params = { code, ...options };
        const response = await axios.get(`${API_BASE}/lookup`, { params });
        return response.data;
    },
    
    // Ricerca per prefisso
    async searchByPrefix(prefix, limit = 10) {
        return this.lookup(prefix, { prefix: true, limit });
    },
    
    // Autocomplete
    async autocomplete(partial, limit = 5) {
        const response = await axios.get(`${API_BASE}/autocomplete`, {
            params: { partial, limit }
        });
        return response.data.suggestions;
    },
    
    // Batch lookup
    async batchLookup(codes, prefer = null) {
        const response = await axios.post(`${API_BASE}/batch`, {
            codes,
            prefer,
            prefix: false
        });
        return response.data.results;
    },
    
    // Estrazione visura
    async extractVisura(file) {
        const formData = new FormData();
        formData.append('file', file);
        
        const response = await axios.post(
            `${API_BASE}/api/extract-visura`,
            formData,
            {
                headers: {
                    'Content-Type': 'multipart/form-data'
                }
            }
        );
        return response.data;
    },
    
    // Health check
    async checkHealth() {
        const response = await axios.get(`${API_BASE}/health`);
        return response.data.status === 'ok';
    }
};

// Uso nel componente
const risultato = await atecoService.lookup('62.01.0');
const risultatiMultipli = await atecoService.searchByPrefix('20', 5);
const suggerimenti = await atecoService.autocomplete('20.1');
const batch = await atecoService.batchLookup(['20.14', '62.01'], '2025');

// Per file upload
const handleFileUpload = async (event) => {
    const file = event.target.files[0];
    const result = await atecoService.extractVisura(file);
    console.log('Dati estratti:', result);
};
```

---

## 🔍 Logica di Ricerca

### Come funziona la ricerca "smart"
Il sistema applica diverse strategie per trovare il codice ATECO:

1. **Normalizzazione**: Il codice viene pulito (spazi, virgole→punti, maiuscole)
2. **Varianti**: Genera varianti del codice (con/senza punti, con zeri finali)
3. **Priorità**: Cerca prima nella versione preferita (2022, 2025, o 2025-camerale)
4. **Fallback**: Se non trova corrispondenze esatte, può cercare per prefisso

### Esempi di ricerca intelligente:
- Input: `"01.11"` → Trova `"01.11.0"`, `"01.11.00"`
- Input: `"0111"` → Trova `"01.11.0"`
- Input: `"20.14,0"` → Trova `"20.14.0"`
- Input: `"62"` con `prefix=true` → Trova tutti i codici del settore ICT

---

## 🔧 Personalizzazione

### Aggiungere nuovi settori
Modifica il file `mapping.yaml`:

```yaml
settori:
  nuovo_settore:
    normative:
      - "Normativa 1"
      - "Normativa 2"
    certificazioni:
      - "ISO XXXXX"
      - "Certificazione Y"
```

Poi modifica la funzione `enrich()` in `ateco_lookup.py` per mappare i prefissi ATECO al nuovo settore.

### Settori attualmente configurati
Il file `mapping.yaml` include già questi settori:
- **chimico**: Industria chimica (REACH, CLP, Seveso)
- **alimentare**: Industria alimentare (HACCP, etichettatura)
- **sanitario**: Dispositivi medici e sanità (MDR, IVDR)
- **automotive**: Industria automobilistica (UNECE, TISAX)
- **industriale**: Manifattura e industria (IEC 62443, CRA)
- **finance**: Servizi finanziari (DORA, PSD2, MiFID)
- **ict**: Tecnologia e software (NIS2, GDPR, CRA)

### Modificare i dati ATECO
Il file Excel `tabella_ATECO.xlsx` contiene tutti i codici. Le colonne principali sono:
- `CODICE_ATECO_2022`
- `TITOLO_ATECO_2022`
- `CODICE_ATECO_2025_RAPPRESENTATIVO`
- `TITOLO_ATECO_2025_RAPPRESENTATIVO`

---

## 📝 Note per l'integrazione Frontend

### CORS
Il backend ha CORS abilitato con `allow_origins=["*"]`. In produzione, modificare per accettare solo il dominio del frontend:

```python
# In ateco_lookup.py, riga 356
allow_origins=["https://tuodominio.com"]
```

### Gestione errori
Implementa sempre gestione errori nel frontend:

```javascript
try {
    const data = await atecoService.lookup(codice);
    // elabora dati
} catch (error) {
    if (error.response) {
        // Server ha risposto con errore
        console.error('Errore server:', error.response.status);
    } else if (error.request) {
        // Nessuna risposta dal server
        console.error('Server non raggiungibile');
    } else {
        // Errore nella configurazione
        console.error('Errore:', error.message);
    }
}
```

### Suggerimenti UI/UX
1. **Autocomplete**: Usa l'endpoint `/autocomplete` dedicato per suggerimenti mentre l'utente digita
2. **Debouncing**: Attendi 300-500ms dopo che l'utente smette di digitare prima di chiamare l'API
3. **Loading state**: Mostra indicatore di caricamento durante le chiamate API
4. **Cache locale**: Considera di cachare i risultati frequenti per ridurre le chiamate (il backend ha già cache LRU)
5. **Suggerimenti**: Quando non ci sono risultati, mostra i codici suggeriti dal campo `suggestions`
6. **Batch requests**: Per ricerche multiple usa `/batch` invece di chiamate singole
7. **Upload visure**: Implementa drag-and-drop per caricare PDF di visure camerali

---

## 🆘 Troubleshooting

### Problema: "File non trovato: tabella_ATECO.xlsx"
**Soluzione**: Assicurati che il file Excel sia nella stessa cartella dello script o specifica il percorso completo.

### Problema: "ModuleNotFoundError"
**Soluzione**: Installa le dipendenze mancanti con `pip install -r requirements.txt`

### Problema: "Address already in use"
**Soluzione**: La porta 8000 è già occupata. Usa una porta diversa: `--port 8001`

### Problema: CORS bloccato dal browser
**Soluzione**: Verifica che il backend sia avviato e che l'URL sia corretto. In sviluppo, assicurati che CORS sia configurato con `allow_origins=["*"]`.

---

## 📧 Supporto

Per domande o problemi specifici sul backend, fare riferimento a:
- Codice sorgente: `ateco_lookup.py`
- Configurazione settori: `mapping.yaml`
- Questa documentazione

Il sistema è progettato per essere semplice, affidabile e facilmente integrabile con qualsiasi frontend moderno (React, Vue, Angular, vanilla JS).