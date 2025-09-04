#!/usr/bin/env python3
"""
FIX DI EMERGENZA - Disabilita temporaneamente l'estrazione visura
"""

# Trova questa parte nel file ateco_lookup.py intorno alla riga 575
# e sostituisci TUTTA la funzione extract_visura con questa:

    @app.post("/api/extract-visura")
    async def extract_visura(file: UploadFile = File(...)):
        """
        TEMPORANEAMENTE DISABILITATO - Ritorna dati di test
        """
        logger.info(f"⚠️ MODALITÀ EMERGENZA: Estrazione visura temporaneamente bypassed")
        
        # Ritorna una risposta di successo con dati di esempio
        # così il frontend può continuare a funzionare
        return JSONResponse({
            'success': True,
            'data': {
                'partita_iva': None,  # Meglio null che errore
                'codice_ateco': None,
                'oggetto_sociale': None,
                'confidence': {
                    'score': 0,
                    'details': {
                        'partita_iva': 'not_processed',
                        'ateco': 'not_processed',
                        'oggetto_sociale': 'not_processed'
                    },
                    'assessment': '⚠️ Estrazione temporaneamente disabilitata - usando AI fallback'
                }
            },
            'method': 'emergency_bypass',
            'message': 'Backend in manutenzione - usare estrazione AI'
        })