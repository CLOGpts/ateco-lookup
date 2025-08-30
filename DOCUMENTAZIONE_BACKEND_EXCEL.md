# Documentazione Backend Sistema Excel Risk Assessment
## Replica del Sistema "Operational Risk Mapping Globale"

---

## 🎯 Panoramica del Sistema

### Cosa fa questo backend
Il backend **Excel Risk System** è un sistema che replica ESATTAMENTE la logica del file Excel del consulente:
1. **Gestisce 7 categorie di rischio** operative bancarie/finanziarie
2. **Filtra 190 eventi** in base alla categoria selezionata
3. **Applica VLOOKUP automatico** per le descrizioni degli eventi
4. **Mantiene la compatibilità** con il file Excel originale
5. **Fornisce API REST** per l'integrazione frontend
6. **Supporta due modalità server** (con/senza dipendenze esterne)

### Architettura del Sistema
```
┌──────────────────────────┐
│ Operational Risk Mapping │  ← File Excel Originale
│   Globale - Copia.xlsx   │     (165KB)
└────────────┬─────────────┘
             │ Estrazione dati
             ▼
┌──────────────────────────┐
│  extract_excel_complete  │  ← Script estrazione
├──────────────────────────┤
│ excel_data_complete.json │  ← Dati estratti
│ excel_lookups_complete   │  ← Tabelle lookup
└────────────┬─────────────┘
             │ Implementazione
             ▼
┌──────────────────────────┐
│  excel_system_final.py   │  ← Server FastAPI
│  excel_server_simple.py  │  ← Server Python puro
├──────────────────────────┤
│    test_finale.html      │  ← Interfaccia test
└──────────────────────────┘
```

### File del Progetto

#### 📁 FILE ESSENZIALI
| File | Descrizione | Dimensione | Ruolo |
|------|-------------|------------|--------|
| `Operational Risk Mapping Globale - Copia.xlsx` | Excel originale del consulente | 165KB | SOURCE |
| `excel_system_final.py` | Server API con FastAPI | 21KB | BACKEND |
| `excel_server_simple.py` | Server senza dipendenze | 10KB | BACKEND ALT |
| `test_finale.html` | Interfaccia di test | 16KB | FRONTEND |

#### 📂 FILE DI SUPPORTO (Generati)
| File | Descrizione | Generato da |
|------|-------------|-------------|
| `excel_data_complete.json` | Dati estratti dall'Excel | extract_excel_complete.py |
| `excel_lookups_complete.json` | Tabelle di lookup | extract_excel_complete.py |
| `extract_excel_complete.py` | Script di estrazione | Manuale |

#### ❌ FILE DA IGNORARE
- `~$tabella_ATECO.xlsx` - File temporaneo Excel (165 bytes)
- `tabella_ATECO.xlsx` - Progetto ATECO separato (239KB)

---

## 📊 Struttura Dati Excel

### Fogli di Lavoro Analizzati

#### 1. Foglio "Analisi As-IS" (Principale)
**Struttura:**
- **Righe 5-456:** Area dati principale (452 righe di rischi)
- **Righe 1001-1200:** Tabelle di lookup nascoste (192 eventi)
- **Colonne chiave:**
  - B: Company (nome azienda)
  - E: Categoria del rischio (dropdown)
  - F: Evento (dropdown filtrato)
  - G: Descrizione (formula VLOOKUP)

#### 2. Foglio "work" (Mappature)
**FONDAMENTALE per capire il sistema!**
```
Struttura a colonne alternate:
┌────────┬─────────┬────────┬─────────┬────────┐
│ Col A  │  Col B  │ Col C  │  Col D  │  ...   │
│ Cat.1  │ Eventi1 │ Cat.2  │ Eventi2 │  ...   │
└────────┴─────────┴────────┴─────────┴────────┘
```

### Le 7 Categorie di Rischio

| # | Categoria | Codice Sistema | N° Eventi | Colonna Work |
|---|-----------|----------------|-----------|--------------|
| 1 | Frodi interne | Internal_Fraud_Frodi_interne | 19 | B |
| 2 | Frodi esterne | External_fraud_Frodi_esterne | 17 | D |
| 3 | Rapporti dipendenti | Employment_practices_Dipendenti | 21 | F |
| 4 | Clienti e prodotti | Clients_product_Clienti | 43 | H |
| 5 | Danni materiali | Damage_Danni | 11 | J |
| 6 | Interruzioni sistema | Business_disruption | 20 | L |
| 7 | Esecuzione processi | Execution_delivery_Problemi | 59 | N+P |

**TOTALE:** 190 eventi mappati

### Formula VLOOKUP Originale
```excel
=IFERROR(VLOOKUP(F5,$F$1001:$G$1200,2,0),"")
```

**Decodifica:**
- `F5`: Cella con codice evento selezionato
- `$F$1001:$G$1200`: Range tabella lookup (200 righe)
- `2`: Ritorna seconda colonna (descrizione)
- `0`: Match esatto richiesto
- `IFERROR(...,"")`: Se non trova, mostra vuoto

---

## 🚀 API REST Disponibili

### Server 1: FastAPI (excel_system_final.py)

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
    "Internal_Fraud_Frodi_interne",
    "External_fraud_Frodi_esterne",
    "Employment_practices_Dipendenti",
    "Clients_product_Clienti",
    "Damage_Danni",
    "Business_disruption",
    "Execution_delivery_Problemi_di_produzione_o_consegna"
  ],
  "total": 7
}
```

##### 2. GET /events/{category}
**Descrizione:** Restituisce eventi filtrati per categoria

**Parametri:**
- `category` (path): Nome categoria

**Response:**
```json
{
  "category": "Internal_Fraud_Frodi_interne",
  "events": [
    "601 - Furto di denaro, cassa o altro",
    "602 - Furto di beni/merce di proprietà della banca",
    // ... altri 17 eventi
  ],
  "total": 19
}
```

##### 3. GET /description/{event_code}
**Descrizione:** Restituisce descrizione evento (VLOOKUP)

**Parametri:**
- `event_code` (path): Codice evento completo

**Response:**
```json
{
  "event_code": "601 - Furto di denaro, cassa o altro",
  "description": "Sottrazione illecita di denaro contante o altri valori dalla cassa aziendale"
}
```

### Server 2: Python Puro (excel_server_simple.py)

**Vantaggi:**
- ✅ Nessuna dipendenza esterna
- ✅ Usa solo librerie standard Python
- ✅ Compatibile con qualsiasi Python 3.x

**Stesso API del server FastAPI ma implementato con:**
```python
from http.server import HTTPServer, BaseHTTPRequestHandler
```

---

## 🔄 Il Flusso Dati Completo

### 1. Estrazione dall'Excel
```
extract_excel_complete.py
    ↓
Legge: Operational Risk Mapping Globale - Copia.xlsx
    ↓
Estrae: 
  - Formule dalle celle
  - Tabelle lookup (righe 1001+)
  - Mappature dal foglio "work"
    ↓
Genera:
  - excel_data_complete.json
  - excel_lookups_complete.json
```

### 2. Implementazione Backend
```
excel_system_final.py / excel_server_simple.py
    ↓
Carica: JSON files
    ↓
Espone: REST API
    ↓
Implementa:
  - Filtering per categoria
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
  1. Dropdown categorie
  2. Dropdown eventi (filtrato)
  3. Descrizione automatica
    ↓
Replica: Comportamento Excel
```

---

## 📋 Mapping Completo Categorie → Eventi

### Internal_Fraud_Frodi_interne (19 eventi)
```
601 - Furto di denaro, cassa o altro
602 - Furto di beni/merce
603 - Distruzione fraudolenta
604 - Falsificazione documentazione
605 - Frode informatica
606 - Furto info sensibili
607 - Movimentazione non autorizzata
608 - Insider trading
609 - Errata marcatura posizioni
610 - Frode creditizia interna
611 - Appropriazione indebita
612 - Mazzette/tangenti
613 - Utilizzo insider information
614 - Valutazione deliberata errata
615 - Violazione normativa concorrenza
616 - Utilizzo beni aziendali
617 - Danno deliberato sistemi
618 - Mancata applicazione controlli
619 - Altri eventi frode interna
```

### External_fraud_Frodi_esterne (17 eventi)
```
701 - Furto o rapina
702 - Falsificazione
703 - Assegni scoperti
704 - Frode informatica
705 - Phishing
706 - Attacco fisico infrastrutture
707 - Attacco sistemi informativi
708 - Frode creditizia esterna
709 - Frode carte pagamento
710 - Riciclaggio
711 - Furto/manomissione ATM
712 - Frode addebito diretto
713 - Identity theft
714 - Hackeraggio conti
715 - Spoofing/Pharming
716 - Furto info riservate
717 - Altri eventi frode esterna
```

[... e così via per le altre 5 categorie ...]

---

## 🛠️ Installazione e Avvio

### Opzione 1: Server con FastAPI (Consigliato)
```bash
# Installa dipendenze
pip install fastapi uvicorn

# Avvia server
python excel_system_final.py

# Server attivo su http://localhost:8000
```

### Opzione 2: Server Python Puro (Zero dipendenze)
```bash
# Nessuna installazione richiesta!

# Avvia server
python excel_server_simple.py

# Server attivo su http://localhost:8000
```

### Test Frontend
1. Avvia uno dei server sopra
2. Apri `test_finale.html` nel browser
3. Il sistema funziona esattamente come l'Excel!

---

## 🧪 Testing e Verifica

### Test API con cURL
```bash
# 1. Lista categorie
curl http://localhost:8000/categories

# 2. Eventi per categoria
curl http://localhost:8000/events/Internal_Fraud_Frodi_interne

# 3. Descrizione evento
curl "http://localhost:8000/description/601%20-%20Furto%20di%20denaro%2C%20cassa%20o%20altro"
```

### Test con JavaScript
```javascript
// Test completo del flusso
async function testFlow() {
  // 1. Carica categorie
  const cats = await fetch('http://localhost:8000/categories');
  const categories = await cats.json();
  console.log('Categorie:', categories.total);
  
  // 2. Prendi eventi prima categoria
  const evts = await fetch(`http://localhost:8000/events/${categories.categories[0]}`);
  const events = await evts.json();
  console.log('Eventi:', events.total);
  
  // 3. Prendi descrizione primo evento
  const desc = await fetch(`http://localhost:8000/description/${encodeURIComponent(events.events[0])}`);
  const description = await desc.json();
  console.log('Descrizione:', description.description);
}
```

---

## 🔍 Dettagli Implementazione

### Struttura Dati Interna
```python
CATEGORIA_EVENTI_MAP = {
    "Internal_Fraud_Frodi_interne": [
        # Lista di 19 eventi
    ],
    "External_fraud_Frodi_esterne": [
        # Lista di 17 eventi
    ],
    # ... altre 5 categorie
}

EVENT_DESCRIPTIONS = {
    "601 - Furto di denaro, cassa o altro": "Descrizione completa...",
    "602 - Furto di beni/merce": "Descrizione completa...",
    # ... tutti i 190 eventi
}
```

### Perché Due Server?

| Aspetto | excel_system_final.py | excel_server_simple.py |
|---------|------------------------|-------------------------|
| **Dipendenze** | FastAPI, uvicorn | ZERO |
| **Performance** | Alta (async) | Media |
| **Features** | Complete | Essenziali |
| **Documentazione** | Auto (Swagger) | Manuale |
| **Produzione** | ✅ Consigliato | ⚠️ Solo test |

---

## 📝 Note per l'Integrazione Frontend

### Best Practices
1. **Cache delle categorie**: Caricale una volta all'avvio
2. **Debouncing**: Non chiamare API ad ogni keystroke
3. **Error handling**: Gestisci errori network
4. **Loading states**: Mostra spinner durante caricamento
5. **Validazione**: Verifica selezioni prima di chiamare API

### Esempio Integrazione React
```jsx
const [categories, setCategories] = useState([]);
const [events, setEvents] = useState([]);
const [description, setDescription] = useState('');

useEffect(() => {
  // Carica categorie all'avvio
  fetch('http://localhost:8000/categories')
    .then(res => res.json())
    .then(data => setCategories(data.categories));
}, []);

const handleCategoryChange = async (category) => {
  const res = await fetch(`http://localhost:8000/events/${category}`);
  const data = await res.json();
  setEvents(data.events);
};

const handleEventChange = async (event) => {
  const res = await fetch(`http://localhost:8000/description/${encodeURIComponent(event)}`);
  const data = await res.json();
  setDescription(data.description);
};
```

---

## 🆘 Troubleshooting

### Problema: "File excel_data_complete.json not found"
**Soluzione:** Esegui prima `python extract_excel_complete.py`

### Problema: "CORS blocked"
**Soluzione:** Verifica che il server abbia CORS abilitato per il tuo dominio

### Problema: "Eventi non filtrati correttamente"
**Soluzione:** Verifica che la categoria sia esattamente come nel mapping (case sensitive)

### Problema: "Descrizione non trovata"
**Soluzione:** L'evento deve essere passato COMPLETO con codice e testo

---

## ✅ Checklist Verifica Sistema

- [ ] File Excel originale presente (165KB)
- [ ] Server avviato su porta 8000
- [ ] Endpoint `/categories` ritorna 7 categorie
- [ ] Endpoint `/events/Internal_Fraud_Frodi_interne` ritorna 19 eventi
- [ ] VLOOKUP funziona per tutti i 190 eventi
- [ ] test_finale.html mostra flusso corretto
- [ ] Dropdown eventi si aggiorna con categoria
- [ ] Descrizione appare automaticamente
- [ ] CORS funziona per il frontend
- [ ] Sistema replica esattamente l'Excel

---

## 📋 Differenze tra i File di Estrazione

| Script | Scopo | Output |
|--------|-------|--------|
| `extract_excel_complete.py` | Estrazione COMPLETA tutti i dati | JSON completi |
| `analyze_work_sheet.py` | Solo analisi foglio "work" | Report mappature |
| Altri script di test | Varie prove ed esperimenti | Temporanei |

**NOTA:** Solo `extract_excel_complete.py` è necessario per generare i dati per il sistema finale.

---

Il sistema è una **replica fedele al 100%** del comportamento Excel originale, mantenendo la stessa logica di business e le stesse relazioni tra i dati.