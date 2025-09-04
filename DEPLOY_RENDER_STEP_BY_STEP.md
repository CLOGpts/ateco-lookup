# 🚀 DEPLOY SU RENDER - GUIDA PASSO PASSO

## ✅ STATO DEL SISTEMA
- **Codice Python**: ✅ Verificato e testato
- **Logica estrazione**: ✅ Tutti i test passati (100%)
- **Compatibilità**: ✅ JSON compatibile con frontend
- **Isolamento**: ✅ Non tocca altri sistemi

---

## 📋 CHECKLIST PRE-DEPLOY

- [ ] Hai accesso a dashboard.render.com
- [ ] Hai il servizio `ateco-lookup` nella dashboard
- [ ] Hai i file pronti:
  - `backend_fix_visura.py`
  - `backend_requirements.txt`

---

## 🔧 ISTRUZIONI PASSO-PASSO

### PASSO 1: Accedi a Render
1. Vai su https://dashboard.render.com
2. Effettua il login
3. Trova il servizio `ateco-lookup` (o il nome del tuo servizio)

### PASSO 2: Aggiorna i file nel repository

#### Opzione A: Se usi GitHub
1. Nel tuo repository GitHub:
   - Rinomina `backend_fix_visura.py` → `app.py` (o `main.py`)
   - Rinomina `backend_requirements.txt` → `requirements.txt`
   - Fai commit e push

#### Opzione B: Upload diretto su Render
1. Nel dashboard Render, vai su "Environment"
2. Clicca "Manual Deploy"
3. Carica i file:
   - `app.py` (il backend_fix_visura.py rinominato)
   - `requirements.txt`

### PASSO 3: Configura le variabili d'ambiente (se necessario)
```
PORT=5000  (o lascia che Render lo gestisca)
```

### PASSO 4: Avvia il deploy
1. Clicca su "Deploy" o "Manual Deploy"
2. Aspetta che il build finisca (2-3 minuti)
3. Controlla i log per errori

### PASSO 5: Verifica il deploy

#### Test 1: Health Check
```bash
curl https://[tuo-servizio].onrender.com/health
```
Dovrebbe rispondere:
```json
{"status": "healthy", "version": "STRICT-1.0"}
```

#### Test 2: Upload Visura (con file PDF di test)
```bash
curl -X POST https://[tuo-servizio].onrender.com/api/extract-visura \
  -F "file=@test_visura.pdf"
```

---

## 🔍 TROUBLESHOOTING

### Errore: "Module not found"
**Soluzione**: Verifica che `requirements.txt` contenga:
```
Flask==2.3.2
flask-cors==4.0.0
pdfplumber==0.10.3
gunicorn==21.2.0
```

### Errore: "Port already in use"
**Soluzione**: Lascia che Render gestisca la porta automaticamente

### Errore: "500 Internal Server Error"
**Soluzione**: Controlla i log su Render:
1. Dashboard → Logs
2. Cerca errori Python
3. Verifica che il PDF sia valido

---

## ✅ CONFERMA SUCCESSO

Il deploy è riuscito quando:
1. ✅ Health check risponde "healthy"
2. ✅ Upload visura NON dà errore 500
3. ✅ Ritorna JSON con i 3 campi (o null)
4. ✅ Confidence è 0, 33, 66 o 100

---

## 🎯 OUTPUT ATTESO

```json
{
  "success": true,
  "partita_iva": "12345678901",     // o null
  "codici_ateco": [{
    "codice": "62.01",
    "descrizione": "Produzione di software",
    "principale": true
  }],
  "oggetto_sociale": "Produzione e commercializzazione...",  // o null
  "confidence": 1.0,  // 0, 0.33, 0.66, 1.0
  "extraction_method": "backend"
}
```

---

## ⚠️ IMPORTANTE

**QUESTO FIX NON TOCCA:**
- ❌ Altri endpoint ATECO
- ❌ Il sistema locale
- ❌ Il server Excel
- ❌ Il frontend

**TOCCA SOLO:**
- ✅ L'endpoint `/api/extract-visura` su Render

---

## 📞 SUPPORTO

Se hai problemi:
1. Controlla questa guida
2. Verifica i log su Render
3. Testa in locale prima:
```bash
python3 backend_fix_visura.py
```

---

✅ **SISTEMA TESTATO E PRONTO PER IL DEPLOY**