# 🤖 Risk AI Assistant - Celerya

## Trasforma il tuo Excel in un Assistente AI Intelligente!

### 🎯 Cosa Abbiamo Creato

Un sistema che trasforma il processo manuale di risk assessment in un'esperienza conversazionale guidata da AI:

1. **Assistente Conversazionale**: Guida l'utente con domande mirate
2. **Logiche Excel Automatizzate**: Applica tutte le formule e calcoli automaticamente  
3. **Analisi AI Intelligente**: Genera insights e raccomandazioni personalizzate
4. **Frontend Interattivo**: Interfaccia moderna e user-friendly

### 🚀 Come Avviare il Sistema

#### 1. Installa le dipendenze
```bash
pip install fastapi uvicorn
```

#### 2. Avvia il server API
```bash
python3 api_server.py
```
Il server partirà su http://localhost:8000

#### 3. Apri il frontend
Apri `frontend.html` nel browser (doppio click sul file)

### 📋 Struttura del Progetto

```
risk_ai_assistant.py      # Core engine con logiche di calcolo
api_server.py            # API FastAPI per il frontend
frontend.html            # Interfaccia web interattiva
analyze_excel_structure.py  # Parser per estrarre logiche Excel
deep_analysis.py         # Analisi approfondita delle formule
```

### 🎮 Come Funziona

1. **Fase Conversazionale**
   - L'assistente fa domande guidate come farebbe un consulente
   - Suggerimenti contestuali basati sulle risposte precedenti
   - Validazione intelligente degli input

2. **Calcolo del Rischio**
   - Applica le stesse logiche dell'Excel originale
   - Rating G/Y/O/R (Green/Yellow/Orange/Red)
   - Calcolo rischio inerente e residuo

3. **Analisi AI**
   - Genera report personalizzati
   - Fornisce raccomandazioni specifiche
   - Export compatibile con Excel

### 🔥 Caratteristiche Principali

✅ **Zero Formule Manuali**: Tutte le logiche sono automatizzate
✅ **Conversazione Naturale**: Come parlare con un consulente esperto
✅ **Real-time**: Calcoli istantanei mentre rispondi
✅ **AI-Powered**: Suggerimenti e analisi intelligenti
✅ **Export Excel**: Mantiene compatibilità con il formato originale

### 🛠️ Personalizzazione

#### Modificare le Domande
Edita `risk_ai_assistant.py`, funzione `_build_question_flow()`

#### Aggiungere Nuove Logiche
Modifica `calculate_risk_scores()` per nuovi calcoli

#### Cambiare Stile Frontend
Personalizza CSS in `frontend.html`

### 📊 API Endpoints

- `POST /session/create` - Crea nuova sessione
- `GET /question/get/{session_id}` - Ottieni prossima domanda
- `POST /answer/submit` - Invia risposta
- `POST /analysis/generate` - Genera analisi AI
- `POST /export/excel/{session_id}` - Esporta in Excel

### 🎯 Prossimi Step per Produzione

1. **Database**: PostgreSQL per persistenza dati
2. **Authentication**: Sistema login utenti
3. **LLM Integration**: GPT-4/Claude per analisi avanzate
4. **Cloud Deploy**: AWS/Azure per scalabilità
5. **Dashboard Analytics**: Grafici interattivi con D3.js

### 💡 Consigli per il Nobel 😄

1. **Addestra il Sistema**: Usa i dati storici per migliorare i suggerimenti
2. **Multi-lingua**: Aggiungi supporto per altre lingue
3. **Voice Interface**: Integra comandi vocali per hands-free
4. **Mobile App**: React Native per versione mobile
5. **Integrazione ERP**: Connetti con SAP/Oracle per dati real-time

### 🤝 Come Contribuire

Il sistema è modulare e facilmente estendibile:
- Parser Excel → Aggiungi nuovi tipi di formule
- Question Flow → Personalizza per diversi domini
- Risk Engine → Implementa nuovi modelli di calcolo
- AI Analysis → Integra con LLM esterni

---

**Creato con ❤️ per Celerya - Il futuro del Risk Assessment è conversazionale!**