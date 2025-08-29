# 📋 ISTRUZIONI PER BACKEND PYTHON - ESTRAZIONE VISURA CAMERALE

## 🎯 Contesto
Il frontend React ha già un sistema di upload/drag&drop funzionante. Dobbiamo solo creare il backend Python che riceve il PDF della visura e estrae i dati.

## 📦 Cosa deve fare il Backend

### 1. Creare endpoint FastAPI
```python
@app.post("/api/extract-visura")
async def extract_visura(file: UploadFile = File(...)):
    """
    Riceve un PDF di visura camerale e restituisce i dati estratti
    """
```

### 2. Estrarre questi 4 dati chiave:

#### A. CODICI ATECO
- **Dove trovarli**: Sezione "ATTIVITÀ", "CODICE ATECO", o "ATTIVITÀ ECONOMICA"
- **Pattern regex**: `\d{2}\.\d{2}(?:\.\d{1,2})?`
- **Esempio**: "62.01.00", "47.73.20"
- **Output**: Lista di tutti i codici trovati

#### B. OGGETTO SOCIALE / MISSION AZIENDALE
- **Dove trovarlo**: Sezione "OGGETTO SOCIALE" o "ATTIVITÀ"
- **Cosa estrarre**: Testo completo fino a "CAPITALE SOCIALE" o fine sezione
- **Pulizia**: Rimuovere a capo multipli, limitare a 1000 caratteri
- **Output**: Stringa di testo pulita

#### C. SEDI (Legale + Unità Locali)
- **Sede Legale**: Dopo "SEDE LEGALE" o "SEDE"
- **Unità Locali**: Sezione "UNITÀ LOCALI" o "UL"
- **Pattern indirizzo**: Via/Piazza/Corso + numero + CAP + Città
- **Output**: Oggetto con sede_legale e array unita_locali

#### D. TIPO BUSINESS (B2B/B2C/Misto)
- **Come inferirlo**: Analizzare l'oggetto sociale
- **Keywords B2B**: "per terzi", "alle imprese", "consulenza", "servizi professionali", "ingrosso"
- **Keywords B2C**: "al dettaglio", "consumatori", "retail", "negozio", "e-commerce"
- **Output**: "B2B", "B2C" o "B2B/B2C"

## 🛠️ Stack Tecnico Richiesto

```bash
pip install fastapi uvicorn python-multipart pdfplumber pandas pyyaml
```

### Librerie chiave:
- **pdfplumber**: Per estrarre testo con posizionamento dal PDF
- **re (regex)**: Per pattern matching
- **fastapi**: Per l'API REST
- **python-multipart**: Per gestire upload file

## 📝 Struttura Response JSON

```json
{
  "success": true,
  "data": {
    "codici_ateco": ["62.01.00", "62.02.00"],
    "oggetto_sociale": "Sviluppo software e consulenza informatica...",
    "sedi": {
      "sede_legale": {
        "indirizzo": "Via Roma 123",
        "cap": "00100",
        "citta": "Roma",
        "provincia": "RM"
      },
      "unita_locali": [
        {
          "indirizzo": "Via Milano 45",
          "cap": "20100",
          "citta": "Milano",
          "provincia": "MI"
        }
      ]
    },
    "tipo_business": "B2B",
    "confidence": 0.95
  },
  "extraction_method": "regex",  // o "ai" se usato fallback
  "processing_time_ms": 234
}
```

## 🔄 Logica di Estrazione

### STEP 1: Tentare estrazione con REGEX (veloce e preciso)
```python
def extract_with_regex(pdf_text):
    # 1. Estrai codici ATECO con pattern
    # 2. Trova oggetto sociale tra keywords
    # 3. Estrai indirizzi con pattern CAP
    # 4. Inferisci business type da keywords
    return data, confidence
```

### STEP 2: Se confidence < 0.7, usa AI come fallback
```python
def extract_with_ai(pdf_text):
    # Solo se regex fallisce o confidence bassa
    # Usa Gemini API con prompt strutturato
    # Costa di più ma funziona su PDF complessi
    return data, confidence
```

## 🎯 Priorità Implementazione

1. **PRIMA**: Fai funzionare l'estrazione base con regex
2. **POI**: Aggiungi validazione e pulizia dati
3. **INFINE**: Implementa fallback AI per casi edge

## 🧪 Test Cases da Provare

1. **Visura standard** InfoCamere (PDF strutturato)
2. **Visura con più codici ATECO** 
3. **Visura con più unità locali**
4. **Visura scansionata** (OCR necessario - fase 2)

## ⚡ Performance Target

- Estrazione regex: < 500ms
- Estrazione con AI: < 3000ms
- Dimensione max PDF: 20MB
- Concurrent requests: 10

## 🔗 Integrazione con Frontend

Il frontend chiamerà l'endpoint così:
```javascript
const formData = new FormData();
formData.append('file', pdfFile);

const response = await fetch('http://localhost:8000/api/extract-visura', {
  method: 'POST',
  body: formData
});

const data = await response.json();
// Popola automaticamente i campi nel form
```

## 🚨 Gestione Errori

Restituire sempre JSON strutturato anche in caso di errore:
```json
{
  "success": false,
  "error": {
    "code": "INVALID_PDF",
    "message": "Il file non è una visura camerale valida",
    "details": "Impossibile trovare sezione CODICE ATECO"
  }
}
```

## 📊 Logging e Monitoring

Loggare:
- Tempo di elaborazione
- Metodo usato (regex/ai)
- Successo/fallimento
- Dimensione file
- Numero campi estratti

## 🔒 Sicurezza

1. Validare che sia un PDF valido
2. Limitare dimensione a 20MB
3. Pulire file temporanei dopo elaborazione
4. Non salvare permanentemente dati sensibili
5. Sanitizzare output prima di restituirlo

## 💡 Suggerimenti Extra

- Usa `functools.lru_cache` per cachare regex compilate
- Processa pagine in parallelo con `asyncio` se PDF lungo
- Considera `pypdfium2` come alternativa più veloce a pdfplumber
- Per OCR futuro: `pytesseract` o `easyocr`

---

## 📦 Codice Starter

```python
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import pdfplumber
import re
import time
from typing import Dict, List, Optional
import os
import tempfile

app = FastAPI()

# CORS per frontend React
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)

class VisuraExtractor:
    def __init__(self):
        # Compila regex una volta sola
        self.patterns = {
            'ateco': re.compile(r'\d{2}\.\d{2}(?:\.\d{1,2})?'),
            'cap': re.compile(r'\b\d{5}\b'),
            'piva': re.compile(r'(?:P\.?\s?IVA|Partita IVA)[:\s]*(\d{11})'),
        }
        
        self.b2b_keywords = ['per terzi', 'consulenza', 'ingrosso', 'industriale']
        self.b2c_keywords = ['dettaglio', 'consumatori', 'retail', 'negozio']
    
    def extract_from_pdf(self, pdf_path: str) -> Dict:
        start_time = time.time()
        
        try:
            with pdfplumber.open(pdf_path) as pdf:
                # Unisci tutto il testo
                full_text = ""
                for page in pdf.pages:
                    text = page.extract_text()
                    if text:
                        full_text += text + "\n"
                
                # Estrai dati
                result = {
                    'success': True,
                    'data': {
                        'codici_ateco': self.extract_ateco(full_text),
                        'oggetto_sociale': self.extract_oggetto_sociale(full_text),
                        'sedi': self.extract_sedi(full_text),
                        'tipo_business': self.infer_business_type(full_text),
                        'confidence': 0.9
                    },
                    'extraction_method': 'regex',
                    'processing_time_ms': int((time.time() - start_time) * 1000)
                }
                
                # Valida risultati
                if not result['data']['codici_ateco']:
                    result['data']['confidence'] = 0.3
                    # TODO: Qui potresti chiamare AI come fallback
                
                return result
                
        except Exception as e:
            return {
                'success': False,
                'error': {
                    'code': 'EXTRACTION_ERROR',
                    'message': str(e)
                }
            }
    
    def extract_ateco(self, text: str) -> List[str]:
        # Implementa estrazione ATECO
        # ...
        pass
    
    def extract_oggetto_sociale(self, text: str) -> str:
        # Implementa estrazione oggetto sociale
        # ...
        pass
    
    def extract_sedi(self, text: str) -> Dict:
        # Implementa estrazione sedi
        # ...
        pass
    
    def infer_business_type(self, text: str) -> str:
        # Implementa inferenza tipo business
        # ...
        pass

@app.post("/api/extract-visura")
async def extract_visura(file: UploadFile = File(...)):
    # Validazione
    if file.content_type != 'application/pdf':
        raise HTTPException(400, "Solo file PDF sono accettati")
    
    if file.size > 20 * 1024 * 1024:  # 20MB
        raise HTTPException(400, "File troppo grande (max 20MB)")
    
    # Salva temporaneamente
    with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as tmp:
        content = await file.read()
        tmp.write(content)
        tmp_path = tmp.name
    
    try:
        # Estrai dati
        extractor = VisuraExtractor()
        result = extractor.extract_from_pdf(tmp_path)
        return result
    finally:
        # Cleanup
        os.unlink(tmp_path)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
```

---

**IMPORTANTE**: Questo backend è progettato per essere indipendente e può girare su qualsiasi server Python. Il frontend React chiamerà semplicemente l'endpoint via HTTP.