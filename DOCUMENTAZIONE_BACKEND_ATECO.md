# Documentazione Backend ATECO Lookup
## Per Sviluppatore Frontend

---

## 🎯 Panoramica del Sistema

### Cosa fa questo backend
Il backend **ATECO Lookup** è un servizio Python che permette di:
1. **Cercare codici ATECO** (classificazione delle attività economiche italiane)
2. **Ottenere informazioni dettagliate** su ogni codice (descrizioni, gerarchie, ricodifiche 2022/2025)
3. **Arricchire i dati** con normative e certificazioni pertinenti al settore
4. **Fornire API REST** per integrazione con applicazioni frontend
5. **Estrarre automaticamente dati** da PDF di visure camerali
6. **Suggerire codici simili** quando non si trovano corrispondenze esatte
7. **Supportare ricerche batch** per elaborazione multipla efficiente

### Architettura
```
┌─────────────────────┐
│   Frontend (UI)     │
└──────────┬──────────┘
           │ HTTP/REST
           ▼
┌─────────────────────┐
│   FastAPI Server    │  ← Porta 8000 (configurabile)
├─────────────────────┤
│  ateco_lookup.py    │  ← Logica principale
├─────────────────────┤
│   File Excel        │  ← Database ATECO (tabella_ATECO.xlsx)
│   mapping.yaml      │  ← Mappatura settori/normative
└─────────────────────┘
```

### Tecnologie utilizzate
- **Python 3.x**
- **FastAPI**: Framework web moderno per API REST
- **Pandas**: Manipolazione dati Excel
- **CORS abilitato**: Permette chiamate da domini diversi
- **Cache LRU**: Ottimizzazione performance per ricerche frequenti
- **pdfplumber/PyPDF2**: Estrazione dati da PDF (opzionale)

---

## 🚀 API REST Disponibili

### Base URL
```
http://127.0.0.1:8000
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

### 2. Ricerca ATECO (Principale)
**Endpoint:** `GET /lookup`

**Parametri Query:**
| Parametro | Tipo | Obbligatorio | Descrizione | Esempio |
|-----------|------|--------------|-------------|---------|
| `code` | string | ✅ | Codice ATECO da cercare | `01.11.0`, `20.14`, `62` |
| `prefer` | string | ❌ | Priorità versione: `2022`, `2025`, `2025-camerale` | `2025` |
| `prefix` | boolean | ❌ | Se `true`, cerca tutti i codici che iniziano con il valore fornito | `true` |
| `limit` | integer | ❌ | Numero massimo di risultati (default: 50) | `10` |

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

**Risposta tipo (ricerca esatta):**
```json
{
  "found": 1,
  "items": [
    {
      "ORDINE_CODICE_ATECO_2022": "123",
      "CODICE_ATECO_2022": "20.14.0",
      "TITOLO_ATECO_2022": "Fabbricazione di altri prodotti chimici di base organici",
      "GERARCHIA_ATECO_2022": "C.20.14.0",
      "NUMERO_CORR_ATECO_2022": "456",
      "SOTTOTIPOLOGIA": "invariato",
      "TIPO_RICODIFICA": "1 a 1",
      "CODICE_ATECO_2025_RAPPRESENTATIVO": "20.14.00",
      "TITOLO_ATECO_2025_RAPPRESENTATIVO": "Fabbricazione di altri prodotti chimici di base organici",
      "CODICE_ATECO_2025_RAPPRESENTATIVO_SISTEMA_CAMERALE": "20.14.00",
      "TITOLO_ATECO_2025_RAPPRESENTATIVO_SISTEMA_CAMERALE": "Fabbricazione di altri prodotti chimici di base organici",
      "settore": "chimico",
      "normative": [
        "REACH (Reg. CE 1907/2006)",
        "CLP (Reg. CE 1272/2008)",
        "Direttiva 98/24/CE (Agenti chimici)",
        "Direttiva Seveso III (2012/18/UE)"
      ],
      "certificazioni": [
        "ISO 9001",
        "ISO 14001",
        "ISO 45001",
        "ISO 50001"
      ]
    }
  ]
}
```

**Risposta tipo (nessun risultato):**
```json
{
  "found": 0,
  "items": [],
  "suggestions": [
    {
      "code": "20.13.0",
      "title": "Fabbricazione di altri prodotti chimici di base inorganici"
    },
    {
      "code": "20.15.0",
      "title": "Fabbricazione di fertilizzanti e composti azotati"
    }
  ],
  "message": "Nessun risultato per 'XX.XX'. Prova con uno dei suggerimenti."
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

### 5. Estrazione Visura Camerale
**Endpoint:** `POST /api/extract-visura`

**Descrizione:** Estrae dati strutturati da un PDF di visura camerale

**Content-Type:** `multipart/form-data`

**Parametri:**
| Parametro | Tipo | Obbligatorio | Descrizione |
|-----------|------|--------------|-------------|
| `file` | file | ✅ | File PDF della visura (max 20MB) |

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

**Note:** Richiede l'installazione di dipendenze aggiuntive:
```bash
pip install pdfplumber PyPDF2 Pillow pdfminer.six
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

### Settori mappati e relativi prefissi ATECO:
- **Chimico**: codici che iniziano con `20`
- **Alimentare**: codici che iniziano con `10` o `11`
- **Sanitario**: codici che iniziano con `21` o `86`
- **Automotive**: codici che iniziano con `29` o `45`
- **Industriale**: codici che iniziano con `25` o `28`
- **ICT**: codici che iniziano con `62`
- **Finance**: codici che iniziano con `64` o `66`

---

## 🛠️ Installazione e Avvio

### Prerequisiti
- Python 3.7 o superiore
- pip (gestore pacchetti Python)

### 1. Installazione dipendenze
```bash
pip install -r requirements.txt
```

Oppure manualmente:
```bash
pip install pandas openpyxl pyyaml fastapi uvicorn
```

### 2. File necessari
Assicurati di avere nella stessa cartella:
- `ateco_lookup.py` (script principale)
- `tabella_ATECO.xlsx` (database codici ATECO)
- `mapping.yaml` (mappatura settori/normative)
- `requirements.txt` (dipendenze)

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

**Nota:** Per l'estrazione da PDF visure camerali, installa anche:
```bash
pip install pdfplumber PyPDF2 Pillow pdfminer.six
```

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

Poi modifica la funzione `enrich()` in `ateco_lookup.py` (righe 183-215) per mappare i prefissi ATECO al nuovo settore.

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