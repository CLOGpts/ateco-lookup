# Endpoint Zone Sismiche - Documentazione

## ENDPOINT: `/seismic-zone/{comune}`

### Descrizione
Restituisce la zona sismica di un comune italiano secondo la classificazione OPCM 3519/2006.

### URL
```
GET /seismic-zone/{comune}?provincia={sigla_provincia}
```

### Parametri

| Parametro | Tipo | Obbligatorio | Descrizione |
|-----------|------|--------------|-------------|
| `comune` | string (path) | Sì | Nome del comune (case-insensitive) |
| `provincia` | string (query) | No | Sigla provincia (es: TO, MI, RM) per disambiguare comuni omonimi |

### Database
- **Fonte**: OPCM 3519/2006 - Protezione Civile + INGV
- **Comuni mappati**: 419 comuni principali (5.2% dei comuni italiani)
- **Copertura**: Tutti i capoluoghi e principali comuni per regione
- **Fuzzy matching**: Sistema intelligente per comuni simili
- **Estimation**: Stima basata su provincia per comuni non mappati

### Zone Sismiche

| Zona | Accelerazione ag | Descrizione | Risk Level |
|------|------------------|-------------|------------|
| 1 | 0.35g | Sismicità alta - zona più pericolosa | Molto Alta |
| 2 | 0.25g | Sismicità media - possibili forti terremoti | Alta |
| 3 | 0.15g | Sismicità bassa - scuotimenti modesti | Media |
| 4 | 0.05g | Sismicità molto bassa - zona meno pericolosa | Bassa |

### Risposte

#### Success (200) - Match esatto
```json
{
  "comune": "TORINO",
  "provincia": "TO",
  "regione": "PIEMONTE",
  "zona_sismica": 3,
  "accelerazione_ag": 0.15,
  "risk_level": "Media",
  "description": "Zona 3 - Sismicità bassa: Zona che può essere soggetta a scuotimenti modesti",
  "normativa": "OPCM 3519/2006",
  "source": "database_match",
  "confidence": 1.0
}
```

#### Success (200) - Fuzzy match
```json
{
  "comune": "TORINO",
  "input_comune": "TORIN",
  "provincia": "TO",
  "regione": "PIEMONTE",
  "zona_sismica": 3,
  "accelerazione_ag": 0.15,
  "risk_level": "Media",
  "description": "Zona 3 - Sismicità bassa: Zona che può essere soggetta a scuotimenti modesti",
  "normativa": "OPCM 3519/2006",
  "source": "fuzzy_match",
  "confidence": 0.92,
  "note": "Match approssimato: 'TORIN' -> 'TORINO'"
}
```

#### Success (200) - Provincia estimation
```json
{
  "comune": "COMUNE_NON_MAPPATO",
  "provincia": "TO",
  "zona_sismica": 3,
  "accelerazione_ag": 0.15,
  "risk_level": "Media",
  "description": "Zona 3 - Sismicità bassa: Zona che può essere soggetta a scuotimenti modesti",
  "normativa": "OPCM 3519/2006",
  "source": "provincia_estimation",
  "confidence": 0.5,
  "note": "Stima basata sulla zona prevalente della provincia TO"
}
```

#### Error (404) - Comune non trovato
```json
{
  "error": "comune_not_found",
  "message": "Comune 'PIPPO' non trovato nel database",
  "suggestions": [
    {
      "comune": "PISA",
      "provincia": "PI",
      "zona_sismica": 3
    }
  ],
  "suggestion_text": "Verifica il nome del comune o fornisci la sigla provincia"
}
```

#### Error (404) - Provincia mismatch
```json
{
  "error": "comune_provincia_mismatch",
  "message": "Comune TORINO non trovato in provincia MI",
  "suggestion": "TORINO trovato in provincia TO"
}
```

#### Error (500) - Internal error
```json
{
  "error": "internal_error",
  "message": "Errore interno del server",
  "details": "..."
}
```

### Esempi CURL

#### Test 1: Comune esatto
```bash
curl http://localhost:8000/seismic-zone/TORINO
```

**Output atteso**:
```json
{
  "comune": "TORINO",
  "provincia": "TO",
  "zona_sismica": 3,
  "accelerazione_ag": 0.15,
  "risk_level": "Media",
  "source": "database_match",
  "confidence": 1.0
}
```

#### Test 2: Milano (case-insensitive)
```bash
curl http://localhost:8000/seismic-zone/milano
```

**Output atteso**:
```json
{
  "comune": "MILANO",
  "provincia": "MI",
  "zona_sismica": 4,
  "accelerazione_ag": 0.05,
  "risk_level": "Bassa",
  "source": "database_match",
  "confidence": 1.0
}
```

#### Test 3: L'Aquila (con apostrofo)
```bash
curl "http://localhost:8000/seismic-zone/L'AQUILA"
```

**Output atteso**:
```json
{
  "comune": "L'AQUILA",
  "provincia": "AQ",
  "zona_sismica": 1,
  "accelerazione_ag": 0.35,
  "risk_level": "Molto Alta",
  "source": "database_match",
  "confidence": 1.0
}
```

#### Test 4: Con parametro provincia
```bash
curl "http://localhost:8000/seismic-zone/ROMA?provincia=RM"
```

#### Test 5: Fuzzy matching
```bash
curl http://localhost:8000/seismic-zone/TORIN
```

**Output atteso**: Trova "TORINO" con confidence < 1.0

### Source Types

| Source | Confidence | Descrizione |
|--------|-----------|-------------|
| `database_match` | 1.0 | Match esatto nel database |
| `fuzzy_match` | 0.6-0.99 | Match approssimato con algoritmo similarità |
| `provincia_estimation` | 0.5 | Stima basata su zona prevalente della provincia |

### Features Avanzate

1. **Case-insensitive**: `torino`, `TORINO`, `Torino` → tutti accettati
2. **Fuzzy matching**: Corregge typo minori (TORIN → TORINO)
3. **Normalizzazione accenti**: À → A, È → E, ecc.
4. **Provincia disambiguation**: Gestisce comuni omonimi
5. **Graceful degradation**: Stima per comuni non mappati
6. **Suggestions**: Fornisce alternative se non trova match

### Statiche Database (419 comuni)

- Zona 1 (Molto Alta): 55 comuni
- Zona 2 (Alta): 129 comuni
- Zona 3 (Media): 134 comuni
- Zona 4 (Bassa): 101 comuni

### Performance

- Latency attesa: < 50ms
- Caricamento database: lazy load (solo al primo utilizzo)
- Cache: No (file JSON piccolo, 200KB)

### Error Handling

Tutti gli errori sono gestiti con:
- Status code appropriato (404, 500)
- Messaggio user-friendly
- Suggerimenti quando possibile
- Logging server-side completo

### Deploy

Backend già deployed su Railway:
- Endpoint pronto all'uso
- Database JSON incluso nel deployment
- Nessuna dipendenza esterna (database locale)

### Integrazione Frontend

```javascript
// Esempio chiamata da frontend
const getSeismicZone = async (comune, provincia = null) => {
  const url = provincia 
    ? `/seismic-zone/${comune}?provincia=${provincia}`
    : `/seismic-zone/${comune}`;
  
  const response = await fetch(url);
  const data = await response.json();
  
  if (response.ok) {
    return {
      success: true,
      zona: data.zona_sismica,
      risk: data.risk_level,
      description: data.description,
      confidence: data.confidence
    };
  } else {
    return {
      success: false,
      error: data.message,
      suggestions: data.suggestions || []
    };
  }
};
```

### Normativa di Riferimento

**OPCM 3519/2006** - Criteri generali per l'individuazione delle zone sismiche e per la formazione e l'aggiornamento degli elenchi delle medesime zone.

### Manutenzione Database

Per aggiornare il database:
1. Modifica `zone_sismiche_comuni.json`
2. Aggiungi comuni in formato:
```json
{
  "NOME_COMUNE": {
    "provincia": "XX",
    "regione": "REGIONE",
    "zona_sismica": 1-4,
    "accelerazione_ag": 0.05-0.35,
    "risk_level": "Bassa|Media|Alta|Molto Alta"
  }
}
```
3. Redeploy su Railway

### Contatti

Backend gestito da: L'ARCHITETTO
Database source: INGV + Protezione Civile
Last update: 2025-10-02
