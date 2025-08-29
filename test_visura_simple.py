#!/usr/bin/env python3
"""
Test semplice per verificare che l'estrazione visure funzioni
Può essere usato anche senza un PDF reale
"""

def test_extraction():
    print("🔍 Test estrazione visura camerale\n")
    
    # Test 1: Verifica import
    try:
        from visura_extractor import VisuraExtractor
        print("✅ Import VisuraExtractor OK")
    except ImportError as e:
        print(f"❌ Errore import: {e}")
        print("   Installa: pip install pdfplumber")
        return False
    
    # Test 2: Crea istanza
    try:
        extractor = VisuraExtractor()
        print("✅ Creazione VisuraExtractor OK")
    except Exception as e:
        print(f"❌ Errore creazione: {e}")
        return False
    
    # Test 3: Test regex patterns
    test_text = """
    DATI ANAGRAFICI
    Codice fiscale e numero d'iscrizione: 12345678901
    Partita IVA: 12345678901
    
    ATTIVITÀ, ALBI RUOLI E LICENZE
    ATTIVITÀ
    Codice: 62.01.00 - Produzione di software
    Descrizione: PRODUZIONE DI SOFTWARE NON CONNESSO ALL'EDIZIONE
    Codice: 62.02.00 - Consulenza nel settore delle tecnologie
    
    OGGETTO SOCIALE
    La società ha per oggetto lo sviluppo, la produzione e la commercializzazione
    di prodotti software, la consulenza informatica e servizi connessi alle
    tecnologie dell'informazione per terzi. La società potrà inoltre svolgere
    attività di formazione professionale nel settore informatico.
    
    SEDE LEGALE
    Via Giuseppe Garibaldi n. 42
    20121 Milano (MI)
    
    UNITÀ LOCALI
    N. 1 - Via Roma 10, 00100 Roma (RM)
    """
    
    # Test estrazione ATECO
    codici = extractor.extract_ateco(test_text)
    if codici:
        print(f"✅ Estrazione ATECO OK: {codici}")
    else:
        print("⚠️  Nessun codice ATECO trovato")
    
    # Test estrazione oggetto sociale
    oggetto = extractor.extract_oggetto_sociale(test_text)
    if oggetto:
        print(f"✅ Estrazione oggetto sociale OK: {oggetto[:50]}...")
    else:
        print("⚠️  Oggetto sociale non trovato")
    
    # Test estrazione sedi
    sedi = extractor.extract_sedi(test_text)
    if sedi.get('sede_legale'):
        print(f"✅ Estrazione sede legale OK: {sedi['sede_legale']}")
    else:
        print("⚠️  Sede legale non trovata")
    
    # Test inferenza business type
    tipo = extractor.infer_business_type(test_text, oggetto)
    print(f"✅ Tipo business inferito: {tipo}")
    
    print("\n✨ Test completato con successo!")
    return True

if __name__ == "__main__":
    import sys
    success = test_extraction()
    sys.exit(0 if success else 1)