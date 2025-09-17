# 📚 GUIDA DI STUDIO PER PERCLO
## Il Tuo Sistema Spiegato Semplice - Come Funziona Tutto

---

# 🌳 ALBERO DEI FILE - COSA C'È E A COSA SERVE

```
Celerya_Cyber_Ateco/
│
├── 🚀 main.py                    ← IL CERVELLO! Tutto parte da qui
│                                   (Il server che risponde alle richieste)
│
├── 📊 MAPPATURE_EXCEL_PERFETTE.json ← LA MEMORIA! Tutti i dati dei rischi
│                                      (191 eventi di rischio catalogati)
│
├── ⚙️ Procfile                   ← ISTRUZIONI per Railway
│                                   (Dice: "Avvia main.py quando parti")
│
├── 📋 requirements.txt            ← LISTA DELLA SPESA per Python
│                                   (Dice: "Installa fastapi e uvicorn")
│
├── 📊 tabella_ATECO.xlsx         ← DATABASE codici attività economiche
│                                   (Es: 62.01 = Sviluppo Software)
│
└── 📁 _ARCHIVIO_DOC_OBSOLETE/    ← CASSETTO delle cose vecchie
                                    (File che non usiamo più)
```

---

# 🧠 COME FUNZIONA - SPIEGATO FACILE

## 1. IL CONCETTO BASE

Immagina il tuo sistema come un **RISTORANTE**:

```
CLIENTE (Frontend)          CAMERIERE (main.py)         CUCINA (Dati)
    │                             │                          │
    ├──"Vorrei il menu"──────────>│                          │
    │                             ├──Cerca nel libro────────>│
    │                             │<──Ecco i piatti──────────│
    │<──"Ecco il menu signore"────│                          │
```

---

# 📖 LE PARTI FONDAMENTALI DEL CODICE

## 1️⃣ **main.py - IL CERVELLO**

```python
# PARTE 1: IMPORTA GLI STRUMENTI
from fastapi import FastAPI     # <- Questo crea il "cameriere"
import json                     # <- Questo legge i file JSON

# PARTE 2: CREA L'APPLICAZIONE
app = FastAPI()                 # <- Nasce il cameriere!

# PARTE 3: CARICA I DATI
with open("MAPPATURE_EXCEL_PERFETTE.json") as f:
    DATI = json.load(f)         # <- Memorizza tutti i rischi

# PARTE 4: CREA GLI ENDPOINT (le "orecchie" che ascoltano)
@app.get("/categories")         # <- Quando chiedi /categories
def get_categories():
    return {"categories": [...]} # <- Ti risponde con le categorie
```

### 🔑 CONCETTI CHIAVE:
- **@app.get("/nome")** = "Quando qualcuno chiede /nome, fai questo"
- **def funzione()** = "Questa è la ricetta di cosa fare"
- **return {...}** = "Rispondi con questi dati"

---

## 2️⃣ **GLI ENDPOINT - LE DOMANDE CHE PUOI FARE**

Pensa agli endpoint come **DOMANDE** che il frontend può fare:

```
DOMANDA                          RISPOSTA
────────────────────────────────────────────────────
GET /categories        →         ["Danni", "Frodi", "Clienti"...]
"Quali categorie hai?"           Lista delle 7 categorie

GET /events/Danni      →         ["101-Incendio", "102-Terremoto"...]
"Quali eventi nei Danni?"       Lista eventi di quella categoria

GET /description/101   →         "Un incendio che causa danni..."
"Cos'è l'evento 101?"           Descrizione dettagliata

POST /save-risk        →         {"score": 75, "level": "ALTO"}
"Salva questa valutazione"      Calcola e ritorna il punteggio
```

---

# 💡 LOGICHE PRINCIPALI - COME RAGIONA

## 1. LOGICA DELLE CATEGORIE

```
I rischi sono divisi in 7 CASSETTI:
┌─────────────┐
│ 1. DANNI    │ <- Eventi 101-199 (Incendi, terremoti...)
├─────────────┤
│ 2. BUSINESS │ <- Eventi 201-299 (Interruzioni, blackout...)
├─────────────┤
│ 3. DIPENDEN.│ <- Eventi 301-399 (Scioperi, infortuni...)
├─────────────┤
│ 4. PRODUZ.  │ <- Eventi 401-499 (Errori, ritardi...)
├─────────────┤
│ 5. CLIENTI  │ <- Eventi 501-599 (Reclami, cause...)
├─────────────┤
│ 6. FRODI INT│ <- Eventi 601-699 (Furti interni...)
├─────────────┤
│ 7. FRODI EXT│ <- Eventi 701-799 (Hacker, truffe...)
└─────────────┘
```

## 2. LOGICA DEL RISK SCORE (Punteggio 0-100)

```python
# COME CALCOLA IL RISCHIO:

PUNTEGGIO = 0

# 1. IMPATTO FINANZIARIO (max 40 punti)
if perdita == "1-10K€":
    PUNTEGGIO += 10
if perdita == "100-500K€":
    PUNTEGGIO += 25

# 2. PERDITA ECONOMICA (max 30 punti)
if colore == "Verde":
    PUNTEGGIO += 5
if colore == "Rosso":
    PUNTEGGIO += 30

# 3. ALTRI IMPATTI (+10 ciascuno)
if danneggia_immagine:
    PUNTEGGIO += 10
if problemi_legali:
    PUNTEGGIO += 10

# RISULTATO FINALE
if PUNTEGGIO > 70:
    return "CRITICO 🔴"
elif PUNTEGGIO > 50:
    return "ALTO 🟠"
elif PUNTEGGIO > 30:
    return "MEDIO 🟡"
else:
    return "BASSO 🟢"
```

---

# 🔄 COME COMUNICANO FRONTEND E BACKEND

## IL DIALOGO TIPO:

```
FRONTEND (Browser)                    BACKEND (Railway)
─────────────────────────────────────────────────────────

1. "Dammi le categorie"
   GET /categories         ───────>   main.py legge MAPPATURE_EXCEL
                          <───────    {"categories": [7 categorie]}

2. "Mostrami eventi Danni"
   GET /events/Danni      ───────>   Filtra eventi 101-199
                          <───────    {"events": [10 eventi]}

3. "Calcola questo rischio"
   POST /save-risk-assessment ────>  Applica formula punteggio
   {dati del form}        <───────   {"score": 65, "level": "ALTO"}
```

---

# 🚀 COME SI AVVIA TUTTO

## SU RAILWAY (PRODUZIONE):

```
1. Tu fai: git push
              ↓
2. GitHub notifica Railway
              ↓
3. Railway legge Procfile ("Avvia main.py")
              ↓
4. Railway esegue: uvicorn main:app
              ↓
5. Il server è ONLINE! 🎉
   https://web-production-3373.up.railway.app
```

## SUL TUO PC (SVILUPPO):

```bash
# 1. Installa le dipendenze
pip install fastapi uvicorn

# 2. Avvia il server
python main.py

# 3. Apri il browser
http://localhost:8000
```

---

# 📝 CONCETTI DA RICORDARE

## VOCABOLARIO ESSENZIALE:

| Termine | Significato | Esempio |
|---------|-------------|---------|
| **Endpoint** | Un "indirizzo" che risponde | `/categories` |
| **GET** | "Dammi qualcosa" | GET /events/Danni |
| **POST** | "Ti mando dei dati" | POST /save-risk |
| **JSON** | Formato dati (come una lista) | {"nome": "valore"} |
| **API** | Il "menu" di cosa puoi chiedere | Tutti gli endpoint |
| **CORS** | Permesso di parlare tra siti | Abilitato per tutti |
| **Deploy** | Pubblicare online | git push → Railway |
| **Mock** | Dati finti per testare | Visura sempre "12345" |

---

# 🎯 COSA PUOI FARE TU

## PER MODIFICARE:

1. **Cambiare una risposta:**
```python
# In main.py, trova l'endpoint
@app.get("/health")
def health():
    return {"status": "healthy"}  # <- Cambia qui!
```

2. **Aggiungere un endpoint:**
```python
# Aggiungi in main.py
@app.get("/mio-endpoint")
def mio_endpoint():
    return {"messaggio": "Ciao!"}
```

3. **Modificare il calcolo rischio:**
```python
# Cerca in main.py la funzione save_risk_assessment
# Cambia i valori dei punti
```

## PER COMUNICARE CON ME:

Quando hai problemi, dimmi:
1. **Cosa volevi fare**: "Aggiungere un campo"
2. **Cosa hai provato**: "Ho modificato main.py"
3. **Cosa è successo**: "Errore 500"
4. **Cosa vedi nei log**: "TypeError line 45"

---

# 🆘 PROBLEMI COMUNI E SOLUZIONI

## Problema: "Il backend non risponde"
**Soluzione:**
1. Controlla Railway sia "Active"
2. Verifica URL: `https://web-production-3373.up.railway.app`
3. Guarda i log su Railway

## Problema: "Modifico ma non cambia nulla"
**Soluzione:**
1. Hai fatto `git add` + `git commit`?
2. Hai fatto `git push`?
3. Aspetta 2 minuti per il deploy

## Problema: "Errore CORS"
**Soluzione:**
- Il CORS è già abilitato per tutti (*)
- Verifica l'URL sia giusto
- Controlla che il metodo sia corretto (GET vs POST)

---

# 📚 RIEPILOGO PER STUDIARE

## I 3 FILE PIÙ IMPORTANTI:

1. **main.py** = Il cervello che gestisce tutto
2. **MAPPATURE_EXCEL_PERFETTE.json** = I dati di tutti i rischi
3. **Procfile** = Dice a Railway come avviare

## LE 3 COSE DA CAPIRE:

1. **Frontend CHIEDE** → **Backend RISPONDE**
2. **GET = dammi** / **POST = ti mando**
3. **JSON = il linguaggio** che parlano

## I 3 COMANDI DA RICORDARE:

```bash
git add .            # Prepara modifiche
git commit -m "..."  # Conferma modifiche
git push            # Pubblica su Railway
```

---

# 🎓 ESERCIZI PER IMPARARE

## LIVELLO 1 - FACILE:
1. Cambia il messaggio di `/health`
2. Aggiungi un endpoint `/about` che ritorna il tuo nome

## LIVELLO 2 - MEDIO:
1. Aggiungi una nuova categoria di rischio
2. Modifica i punti del risk score

## LIVELLO 3 - AVANZATO:
1. Crea un endpoint che conta gli eventi totali
2. Aggiungi un campo al risk assessment

---

# 💭 DOMANDE CHE PUOI FARMI

- "Come faccio a..."
- "Perché questo non funziona..."
- "Cosa significa..."
- "Puoi spiegarmi meglio..."

Non aver paura di chiedere! Sono qui per aiutarti a imparare!

---

**Questa guida è per TE, Perclo!**
Aggiornata il: 16/12/2024
Creata con ❤️ per aiutarti a capire il tuo sistema