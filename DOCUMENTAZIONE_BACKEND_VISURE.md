# Documentazione Backend Estrazione Visure Camerali
## Per Sviluppatore Frontend

---

## 🎯 Panoramica del Sistema

### Cosa fa questo backend
Il backend **Visura Extractor** è un sistema Python avanzato che permette di:
1. **Estrarre dati strutturati** da PDF di visure camerali
2. **Identificare automaticamente** tutti i campi principali (denominazione, P.IVA, codici ATECO, etc.)
3. **Validare e normalizzare** i dati estratti secondo standard italiani
4. **Calcolare confidence score** per l'affidabilità dell'estrazione
5. **Gestire fallback intelligenti** tra 3 versioni di estrattori
6. **Arricchire i dati ATECO** con descrizioni complete
7. **Classificare il tipo di business** automaticamente

### Architettura del Sistema
```
┌─────────────────────┐
│   Frontend (UI)     │
└──────────┬──────────┘
           │ POST /api/extract-visura
           ▼
┌─────────────────────┐
│   FastAPI Server    │  ← ateco_lookup.py
├─────────────────────┤
│  Sistema Fallback   │  ← Priorità estrattori
├─────────────────────┤
│ 1. Fixed (v3.0)     │  ← visura_extractor_fixed.py ⭐
│ 2. Power (v2.0)     │  ← visura_extractor_power.py
│ 3. Ultimate (v1.0)  │  ← visura_extractor_ultimate.py
└─────────────────────┘
```

### Tecnologie utilizzate
- **Python 3.7+**: Linguaggio principale
- **pdfplumber**: Estrazione testo da PDF con precisione
- **PyPDF2**: Fallback per PDF complessi
- **regex (re)**: Pattern matching avanzato
- **FastAPI**: API REST (integrazione con ateco_lookup.py)
- **Sistema di fallback**: 3 livelli di estrattori per massima affidabilità

---

## 🚀 Sistema di Estrazione a 3 Livelli

### Priorità e Caratteristiche

#### 1️⃣ **VisuraExtractorFixed** (PRIORITÀ MASSIMA)
**File:** `visura_extractor_fixed.py`
**Versione:** 3.0
**Caratteristiche:**
- ✅ Segue ESATTAMENTE le specifiche frontend
- ✅ Mapping completo comuni→province (114 comuni)
- ✅ Validazione province italiane (tutte 106)
- ✅ Descrizioni ATECO complete per settori principali
- ✅ Estrazione numero REA con provincia corretta
- ✅ Calcolo confidence score preciso
- ✅ Validazione finale con error reporting

**Campi estratti:**
1. Denominazione/Ragione sociale
2. Forma giuridica (SRL, SPA, SNC, etc.)
3. Partita IVA (validata 11 cifre)
4. Codice Fiscale (11-16 caratteri)
5. Sede legale (indirizzo, CAP, comune, provincia)
6. Numero REA (con provincia)
7. Codici ATECO (con descrizioni e flag principale)
8. PEC (validata formato email)
9. Email ordinaria
10. Telefono
11. Sito web
12. Capitale sociale
13. Oggetto sociale
14. Stato attività
15. Data costituzione
16. Amministratori

#### 2️⃣ **VisuraExtractorPower** (FALLBACK 1)
**File:** `visura_extractor_power.py`
**Versione:** 2.0
**Caratteristiche:**
- 🔧 Pattern regex ottimizzati per ogni campo
- 🔧 Estrazione multi-pattern per maggiore copertura
- 🔧 Classificazione automatica tipo business
- 🔧 Estrazione dati finanziari (fatturato, dipendenti)
- 🔧 Supporto sedi secondarie

**Campi aggiuntivi:**
- Fatturato
- Numero dipendenti
- Sedi secondarie/unità locali
- Data ultimo bilancio
- Tipo business (tech, manufacturing, retail, etc.)

#### 3️⃣ **VisuraExtractorUltimate** (FALLBACK 2)
**File:** `visura_extractor_ultimate.py`
**Versione:** 1.0
**Caratteristiche:**
- 🛠️ Estrazione base affidabile
- 🛠️ Dizionario ATECO esteso
- 🛠️ Logging dettagliato per debug
- 🛠️ Validazione province rigorosa

---

## 📊 Struttura Dati Risposta

### Risposta Standard (Successo)
```json
{
  "success": true,
  "confidence": 0.95,
  "data": {
    "denominazione": "CELERYA SRL",
    "forma_giuridica": "SRL",
    "partita_iva": "12345678901",
    "codice_fiscale": "12345678901",
    "sede_legale": {
      "indirizzo": "Via Roma 123",
      "cap": "10100",
      "comune": "Torino",
      "provincia": "TO"
    },
    "numero_rea": "TO-1234567",
    "codici_ateco": [
      {
        "codice": "62.01",
        "descrizione": "Produzione di software non connesso all'edizione",
        "principale": true
      },
      {
        "codice": "62.02",
        "descrizione": "Consulenza nel settore delle tecnologie dell'informatica",
        "principale": false
      }
    ],
    "pec": "info@pec.celerya.it",
    "email": "info@celerya.it",
    "telefono": "011-1234567",
    "sito_web": "www.celerya.it",
    "capitale_sociale": {
      "valore": 10000.00,
      "valuta": "EUR",
      "versato": "interamente versato"
    },
    "oggetto_sociale": "Sviluppo software, consulenza informatica...",
    "stato_attivita": "ATTIVA",
    "data_costituzione": "01/01/2020",
    "amministratori": [
      {
        "nome": "Mario Rossi",
        "carica": "Amministratore Unico",
        "codice_fiscale": "RSSMRA80A01H501Z"
      }
    ],
    "tipo_business": "technology",
    "validation_errors": []
  }
}
```

### Risposta Errore
```json
{
  "success": false,
  "error": {
    "code": "EXTRACTION_ERROR",
    "message": "Errore durante l'estrazione",
    "details": "Dettagli specifici dell'errore"
  }
}
```

### Codici di Errore
| Codice | Descrizione | Soluzione |
|--------|-------------|-----------|
| `INVALID_FILE_TYPE` | File non è PDF | Inviare solo file .pdf |
| `FILE_TOO_LARGE` | File supera 20MB | Ridurre dimensione file |
| `EMPTY_FILE` | PDF vuoto o corrotto | Verificare il file |
| `MODULE_NOT_AVAILABLE` | Estrattore non disponibile | Verificare installazione dipendenze |
| `EXTRACTION_ERROR` | Errore generico estrazione | Controllare formato visura |
| `NO_DATA_FOUND` | Nessun dato estratto | Visura non riconosciuta |

---

## 🔍 Logica di Estrazione

### 1. Flusso di Estrazione
```
PDF Upload → Validazione → Selezione Estrattore → Estrazione → Validazione → Arricchimento → Response
```

### 2. Sistema di Fallback
```python
# Ordine di priorità
1. Prova VisuraExtractorFixed (più preciso)
   ↓ (se fallisce)
2. Prova VisuraExtractorPower (più feature)
   ↓ (se fallisce)  
3. Prova VisuraExtractorUltimate (base affidabile)
   ↓ (se tutti falliscono)
4. Ritorna errore MODULE_NOT_AVAILABLE
```

### 3. Validazione Dati

#### Partita IVA
- DEVE essere esattamente 11 cifre
- Pattern: `^\d{11}$`
- Verifica checksum (opzionale)

#### Codice Fiscale
- 11 cifre (aziende) o 16 caratteri (persone)
- Pattern: `^[A-Z0-9]{11,16}$`

#### Provincia
- DEVE essere sigla valida (2 lettere)
- Verificata contro lista 106 province italiane

#### PEC/Email
- Validazione formato email standard
- PEC spesso contiene "pec" nel dominio

#### Numero REA
- Formato: `XX-1234567` (provincia-numero)
- XX deve essere provincia valida

### 4. Calcolo Confidence Score
```python
confidence = base_score * fattori:
- Denominazione trovata: +0.2
- P.IVA valida: +0.2
- Sede completa: +0.15
- ATECO trovati: +0.15
- PEC trovata: +0.1
- REA valido: +0.1
- Altri campi: +0.1
```

---

## 🛠️ Installazione e Configurazione

### Prerequisiti
```bash
# Python 3.7+
python --version

# Dipendenze richieste
pip install pdfplumber PyPDF2 Pillow pdfminer.six
```

### File Necessari
```
project/
├── ateco_lookup.py              # Server API principale
├── visura_extractor_fixed.py    # Estrattore v3 (priorità)
├── visura_extractor_power.py    # Estrattore v2 (fallback)
├── visura_extractor_ultimate.py # Estrattore v1 (fallback)
└── requirements.txt              # Dipendenze
```

### Test Estrattore Standalone
```python
# Test diretto
from visura_extractor_fixed import VisuraExtractorFixed

extractor = VisuraExtractorFixed()
result = extractor.extract_from_pdf("visura.pdf")
print(result)
```

---

## 🧪 Testing e Debug

### Endpoint di Test
```bash
# Test se l'API è attiva
curl http://localhost:8000/api/test-visura

# Response attesa
{
  "success": true,
  "message": "API funzionante! VisuraExtractorPower disponibile: true",
  "data": {
    "denominazione": "TEST CELERYA SRL",
    ...
  }
}
```

### Upload Visura
```javascript
// JavaScript/Fetch
const formData = new FormData();
formData.append('file', pdfFile);

const response = await fetch('http://localhost:8000/api/extract-visura', {
  method: 'POST',
  body: formData
});

const result = await response.json();
if (result.success) {
  console.log('Dati estratti:', result.data);
  console.log('Confidence:', result.confidence);
} else {
  console.error('Errore:', result.error);
}
```

### Esempio con Axios
```javascript
import axios from 'axios';

async function extractVisura(file) {
  const formData = new FormData();
  formData.append('file', file);
  
  try {
    const response = await axios.post(
      'http://localhost:8000/api/extract-visura',
      formData,
      {
        headers: {
          'Content-Type': 'multipart/form-data'
        }
      }
    );
    
    if (response.data.success) {
      return response.data.data;
    } else {
      throw new Error(response.data.error.message);
    }
  } catch (error) {
    console.error('Errore estrazione:', error);
    throw error;
  }
}
```

---

## 📝 Mapping Comuni → Province

Il sistema include un dizionario completo di 114+ comuni italiani mappati alle rispettive province:

```python
# Esempi di mapping
'TORINO' → 'TO'
'MILANO' → 'MI'
'ROMA' → 'RM'
'BOSCONERO' → 'TO'  # Comune specifico menzionato
```

Questo garantisce che il numero REA sia sempre formattato correttamente con la provincia giusta.

---

## 🎯 Classificazione Business Type

Il sistema classifica automaticamente il tipo di business basandosi su:
- Codici ATECO
- Oggetto sociale
- Denominazione

### Tipi di Business
| Tipo | Descrizione | Codici ATECO |
|------|-------------|--------------|
| `technology` | Software, IT, Tech | 62.xx, 63.xx |
| `manufacturing` | Produzione, Industria | 10-33 |
| `retail` | Commercio dettaglio | 47.xx |
| `wholesale` | Commercio ingrosso | 46.xx |
| `construction` | Costruzioni, Edilizia | 41-43 |
| `hospitality` | Ristorazione, Hotel | 55-56 |
| `professional` | Servizi professionali | 69-74 |
| `finance` | Servizi finanziari | 64-66 |
| `real_estate` | Immobiliare | 68.xx |
| `healthcare` | Sanità, Salute | 86-88 |
| `education` | Istruzione | 85.xx |
| `agriculture` | Agricoltura | 01-03 |
| `transport` | Trasporti | 49-53 |

---

## 🔧 Personalizzazione

### Aggiungere Nuovi Pattern
```python
# In visura_extractor_fixed.py
def _extract_campo_custom(self, text: str) -> Optional[str]:
    patterns = [
        r'(?:CAMPO CUSTOM)[\s:]+([^\n]+)',
        # Aggiungi nuovi pattern qui
    ]
    
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            return match.group(1).strip()
    return None
```

### Estendere Codici ATECO
```python
# In visura_extractor_fixed.py
self.ateco_descriptions.update({
    '95.11': 'Riparazione di computer e periferiche',
    # Aggiungi nuovi codici qui
})
```

---

## 🆘 Troubleshooting

### Problema: "No module named 'pdfplumber'"
**Soluzione:**
```bash
pip install pdfplumber PyPDF2 Pillow pdfminer.six
```

### Problema: Estrazione restituisce campi vuoti
**Possibili cause:**
1. PDF non è una visura camerale standard
2. PDF scansionato (non testo selezionabile)
3. Formato visura non riconosciuto

**Soluzione:**
- Verificare che il PDF contenga testo selezionabile
- Controllare i log per pattern non matchati
- Aggiungere nuovi pattern se necessario

### Problema: Provincia non riconosciuta
**Soluzione:**
- Verificare che la provincia sia nella lista `province_valide`
- Aggiungere mapping comune→provincia se mancante

### Problema: Confidence score basso
**Significato:** Pochi campi estratti con successo
**Soluzione:**
- Verificare qualità del PDF
- Controllare che sia una visura completa
- Aggiornare pattern di estrazione

---

## 📧 Note per l'Integrazione Frontend

### Best Practices
1. **Validazione pre-upload**: Verificare che sia un PDF prima di inviare
2. **Limite dimensione**: Max 20MB per file
3. **Loading state**: Mostrare spinner durante l'estrazione (può richiedere 2-5 secondi)
4. **Gestione errori**: Mostrare messaggi user-friendly basati su error.code
5. **Confidence threshold**: Considerare affidabili risultati con confidence > 0.7
6. **Fallback manuale**: Permettere correzione manuale dei campi estratti

### Esempio UI Flow
```
1. User seleziona PDF → Validazione client-side
2. Upload con progress bar → POST /api/extract-visura
3. Mostra risultati → Evidenzia campi con bassa confidence
4. Permetti editing → User può correggere campi
5. Salva dati validati → Invia al tuo backend
```

---

## 📋 Checklist Integrazione

- [ ] Installate dipendenze Python (`pdfplumber`, `PyPDF2`)
- [ ] Presenti tutti e 3 i file extractor
- [ ] Server FastAPI configurato e running
- [ ] CORS abilitato per il dominio frontend
- [ ] Endpoint `/api/extract-visura` raggiungibile
- [ ] Test con visura campione funzionante
- [ ] Gestione errori implementata nel frontend
- [ ] UI per upload file implementata
- [ ] Visualizzazione risultati con confidence
- [ ] Possibilità di correzione manuale

---

Il sistema è progettato per essere **robusto**, **affidabile** e **facilmente integrabile** con qualsiasi frontend moderno. Il sistema di fallback a 3 livelli garantisce massima compatibilità con diversi formati di visure camerali.