# Documentazione Backend Sistema Excel Risk Assessment
## Replica PERFETTA del Sistema "Operational Risk Mapping Globale"

---

## 🎯 Panoramica del Sistema

### Cosa fa questo backend
Il backend **Excel Risk System** replica ESATTAMENTE la logica del file Excel del consulente:
1. **Gestisce 7 categorie di rischio** operative bancarie/finanziarie
2. **Filtra 191 eventi totali** in base alla categoria selezionata
3. **Applica VLOOKUP automatico** per le descrizioni degli eventi (189 mappature)
4. **Mantiene la compatibilità 100%** con il file Excel originale
5. **Fornisce API REST** per l'integrazione frontend
6. **Server Python puro** senza dipendenze esterne

### Architettura del Sistema
```
┌──────────────────────────┐
│ Operational Risk Mapping │  ← File Excel Originale
│   Globale - Copia.xlsx   │     (165KB)
└────────────┬─────────────┘
             │ Analisi righe 1000+
             ▼
┌──────────────────────────┐
│ analisi_precisa_1000.py  │  ← Script estrazione dati
├──────────────────────────┤
│ MAPPATURE_EXCEL_PERFETTE │  ← JSON con dati corretti
│        .json (69KB)      │
└────────────┬─────────────┘
             │ Implementazione
             ▼
┌──────────────────────────┐
│ excel_server_corretto.py │  ← Server Python puro
├──────────────────────────┤
│    test_finale.html      │  ← Interfaccia test
└──────────────────────────┘
```

### File del Progetto

#### 📁 FILE ESSENZIALI
| File | Descrizione | Dimensione | Ruolo |
|------|-------------|------------|-------|
| `Operational Risk Mapping Globale - Copia.xlsx` | Excel originale del consulente | 165KB | SOURCE |
| `excel_server_corretto.py` | Server API Python puro | 5KB | BACKEND |
| `test_finale.html` | Interfaccia di test | 16KB | FRONTEND |
| `MAPPATURE_EXCEL_PERFETTE.json` | Dati estratti corretti | 69KB | DATI |
| `analisi_precisa_1000.py` | Script per estrarre dati | 9KB | UTILITY |

---

## 📊 Struttura Dati Excel - LA CHIAVE

### Il Segreto: Righe 1000+ del foglio "Analisi As-IS"

**SCOPERTA FONDAMENTALE:** Tutti i dati sono nelle righe 1000+ del foglio "Analisi As-IS"!
- **Righe 1-999:** Area di lavoro per l'utente
- **Righe 1000-1300:** Tabelle nascoste per VLOOKUP e mappature

### Formula VLOOKUP Originale
```excel
=IFERROR(VLOOKUP(F5,$F$1001:$G$1200,2,0),"")
```

**Decodifica:**
- `F5`: Cella con codice evento selezionato
- `$F$1001:$G$1200`: Tabella lookup nascosta (colonne F e G)
- `2`: Ritorna seconda colonna (descrizione)
- `0`: Match esatto richiesto
- `IFERROR(...,"")`: Se non trova, mostra vuoto

### Le 7 Categorie di Rischio - MAPPATURE CORRETTE

| Categoria | Range Codici | N° Eventi | Codice "Varie" |
|-----------|--------------|-----------|----------------|
| **Damage_Danni** | 101-115 | 10 | 115 |
| **Business_disruption** | 201-299 | 20 | 299 |
| **Employment_practices_Dipendenti** | 301-399 | 22 | 399 |
| **Execution_delivery_Problemi** | 401-499 | 59 | 499 |
| **Clients_product_Clienti** | 501-599 | 44 | 599 |
| **Internal_Fraud_Frodi_interne** | 601-699 | 20 | 699 |
| **External_fraud_Frodi_esterne** | 701-799 | 16 | 799 |

**TOTALE:** 191 eventi mappati, 189 con descrizioni VLOOKUP

### Pattern dei Codici
- Ogni categoria ha un range di 100 numeri
- I codici che finiscono in **99** (o 15 per Damage) sono per "Varie/Altri"
- Esempio: 599 = "Altre cause in relazione alla relazione con il cliente"

---

## 🚀 API REST Disponibili

### Server: excel_server_corretto.py

#### Base URL
```
http://localhost:8000
```

#### Endpoints

##### 1. GET /categories
**Descrizione:** Restituisce tutte le categorie di rischio

**Response:**
```json
{
  "categories": [
    "Damage_Danni",
    "Business_disruption",
    "Employment_practices_Dipendenti",
    "Execution_delivery_Problemi_di_produzione_o_consegna",
    "Clients_product_Clienti",
    "Internal_Fraud_Frodi_interne",
    "External_fraud_Frodi_esterne"
  ],
  "total": 7
}
```

##### 2. GET /events/{category}
**Descrizione:** Restituisce eventi filtrati per categoria

**Esempio:** `/events/Clients_product_Clienti`

**Response:**
```json
{
  "category": "Clients_product_Clienti",
  "events": [
    "501 - Mancato rispetto delle regole di vendita...",
    "502 - Autorizzazione / rifiuto di un pagamento non conforme",
    // ... altri eventi fino a 599
  ],
  "total": 44
}
```

##### 3. GET /description/{event_code}
**Descrizione:** Restituisce descrizione evento (VLOOKUP)

**Esempio:** `/description/501%20-%20Mancato%20rispetto...`

**Response:**
```json
{
  "event_code": "501 - Mancato rispetto delle regole di vendita...",
  "description": "Violazione delle normative sulla vendita di prodotti..."
}
```

##### 4. GET /stats
**Descrizione:** Statistiche del sistema

**Response:**
```json
{
  "total_categories": 7,
  "total_events": 191,
  "total_descriptions": 189,
  "events_per_category": {
    "Damage_Danni": 10,
    "Business_disruption": 20,
    // ...
  }
}
```

---

## 🔄 Il Flusso Dati Completo

### 1. Estrazione dall'Excel
```
analisi_precisa_1000.py
    ↓
Legge: Righe 1000-1300 del foglio "Analisi As-IS"
    ↓
Estrae: 
  - Colonna F: Codici eventi (101, 102, ...)
  - Colonna G: Descrizioni per VLOOKUP
    ↓
Organizza per range di codici:
  - 100-199 → Damage_Danni
  - 200-299 → Business_disruption
  - etc...
    ↓
Genera: MAPPATURE_EXCEL_PERFETTE.json
```

### 2. Server Backend
```
excel_server_corretto.py
    ↓
Carica: MAPPATURE_EXCEL_PERFETTE.json
    ↓
Espone: REST API su porta 8000
    ↓
Implementa:
  - Filtering per categoria basato sui codici
  - VLOOKUP per descrizioni
  - CORS per frontend
```

### 3. Frontend Test
```
test_finale.html
    ↓
Chiama: API endpoints
    ↓
Mostra:
  1. Dropdown categorie (7 opzioni)
  2. Dropdown eventi (filtrato per range codici)
  3. Descrizione automatica (VLOOKUP)
    ↓
Replica: Comportamento Excel AL 100%
```

---

## 📋 Esempi di Mappature Corrette

### Damage_Danni (101-115)
```
101 - Disastro naturale: fuoco
102 - Meteorologico, geologico e altre catastrofi naturali
103 - Terremoto
...
110 - Danni criminali (arson, …)
115 - Altri danni a beni materiali
```

### Clients_product_Clienti (501-599)
```
501 - Mancato rispetto delle regole di vendita...
502 - Autorizzazione / rifiuto di un pagamento non conforme
...
575 - Violazione della normativa sulla vigilanza
599 - Altre cause in relazione alla relazione con il cliente...
```

---

## 🛠️ Installazione e Avvio

### Requisiti
- Python 3.x (qualsiasi versione)
- Nessuna dipendenza esterna!

### Avvio Server
```bash
# Avvia il server
python3 excel_server_corretto.py

# Server attivo su http://localhost:8000
```

### Test Frontend
1. Avvia il server sopra
2. Apri `test_finale.html` nel browser
3. Il sistema funziona ESATTAMENTE come l'Excel!

---

## 🧪 Testing e Verifica

### Test Rapido con cURL
```bash
# Lista categorie
curl http://localhost:8000/categories

# Eventi per Clients_product_Clienti
curl http://localhost:8000/events/Clients_product_Clienti

# Descrizione evento 501
curl "http://localhost:8000/description/501%20-%20Mancato%20rispetto..."

# Statistiche
curl http://localhost:8000/stats
```

### Verifica Corrispondenza con Excel
1. Apri Excel su "Analisi As-IS"
2. Seleziona categoria nella colonna E
3. Verifica che gli eventi nella colonna F corrispondano
4. Seleziona un evento e verifica che la descrizione (colonna G) sia uguale

---

## ✅ Checklist Verifica Sistema

- [x] File Excel originale presente (165KB)
- [x] MAPPATURE_EXCEL_PERFETTE.json creato (69KB)
- [x] Server avviato su porta 8000
- [x] 7 categorie con range codici corretti
- [x] 191 eventi totali mappati
- [x] 189 descrizioni VLOOKUP funzionanti
- [x] test_finale.html mostra flusso corretto
- [x] Dropdown eventi si aggiorna per categoria
- [x] Descrizione appare automaticamente
- [x] Sistema replica ESATTAMENTE l'Excel

---

## 📝 Note Tecniche Importanti

### Perché le righe 1000+?
Il consulente ha nascosto i dati di riferimento nelle righe 1000+ per:
1. **Pulizia visiva:** L'utente vede solo l'area di lavoro
2. **Protezione:** I dati non sono modificabili per errore
3. **Performance:** Le formule VLOOKUP puntano a range fissi

### Il foglio "work"
Il foglio "work" ci ha aiutato a capire la LOGICA del sistema, ma i DATI VERI sono tutti nel foglio "Analisi As-IS" dalle righe 1000+.

### Codici numerici
Ogni categoria ha il suo range di 100 numeri:
- Facilita l'ordinamento
- Permette raggruppamenti logici
- Il codice xx99 (o 115 per Damage) è sempre per "Varie"

---

## 🎯 RISULTATO FINALE

Il sistema ora:
1. **Replica AL 100%** il comportamento dell'Excel originale
2. **Usa i dati CORRETTI** estratti dalle righe 1000+
3. **Mantiene la stessa logica** di categorie → eventi → descrizioni
4. **Funziona senza dipendenze** esterne

**Il segreto era nelle righe 1000+ del foglio "Analisi As-IS"!**