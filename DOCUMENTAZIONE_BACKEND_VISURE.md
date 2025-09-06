# Documentazione Backend Estrazione Visure Camerali
## Sistema STRICT - Solo 3 Campi Fondamentali

---

## 🎯 Panoramica del Sistema

### Cosa fa questo backend
Il backend **Visura Extractor STRICT** è un sistema Python bulletproof che:
1. **Estrae SOLO 3 campi fondamentali** da PDF di visure camerali
2. **MAI inventa dati** - meglio NULL che dati sbagliati
3. **Zero crash garantiti** - gestione errori totale
4. **Confidence REALE** basata sui campi effettivamente trovati
5. **Fallback multipli** per librerie PDF (pdfplumber → PyPDF2 → pdfminer)
6. **Validazione rigorosa** di ogni campo estratto

### Architettura del Sistema
```
┌─────────────────────┐
│   Frontend (UI)     │
└──────────┬──────────┘
           │ POST /api/extract-visura
           ▼
┌─────────────────────┐
│   FastAPI Server    │ ← ateco_lookup.py
├─────────────────────┤
│  Estrazione STRICT  │ ← Integrata direttamente
├─────────────────────┤
│ 1. Partita IVA      │ ← 11 cifre validate
│ 2. Codice ATECO     │ ← Formato XX.XX
│ 3. Oggetto Sociale  │ ← Min 30 caratteri
└─────────────────────┘
```

### Tecnologie utilizzate
- **Python 3.7+**: Linguaggio principale
- **pdfplumber**: Estrazione testo primaria (con fallback)
- **PyPDF2**: Fallback per PDF complessi
- **pdfminer.six**: Ultimo fallback disponibile
- **regex (re)**: Pattern matching rigoroso
- **FastAPI**: API REST (integrazione in ateco_lookup.py)

---

## 🔒 Sistema STRICT - I 3 Campi Fondamentali

### 1️⃣ **Partita IVA**
**Validazione:** DEVE essere esattamente 11 cifre
```python
Pattern: r'(?:Partita IVA|P\.?\s?IVA|VAT)[\s:]+(\d{11})'
Validazione: re.match(r'^\d{11}$', piva)
```
**Comportamento:**
- ✅ Trova e valida 11 cifre esatte
- ❌ Ritorna NULL se non trova o non valida
- ❌ MAI inventa o deduce

### 2️⃣ **Codice ATECO**
**Validazione:** Formato XX.XX o XX.XX.XX
```python
Pattern: r'(?:Codice ATECO|ATECO|Attività prevalente)[\s:]+(\d{2}[.\s]\d{2}(?:[.\s]\d{1,2})?)'
Validazione: re.match(r'^\d{2}\.\d{2}(?:\.\d{1,2})?$', ateco)
```
**Comportamento:**
- ✅ Estrae codice principale con formato corretto
- ✅ Normalizza separatori (spazi → punti)
- ❌ Ritorna NULL se formato non valido

### 3️⃣ **Oggetto Sociale**
**Validazione:** Minimo 30 caratteri, deve contenere parole business
```python
Parole chiave: ['produzione', 'commercio', 'servizi', 'consulenza', ...]
Lunghezza: len(oggetto) >= 30
Truncate: max 500 caratteri
```
**Comportamento:**
- ✅ Estrae descrizione attività se presente
- ✅ Valida che sia testo business reale
- ❌ Ritorna NULL se troppo corto o non pertinente

---

## 📊 Sistema di Confidence REALE

### Calcolo Confidence Score
```
Confidence = Somma dei campi trovati:
- Partita IVA trovata e valida: +33%
- Codice ATECO trovato e valido: +33%
- Oggetto Sociale trovato e valido: +34%
```

### Livelli di Confidence
| Score | Significato | Assessment |
|-------|-------------|------------|
| 100% | 3/3 campi trovati | ✅ Tutti e 3 i campi trovati e validi |
| 66-67% | 2/3 campi trovati | ⚠️ 2 campi su 3 trovati |
| 33-34% | 1/3 campi trovati | ⚠️ Solo 1 campo trovato |
| 0% | 0/3 campi trovati | ❌ Nessun campo valido trovato |

---

## 🚀 Struttura Risposta API

### Risposta Standard (Successo)
```json
{
  "success": true,
  "data": {
    "partita_iva": "12345678901",     // o null
    "codice_ateco": "62.01",           // o null
    "oggetto_sociale": "Produzione...", // o null
    "codici_ateco": [],                // array vuoto per compatibilità
    "confidence": {
      "score": 100,
      "details": {
        "partita_iva": "valid",
        "ateco": "valid",
        "oggetto_sociale": "valid"
      },
      "assessment": "✅ Tutti e 3 i campi trovati e validi"
    }
  },
  "method": "backend"
}
```

### Risposta con Campi Mancanti
```json
{
  "success": true,
  "data": {
    "partita_iva": "12345678901",
    "codice_ateco": null,              // Non trovato
    "oggetto_sociale": null,           // Non trovato
    "codici_ateco": [],
    "confidence": {
      "score": 33,
      "details": {
        "partita_iva": "valid",
        "ateco": "not_found",
        "oggetto_sociale": "not_found"
      },
      "assessment": "⚠️ Solo 1 campo trovato"
    }
  },
  "method": "backend"
}
```

### Risposta Errore (mai dovrebbe accadere)
```json
{
  "success": false,
  "error": {
    "code": "EXTRACTION_ERROR",
    "message": "Errore durante l'estrazione",
    "details": "Dettagli specifici"
  }
}
```

---

## 🛡️ Sistema Bulletproof - Zero Crash

### Gestione Errori Multilivello
```python
# LIVELLO 1: Try/except totale sulla funzione
try:
    # estrazione
except Exception as e:
    return risultato_vuoto

# LIVELLO 2: Fallback librerie PDF
try:
    pdfplumber.open(pdf)
except:
    try:
        PyPDF2.PdfReader(pdf)
    except:
        try:
            pdfminer.extract_text(pdf)
        except:
            return testo_vuoto

# LIVELLO 3: Ogni estrazione campo protetta
try:
    extract_partita_iva()
except:
    partita_iva = None
```

### Principio: Meglio NULL che Crash
- **MAI** solleva eccezioni non gestite
- **MAI** inventa dati mancanti
- **SEMPRE** ritorna struttura valida
- **SEMPRE** log errori per debug

---

## 🔧 Installazione e Configurazione

### Prerequisiti
```bash
# Python 3.7+
python --version

# Dipendenze richieste
pip install -r requirements.txt
```

### requirements.txt
```
pandas
openpyxl
fastapi
uvicorn
pyyaml
python-multipart
pdfplumber
PyPDF2
Pillow>=9.0.0
pdfminer.six>=20211012
```

### File Necessari
```
project/
├── ateco_lookup.py                      # Server API con estrazione integrata
├── visura_extractor_FINAL_embedded.py   # Modulo estrazione standalone
└── requirements.txt                     # Dipendenze
```

### Avvio Server
```bash
# Avvia il backend
python ateco_lookup.py --file master_ateco_*.xlsx --serve --port 8000
```

---

## 🧪 Testing e Debug

### Test Estrazione Diretta
```python
from visura_extractor_FINAL_embedded import VisuraExtractorFinal

extractor = VisuraExtractorFinal()
result = extractor.extract_three_fields("visura.pdf")
print(f"P.IVA: {result['data']['partita_iva']}")
print(f"ATECO: {result['data']['codice_ateco']}")
print(f"Confidence: {result['data']['confidence']['score']}%")
```

### Upload via cURL
```bash
curl -X POST http://localhost:8000/api/extract-visura \
  -F "file=@visura.pdf"
```

### Upload via JavaScript
```javascript
const formData = new FormData();
formData.append('file', pdfFile);

const response = await fetch('http://localhost:8000/api/extract-visura', {
  method: 'POST',
  body: formData
});

const result = await response.json();
if (result.success) {
  console.log('P.IVA:', result.data.partita_iva || 'Non trovata');
  console.log('ATECO:', result.data.codice_ateco || 'Non trovato');
  console.log('Confidence:', result.data.confidence.score + '%');
}
```

---

## 📝 Note Importanti per il Frontend

### Gestione Campi NULL
```javascript
// SEMPRE controllare per null
const partitaIva = result.data.partita_iva || 'Non disponibile';
const codiceAteco = result.data.codice_ateco || 'Non disponibile';
const oggettoSociale = result.data.oggetto_sociale || 'Non disponibile';

// Mostra confidence per trasparenza
const confidenceText = result.data.confidence.assessment;
const confidenceColor = result.data.confidence.score === 100 ? 'green' : 
                        result.data.confidence.score > 50 ? 'yellow' : 'red';
```

### Best Practices
1. **NON assumere** che tutti i campi siano presenti
2. **Mostrare sempre** il confidence score all'utente
3. **Permettere** inserimento manuale per campi mancanti
4. **Validare** lato client prima di salvare
5. **Considerare** confidence < 66% come "necessita revisione"

### UI Consigliata
```
┌──────────────────────────────┐
│ Estrazione Visura            │
├──────────────────────────────┤
│ P.IVA: [___________] ✅      │
│ ATECO: [_____] ❌ Non trovato │
│ Oggetto: [________] ⚠️       │
│                              │
│ Confidence: 66% ⚠️           │
│ "2 campi su 3 trovati"       │
│                              │
│ [Modifica] [Conferma]        │
└──────────────────────────────┘
```

---

## 🆘 Troubleshooting

### Problema: Tutti i campi sono NULL
**Possibili cause:**
1. PDF non è una visura camerale
2. PDF è scansionato (immagine, non testo)
3. Formato visura molto diverso dal previsto

**Soluzione:**
- Verificare che il PDF contenga testo selezionabile
- Provare con una visura camerale standard
- Controllare i log del backend per dettagli

### Problema: Confidence sempre basso
**Causa:** Il sistema trova solo 1-2 campi su 3
**Soluzione:**
- È normale per visure non standard
- Permettere all'utente di completare manualmente
- Non è un errore, è trasparenza

### Problema: P.IVA presente ma non estratta
**Verifica:**
```bash
# Controlla se il pattern matcha
grep -E "Partita IVA|P\.?\s?IVA" visura.pdf
```
**Soluzione:**
- Il formato potrebbe essere diverso
- Contattare per aggiungere nuovo pattern

---

## 🎯 Filosofia del Sistema STRICT

### Principi Fondamentali
1. **Verità > Completezza**: Meglio 1 campo certo che 3 incerti
2. **NULL > Errore**: Mai inventare dati
3. **Trasparenza**: Sempre comunicare cosa è stato trovato
4. **Robustezza**: Il sistema non deve mai crashare
5. **Semplicità**: Solo 3 campi, fatti bene

### Perché STRICT?
- **Affidabilità legale**: I dati estratti sono verificabili
- **Fiducia utente**: L'utente sa cosa è stato trovato
- **Manutenibilità**: Codice semplice e chiaro
- **Scalabilità**: Facile aggiungere validazioni

---

## 📋 Checklist Integrazione

- [ ] Backend avviato su porta 8000
- [ ] File `visura_extractor_FINAL_embedded.py` presente
- [ ] Dipendenze Python installate
- [ ] Test con visura PDF reale
- [ ] Frontend gestisce campi NULL
- [ ] UI mostra confidence score
- [ ] Possibilità editing manuale campi
- [ ] Validazione P.IVA (11 cifre) lato client
- [ ] Gestione errori implementata
- [ ] Test con visura che ritorna 0% confidence

---

## 🚀 Performance e Limiti

### Performance
- Tempo estrazione: 1-3 secondi per PDF
- Dimensione max PDF: 20MB
- Concurrent requests: gestite da FastAPI

### Limiti Noti
- Solo visure camerali italiane
- Solo testo (no OCR per immagini)
- Solo 3 campi fondamentali
- Pattern predefiniti (estendibili)

---

Il sistema STRICT è progettato per essere **affidabile**, **trasparente** e **manutenibile**. 
La filosofia "meglio NULL che sbagliato" garantisce che i dati estratti siano sempre verificabili e affidabili.

**Versione:** 2.0 STRICT
**Data:** Settembre 2024
**Maintainer:** Team Celerya