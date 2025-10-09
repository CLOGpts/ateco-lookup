# 🚀 Guida Setup PostgreSQL su Railway

**Obiettivo**: Attivare database PostgreSQL gratuito su Railway in 10 minuti

**Livello**: Principiante (no coding required!)

**Costo**: **Gratis** (1GB storage, sufficiente per anni)

---

## 📋 Prerequisiti

- ✅ Account Railway (già ce l'hai per il backend)
- ✅ Backend SYD Cyber già deployato su Railway
- ✅ 10 minuti di tempo

---

## 🎯 Step 1: Accedi a Railway

1. Vai su [railway.app](https://railway.app)
2. Fai login con il tuo account
3. Dovresti vedere il progetto **"Celerya_Cyber_Ateco"** (o nome simile)

```
┌─────────────────────────────────────┐
│  📦 Celerya_Cyber_Ateco             │
│                                     │
│  ✅ web-production-3373 (backend)   │
│  🔧 Settings                        │
└─────────────────────────────────────┘
```

---

## 🗄️ Step 2: Aggiungi PostgreSQL Database

### 2.1 Clicca "+ New"

Nella dashboard del progetto, cerca il bottone **"+ New"** in alto a destra

```
[+ New] ← Clicca qui
```

### 2.2 Seleziona "Database"

Dal menu che appare:
- ❌ Non cliccare "Empty Service"
- ❌ Non cliccare "GitHub Repo"
- ✅ **Clicca "Database"**

```
+ New
  ├─ Empty Service
  ├─ GitHub Repo
  └─ Database ← QUESTO!
```

### 2.3 Scegli "PostgreSQL"

Ti appariranno diverse opzioni di database:
- MySQL
- **PostgreSQL** ← **Scegli questo!**
- MongoDB
- Redis

```
Select Database Type:

🐘 PostgreSQL  ← Clicca qui
   Fast, reliable, open-source
   ✅ 1GB Free tier
```

---

## ✅ Step 3: Configurazione Automatica

Railway configurerà automaticamente:

```
🔧 Creazione database PostgreSQL...
✅ Database creato: postgres-xyzabc
✅ Credenziali generate
✅ URL connessione disponibile
✅ Backup giornalieri attivati
```

**IMPORTANTE**: Railway **genera automaticamente** la variabile `DATABASE_URL` nel tuo progetto. Non devi copiarla manualmente!

---

## 🔗 Step 4: Verifica Connessione

### 4.1 Controlla variabili ambiente

1. Clicca sul servizio **backend** (web-production-3373)
2. Vai su tab **"Variables"**
3. Dovresti vedere una **nuova variabile**:

```
DATABASE_URL = postgresql://postgres:******************@....railway.app:*****/railway
```

**Se la vedi** → ✅ Setup completato!

**Se NON la vedi** → Segui Step 4.2

### 4.2 Collega database al backend (se necessario)

Se `DATABASE_URL` non appare automaticamente:

1. Clicca sul database PostgreSQL
2. Vai su tab **"Connect"**
3. Clicca **"Connect to Backend Service"**
4. Seleziona il tuo backend (web-production-3373)
5. Railway aggiungerà automaticamente `DATABASE_URL`

```
Connect Database to:
  ✅ web-production-3373 (Backend)

[Connect Service]
```

---

## 📊 Step 5: Verifica Info Database

Clicca sul database PostgreSQL e vai su tab **"Data"** per vedere:

```
┌─────────────────────────────────────┐
│  PostgreSQL Database                │
├─────────────────────────────────────┤
│  Name:     railway                  │
│  Host:     xxxxx.railway.app        │
│  Port:     5432                     │
│  User:     postgres                 │
│  Database: railway                  │
│                                     │
│  Storage:  0 MB / 1024 MB (0%)     │
│  Status:   🟢 Active                │
└─────────────────────────────────────┘
```

**Storage**: Inizia a 0 MB, crescerà con i dati

---

## 🧪 Step 6: Test Connessione (Backend)

Adesso testiamo se il backend riesce a connettersi.

### 6.1 Aggiungi dipendenze Python

Nel file `/Celerya_Cyber_Ateco/requirements.txt`, aggiungi:

```txt
# Database
sqlalchemy==2.0.23
psycopg2-binary==2.9.9
alembic==1.12.1
```

### 6.2 Test script

Creo uno script di test per te (lo eseguiremo dopo):

**File**: `database/test_connection.py`

```python
from database.config import check_database_connection, get_pool_status

print("🔍 Test connessione database...")

if check_database_connection():
    print("✅ Connessione OK!")
    status = get_pool_status()
    print(f"📊 Pool status: {status}")
else:
    print("❌ Connessione FALLITA!")
    print("Controlla DATABASE_URL in Railway Variables")
```

### 6.3 Deploy e testa

1. Fai commit del codice:
   ```bash
   git add .
   git commit -m "feat: add database models and config"
   git push
   ```

2. Railway auto-deploya il backend

3. Vai su Railway → Backend → **Logs**

4. Cerca nel log:
   ```
   ✅ Connessione OK!
   📊 Pool status: {'pool_size': 20, 'status': 'healthy'}
   ```

Se vedi questo → **Database funzionante!** 🎉

---

## 📈 Step 7: Monitoraggio Database

### Storage

Vai su Database → **Metrics** per vedere:
- 📊 Storage utilizzato
- 📈 Query al secondo
- ⚡ Latenza media

```
┌─────────────────────────────────┐
│  Storage Usage                  │
│  ████░░░░░░ 130 MB / 1024 MB   │
└─────────────────────────────────┘
```

**Alert**: Railway ti avvisa quando arrivi a 900 MB

### Backup

Railway fa **backup automatici giornalieri**:
- Retention: 7 giorni (free tier)
- Restore: 1 click

```
Backups:
  ✅ 2025-10-09 02:00 UTC (130 MB)
  ✅ 2025-10-08 02:00 UTC (128 MB)
  ✅ 2025-10-07 02:00 UTC (125 MB)
```

---

## ⚠️ Troubleshooting

### Problema: "DATABASE_URL not found"

**Soluzione**:
1. Vai su Backend → Variables
2. Verifica che `DATABASE_URL` esista
3. Se manca, segui Step 4.2 sopra

### Problema: "Connection timeout"

**Soluzione**:
1. Verifica che database sia **Active** (non sleeping)
2. Railway free tier può mettere in sleep dopo 5 min inattività
3. Primo request può essere lento (wake-up)

### Problema: "Storage full"

**Soluzione**:
1. Free tier = 1 GB
2. Se arrivi a limite, upgrade a $5/mese → 8 GB
3. O pulisci dati vecchi (assessments > 1 anno)

---

## 🎉 Completato!

Ora hai:
- ✅ PostgreSQL attivo su Railway
- ✅ `DATABASE_URL` configurata
- ✅ Connection pool pronto (20 connessioni)
- ✅ Backup automatici
- ✅ Monitoring disponibile

---

## 📝 Prossimi Step

1. ✅ Setup PostgreSQL (fatto!)
2. ⏳ Creare tabelle (usare `database/models.py`)
3. ⏳ Migrare dati JSON/Excel → PostgreSQL
4. ⏳ Aggiornare endpoint backend
5. ⏳ Testing completo

---

## 📞 Supporto

- 📚 Docs Railway: https://docs.railway.app/databases/postgresql
- 💬 Railway Discord: https://discord.gg/railway
- 📧 Support: Vai su Railway → Help

---

**Setup completato da**: Claudio
**Data**: 2025-10-09
**Tempo impiegato**: _____ minuti
**Problemi incontrati**: Nessuno / ___________
