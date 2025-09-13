# ISTRUZIONI BACKEND - ESTRAZIONE VISURA CAMERALE
## ⚠️ REGOLE FERREE - NON DEVIARE MAI

### 🎯 SOLO 3 CAMPI DA ESTRARRE:
1. **PARTITA IVA**
2. **CODICE ATECO** 
3. **OGGETTO SOCIALE**

---

## 1️⃣ PARTITA IVA
### DOVE CERCARE:
```
- Dopo "Partita IVA:" o "P.IVA:" o "P. IVA:"
- Dopo "VAT:" o "VAT Number:"
- Nel campo "Codice Fiscale:" (spesso coincidono)
```

### VALIDAZIONE OBBLIGATORIA:
```python
def validate_partita_iva(piva):
    # DEVE essere ESATTAMENTE 11 cifre numeriche
    cleaned = re.sub(r'\D', '', str(piva))
    if len(cleaned) == 11 and cleaned.isdigit():
        return cleaned
    return None  # SE NON VALIDA, RITORNA NULL
```

### ❌ SE NON TROVI O NON È VALIDA → `null`

---

## 2️⃣ CODICE ATECO
### DOVE CERCARE:
```
- Dopo "Codice ATECO:" o "ATECO:" 
- Dopo "Attività prevalente:" o "Codice attività:"
- Dopo "Importanza: P -" o "I - primaria"
- Pattern: numeri formato XX.XX o XX.XX.XX
```

### VALIDAZIONE OBBLIGATORIA:
```python
def validate_ateco(ateco):
    # Pulisci e normalizza
    normalized = str(ateco).replace(' ', '.').strip()
    # DEVE matchare XX.XX o XX.XX.XX
    if re.match(r'^\d{2}\.\d{2}(?:\.\d{1,2})?$', normalized):
        return normalized
    return None  # SE NON VALIDO, RITORNA NULL
```

### ❌ SE NON TROVI O FORMATO ERRATO → `null`

---

## 3️⃣ OGGETTO SOCIALE
### DOVE CERCARE:
```
- Dopo "OGGETTO SOCIALE:" o "Oggetto sociale:"
- Dopo "Oggetto:" o "OGGETTO:"
- Dopo "Attività:" o "Descrizione attività:"
- Dopo il codice ATECO, spesso c'è la descrizione
```

### VALIDAZIONE OBBLIGATORIA:
```python
def validate_oggetto_sociale(oggetto):
    if not oggetto:
        return None
    
    # Pulisci
    cleaned = ' '.join(str(oggetto).split())
    
    # DEVE avere ALMENO 30 caratteri
    if len(cleaned) < 30:
        return None
        
    # DEVE contenere parole italiane comuni
    business_words = ['produzione', 'commercio', 'servizi', 'consulenza', 
                      'vendita', 'attività', 'gestione', 'intermediazione']
    
    has_business_word = any(word in cleaned.lower() for word in business_words)
    
    if not has_business_word:
        return None  # Probabilmente non è l'oggetto sociale
    
    # Tronca se troppo lungo
    if len(cleaned) > 500:
        return cleaned[:500] + '...'
    
    return cleaned
```

### ❌ SE NON TROVI O < 30 CARATTERI → `null`

---

## 📊 CALCOLO CONFIDENCE ONESTO

```python
def calculate_real_confidence(partita_iva, ateco, oggetto_sociale):
    """
    CONFIDENCE REALE basata su validazioni
    """
    score = 0
    details = {}
    
    # Check Partita IVA
    if partita_iva and validate_partita_iva(partita_iva):
        score += 33
        details['partita_iva'] = 'valid'
    else:
        details['partita_iva'] = 'invalid_or_missing'
    
    # Check ATECO
    if ateco and validate_ateco(ateco):
        score += 33
        details['ateco'] = 'valid'
    else:
        details['ateco'] = 'invalid_or_missing'
    
    # Check Oggetto Sociale
    if oggetto_sociale and validate_oggetto_sociale(oggetto_sociale):
        score += 34
        details['oggetto_sociale'] = 'valid'
    else:
        details['oggetto_sociale'] = 'invalid_or_missing'
    
    return {
        'score': score,  # 0, 33, 66, o 100
        'details': details
    }
```

---

## 🚫 COSA NON FARE MAI:

### ❌ NON ESTRARRE:
- "HA DEPOSITATO..." → NON è una denominazione!
- "VISURA ORDINARIA" → NON è un nome azienda!
- "CAMERA DI COMMERCIO" → NON è un dato!
- Testo generico che non è un campo specifico

### ❌ NON INVENTARE:
- Se non trovi → `null` (non inventare)
- Se non sei sicuro → `null` (meglio vuoto che sbagliato)
- Confidence inventate → USA IL CALCOLO REALE

---

## 📤 OUTPUT RICHIESTO:

```json
{
  "success": true,
  "data": {
    "partita_iva": "04837181009",    // o null
    "codice_ateco": "68.31",         // o null  
    "oggetto_sociale": "INTERMEDIAZIONE, SERVIZI E CONSULENZE...",  // o null
    "confidence": {
      "score": 100,  // 0, 33, 66, o 100 - MAI numeri inventati!
      "details": {
        "partita_iva": "valid",
        "ateco": "valid",
        "oggetto_sociale": "valid"
      }
    }
  },
  "method": "backend"  // o "ai_assisted" se usi Gemini
}
```

---

## ⚡ ESEMPI PRATICI:

### ✅ BUONO:
```json
{
  "partita_iva": "04837181009",
  "codice_ateco": "68.31",
  "oggetto_sociale": "INTERMEDIAZIONE, SERVIZI E CONSULENZE IN MATERIA DI COMPRAVENDITA...",
  "confidence": {
    "score": 100,
    "details": {
      "partita_iva": "valid",
      "ateco": "valid", 
      "oggetto_sociale": "valid"
    }
  }
}
```

### ❌ CATTIVO:
```json
{
  "denominazione": "HA DEPOSITATO, INSIEME AL BILANCIO...",  // NO! Non è il nome!
  "confidence": {
    "score": 60  // NO! Numero inventato!
  }
}
```

---

## 🔴 REGOLA D'ORO:
**MEGLIO NULL CHE DATI SBAGLIATI!**

Se hai dubbi → `null`
Se non è chiaro → `null`
Se sembra strano → `null`

**I CLIENTI PREFERISCONO CAMPI VUOTI CHE DATI INVENTATI!**