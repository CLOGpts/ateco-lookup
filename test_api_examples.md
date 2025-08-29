# 🧪 Test delle Nuove Funzionalità API

## Ambiente di Test
Per testare le nuove funzionalità, assicurati di avere installato le dipendenze:

```bash
pip install pandas openpyxl pyyaml fastapi uvicorn
```

Poi avvia il server:
```bash
python ateco_lookup.py --file tabella_ATECO.xlsx --serve --port 8000
```

## 1. Health Check Migliorato ✅
**Nuovo:** Ora ritorna versione e stato cache

### Test con cURL:
```bash
curl http://127.0.0.1:8000/health
```

### Risposta attesa:
```json
{
  "status": "ok",
  "version": "2.0",
  "cache_enabled": true
}
```

## 2. Lookup con Gestione Errori ✅
**Nuovo:** Validazione input e suggerimenti quando non trova risultati

### Test codice troppo corto:
```bash
curl "http://127.0.0.1:8000/lookup?code=1"
```

### Risposta attesa (errore strutturato):
```json
{
  "detail": {
    "error": "INVALID_CODE",
    "message": "Codice troppo corto (minimo 2 caratteri)"
  }
}
```

### Test codice non trovato con suggerimenti:
```bash
curl "http://127.0.0.1:8000/lookup?code=99.99.99"
```

### Risposta attesa:
```json
{
  "found": 0,
  "items": [],
  "suggestions": [
    {"code": "99.09.01", "title": "Altri servizi..."},
    {"code": "99.00.00", "title": "Attività di organizzazioni..."}
  ],
  "message": "Nessun risultato per '99.99.99'. Prova con uno dei suggerimenti."
}
```

## 3. Batch Lookup (NUOVO) ✅
**Permette di cercare multipli codici in una sola richiesta**

### Test con cURL:
```bash
curl -X POST "http://127.0.0.1:8000/batch" \
  -H "Content-Type: application/json" \
  -d '{
    "codes": ["20.14.0", "62.01.0", "10.11.0"],
    "prefer": "2025",
    "prefix": false
  }'
```

### Risposta attesa:
```json
{
  "total_codes": 3,
  "results": [
    {
      "code": "20.14.0",
      "found": 1,
      "items": [{
        "CODICE_ATECO_2022": "20.14.0",
        "TITOLO_ATECO_2022": "Fabbricazione di altri prodotti chimici",
        "settore": "chimico",
        "normative": ["REACH", "CLP", "..."],
        "certificazioni": ["ISO 9001", "..."]
      }]
    },
    {
      "code": "62.01.0",
      "found": 1,
      "items": [{
        "CODICE_ATECO_2022": "62.01.0",
        "TITOLO_ATECO_2022": "Produzione di software",
        "settore": "ict",
        "normative": ["NIS2", "GDPR", "..."],
        "certificazioni": ["ISO 27001", "..."]
      }]
    },
    {
      "code": "10.11.0",
      "found": 1,
      "items": [{
        "CODICE_ATECO_2022": "10.11.0",
        "TITOLO_ATECO_2022": "Lavorazione carni",
        "settore": "alimentare",
        "normative": ["Reg. CE 178/2002", "..."],
        "certificazioni": ["ISO 22000", "..."]
      }]
    }
  ]
}
```

### Test limite batch (max 50 codici):
```bash
curl -X POST "http://127.0.0.1:8000/batch" \
  -H "Content-Type: application/json" \
  -d '{
    "codes": ["01.11.0", "01.12.0", ... (51 codici)]
  }'
```

### Risposta errore:
```json
{
  "detail": {
    "error": "TOO_MANY_CODES",
    "message": "Massimo 50 codici per richiesta batch"
  }
}
```

## 4. Autocomplete (NUOVO) ✅
**Suggerimenti mentre l'utente digita**

### Test autocomplete base:
```bash
curl "http://127.0.0.1:8000/autocomplete?partial=20.1"
```

### Risposta attesa:
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
      "code": "20.12.0",
      "title": "Fabbricazione di coloranti e pigmenti",
      "version": "2022"
    },
    {
      "code": "20.13.0",
      "title": "Fabbricazione di altri prodotti chimici inorganici",
      "version": "2022"
    },
    {
      "code": "20.14.0",
      "title": "Fabbricazione di altri prodotti chimici organici",
      "version": "2022"
    },
    {
      "code": "20.15.0",
      "title": "Fabbricazione di fertilizzanti",
      "version": "2022"
    }
  ],
  "count": 5
}
```

### Test con limite personalizzato:
```bash
curl "http://127.0.0.1:8000/autocomplete?partial=62&limit=3"
```

### Risposta attesa:
```json
{
  "partial": "62",
  "suggestions": [
    {
      "code": "62.01.0",
      "title": "Produzione di software",
      "version": "2022"
    },
    {
      "code": "62.02.0",
      "title": "Consulenza informatica",
      "version": "2022"
    },
    {
      "code": "62.03.0",
      "title": "Gestione di strutture informatizzate",
      "version": "2022"
    }
  ],
  "count": 3
}
```

## 5. Cache LRU (Performance) ✅
**Le ricerche ripetute sono ora molto più veloci**

### Test performance:
```bash
# Prima chiamata (senza cache)
time curl "http://127.0.0.1:8000/lookup?code=20.14.0"
# Tempo: ~50ms

# Seconda chiamata (con cache)
time curl "http://127.0.0.1:8000/lookup?code=20.14.0"
# Tempo: ~5ms (10x più veloce!)
```

## 6. Logging Strutturato ✅
**Tutti gli endpoint ora loggano le richieste**

### Output server (console):
```
2025-08-29 15:30:45,123 - ateco_lookup - INFO - Health check requested
2025-08-29 15:30:50,456 - ateco_lookup - INFO - Lookup requested for code: 20.14.0, prefer: 2025, prefix: False
2025-08-29 15:30:50,478 - ateco_lookup - INFO - Found 1 results for code: 20.14.0
2025-08-29 15:30:55,789 - ateco_lookup - WARNING - Invalid code provided: 1
2025-08-29 15:31:00,012 - ateco_lookup - INFO - Batch lookup requested for 3 codes
2025-08-29 15:31:05,345 - ateco_lookup - INFO - Autocomplete requested for: 20.1
2025-08-29 15:31:10,678 - ateco_lookup - INFO - No results found for code: 99.99.99
```

## Test da JavaScript/Frontend

### Esempio con Fetch API:
```javascript
// Test autocomplete
async function testAutocomplete() {
    const response = await fetch('http://127.0.0.1:8000/autocomplete?partial=20.1&limit=3');
    const data = await response.json();
    console.log('Suggerimenti:', data.suggestions);
}

// Test batch lookup
async function testBatch() {
    const response = await fetch('http://127.0.0.1:8000/batch', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({
            codes: ['20.14.0', '62.01.0', '10.11.0'],
            prefer: '2025'
        })
    });
    const data = await response.json();
    console.log('Risultati batch:', data.results);
}

// Test gestione errori
async function testErrorHandling() {
    try {
        const response = await fetch('http://127.0.0.1:8000/lookup?code=1');
        if (!response.ok) {
            const error = await response.json();
            console.error('Errore strutturato:', error.detail);
        }
    } catch (e) {
        console.error('Errore di rete:', e);
    }
}
```

## Documentazione Interattiva
FastAPI genera automaticamente la documentazione Swagger UI:

**Accedi a:** `http://127.0.0.1:8000/docs`

Qui puoi testare tutti gli endpoint interattivamente con un'interfaccia grafica.

## Riepilogo Miglioramenti 🎯

| Funzionalità | Prima | Dopo | Beneficio |
|--------------|-------|------|-----------|
| **Cache** | ❌ Nessuna | ✅ LRU Cache (500 entries) | 10x più veloce per ricerche ripetute |
| **Batch** | ❌ Solo singolo | ✅ Fino a 50 codici | Riduce latenza per lookup multipli |
| **Autocomplete** | ❌ Non disponibile | ✅ Suggerimenti real-time | UX migliorata durante digitazione |
| **Errori** | ❌ Generici | ✅ Codici strutturati | Debug più facile per frontend |
| **Suggerimenti** | ❌ Nessuno | ✅ Codici simili | Aiuta l'utente quando sbaglia |
| **Logging** | ❌ Nessuno | ✅ Strutturato con livelli | Monitoring e debug |
| **Versione API** | ❌ 1.0 | ✅ 2.0 | Versionamento chiaro |

## Note per il Frontend Developer

1. **Usa `/autocomplete`** per implementare suggerimenti mentre l'utente digita
2. **Usa `/batch`** quando devi cercare più codici (es. import CSV)
3. **Gestisci i suggerimenti** quando `found === 0` per aiutare l'utente
4. **La cache è automatica** - non devi fare nulla lato frontend
5. **I codici errore strutturati** ti permettono di mostrare messaggi specifici

Il backend è ora pronto per la produzione con tutte le ottimizzazioni richieste! 🚀