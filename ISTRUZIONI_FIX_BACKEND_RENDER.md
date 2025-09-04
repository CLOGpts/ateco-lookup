# 🚨 FIX URGENTE BACKEND RENDER - ERRORE 500

## PROBLEMA ATTUALE
Il backend su Render sta crashando con errore 500 quando si carica una visura.
L'AI deve sempre subentrare perché il backend non funziona.

## SOLUZIONE
Ho preparato un backend Python fixato con il sistema STRICT a 3 campi.

## FILE DA CARICARE SU RENDER

### 1. File principale: `backend_fix_visura.py`
Questo file contiene:
- Estrazione STRICT dei 3 campi fondamentali
- Validazione rigorosa (P.IVA 11 cifre, ATECO formato XX.XX)
- Confidence REALE (0, 33, 66, 100)
- Compatibilità totale con il frontend esistente

### 2. Dependencies: `backend_requirements.txt`
```
Flask==2.3.2
flask-cors==4.0.0
pdfplumber==0.10.3
gunicorn==21.2.0
python-dotenv==1.0.0
```

## COME DEPLOYARE SU RENDER

### Opzione A: Se hai accesso diretto a Render

1. Vai su dashboard.render.com
2. Trova il servizio `ateco-lookup`
3. Aggiorna il repository con:
   - `backend_fix_visura.py` (rinominalo in `app.py` o `main.py`)
   - `requirements.txt` (usa `backend_requirements.txt`)
4. Render farà il deploy automatico

### Opzione B: Deploy locale per test

1. Installa dependencies:
```bash
pip install -r backend_requirements.txt
```

2. Avvia il server:
```bash
python backend_fix_visura.py
```

3. Testa con:
```bash
curl -X POST http://localhost:5000/api/extract-visura \
  -F "file=@tuavisura.pdf"
```

## COSA FA IL FIX

✅ **Estrae SOLO 3 campi certi:**
- Partita IVA (validata 11 cifre)
- Codice ATECO (formato XX.XX, esclude anni)
- Oggetto Sociale (min 30 caratteri)

✅ **Confidence ONESTA:**
- 0% = Nessun campo trovato
- 33% = 1 campo trovato
- 66% = 2 campi trovati
- 100% = Tutti 3 i campi

✅ **Compatibilità Frontend:**
- Mantiene la struttura JSON attesa
- Auto-popola ATECO nella sidebar
- Nessuna modifica richiesta al frontend

## TESTING

Dopo il deploy, verifica che:
1. L'endpoint `/health` risponda con `{"status": "healthy"}`
2. L'upload di una visura non dia più errore 500
3. I 3 campi vengano estratti correttamente
4. La confidence sia sempre 0, 33, 66 o 100

## NOTE IMPORTANTI

⚠️ **NON toccare altri endpoint** - Solo `/api/extract-visura` è stato modificato
⚠️ **Meglio null che sbagliato** - Se un campo non è certo, ritorna null
⚠️ **Mai inventare dati** - La confidence deve essere REALE

## SUPPORTO

Se hai problemi:
1. Controlla i log su Render
2. Verifica che pdfplumber sia installato
3. Testa in locale prima di deployare

---

📌 **Sistema certificato STRICT - Zero tolleranza per errori**