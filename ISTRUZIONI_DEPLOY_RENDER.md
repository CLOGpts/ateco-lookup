# 🚀 ISTRUZIONI PER DEPLOY SU RENDER

## ✅ COSA È STATO FATTO

Ho creato il sistema completo per estrarre dati dalle visure camerali PDF:

1. **`visura_extractor.py`** - Classe completa per estrazione dati
2. **Endpoint `/api/extract-visura`** integrato in `ateco_lookup.py`
3. **Dipendenze aggiunte** in `requirements.txt`
4. **Test di validazione** creati

## 📦 FILE DA DEPLOYARE

Assicurati che questi file siano nel repository GitHub:

- ✅ `ateco_lookup.py` (aggiornato con nuovo endpoint)
- ✅ `visura_extractor.py` (nuovo file)
- ✅ `requirements.txt` (con pdfplumber aggiunto)
- ✅ `mapping.yaml` (già esistente)
- ✅ `tabella_ATECO.xlsx` (già esistente)

## 🔧 STEPS PER IL DEPLOY

### 1. Commit e Push su GitHub

```bash
git add .
git commit -m "Aggiunto endpoint estrazione visure camerali PDF"
git push origin main
```

### 2. Render Auto-Deploy

Se hai configurato auto-deploy, Render aggiornerà automaticamente.
Altrimenti vai su Render Dashboard e clicca "Manual Deploy".

### 3. Verifica Dipendenze

Render installerà automaticamente da `requirements.txt`:
- `pdfplumber` (per estrazione PDF)
- `python-multipart` (per upload file)

## 🧪 TEST POST-DEPLOY

### Test Health Check:
```bash
curl https://ateco-lookup.onrender.com/health
```

### Test Estrazione Visura:
```bash
curl -X POST "https://ateco-lookup.onrender.com/api/extract-visura" \
  -F "file=@test_visura.pdf"
```

### Test da JavaScript:
```javascript
const formData = new FormData();
formData.append('file', pdfFile);

const response = await fetch('https://ateco-lookup.onrender.com/api/extract-visura', {
  method: 'POST',
  body: formData
});

const data = await response.json();
console.log(data);
```

## 📊 RESPONSE ATTESA

```json
{
  "success": true,
  "data": {
    "codici_ateco": ["62.01.00"],
    "oggetto_sociale": "Sviluppo software...",
    "sedi": {
      "sede_legale": {
        "indirizzo": "Via Roma 123",
        "cap": "00100",
        "citta": "Roma"
      }
    },
    "tipo_business": "B2B",
    "confidence": 0.9,
    "ateco_details": [
      {
        "code": "62.01.00",
        "description": "Produzione di software",
        "normative": ["GDPR"],
        "certificazioni": ["ISO 27001"]
      }
    ]
  },
  "extraction_method": "regex",
  "processing_time_ms": 500
}
```

## ⚠️ POSSIBILI PROBLEMI E SOLUZIONI

### Problema: "MODULE_NOT_AVAILABLE"
**Soluzione**: Verifica che `pdfplumber` sia in requirements.txt

### Problema: "INVALID_PDF"
**Soluzione**: Il file non è un PDF valido

### Problema: Confidence bassa
**Normale**: Il frontend userà Gemini AI come fallback

## 🎯 IMPORTANTE PER IL FRONTEND

Il sistema è **antifragile a 3 livelli**:

1. **Backend Python** (regex veloce) - Questo endpoint
2. **Gemini AI** (se backend fallisce) - Già implementato dal frontend
3. **Chat manuale** (ultima risorsa) - Già implementato

Quindi anche se l'estrazione non è perfetta al 100%, il sistema complessivo funzionerà!

## 📝 VARIABILI D'AMBIENTE

Non servono nuove variabili. Il sistema usa quelle esistenti.

## 🔍 MONITORING

Controlla i log su Render per vedere:
- Richieste ricevute
- Codici ATECO estratti
- Confidence score
- Eventuali errori

## ✨ FATTO!

Una volta deployato, l'endpoint sarà disponibile su:
```
https://ateco-lookup.onrender.com/api/extract-visura
```

Il frontend può iniziare a usarlo immediatamente!

---

**🍾 PRONTO PER LO CHAMPAGNE!**