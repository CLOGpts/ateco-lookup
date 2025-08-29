#!/usr/bin/env python3
"""
Script di test per l'estrazione dati da visure camerali
Testa sia l'estrattore standalone che l'endpoint API
"""
import os
import sys
import json
import requests
import time
from pathlib import Path

# Configurazione
API_BASE_URL = "http://localhost:8000"
TEST_PDF_PATH = "test_visura.pdf"  # Sostituisci con il path della tua visura di test

def test_standalone_extractor():
    """Test dell'estrattore standalone"""
    print("\n" + "="*60)
    print("TEST 1: Estrattore Standalone")
    print("="*60)
    
    # Verifica che visura_extractor.py esista
    if not Path("visura_extractor.py").exists():
        print("❌ File visura_extractor.py non trovato!")
        return False
    
    # Import del modulo
    try:
        from visura_extractor import VisuraExtractor
        print("✅ Import VisuraExtractor riuscito")
    except ImportError as e:
        print(f"❌ Errore import: {e}")
        print("   Installa: pip install pdfplumber")
        return False
    
    # Test con file di esempio (se esiste)
    if Path(TEST_PDF_PATH).exists():
        print(f"\n📄 Test con file: {TEST_PDF_PATH}")
        extractor = VisuraExtractor()
        result = extractor.extract_from_pdf(TEST_PDF_PATH)
        
        print("\n📊 Risultato estrazione:")
        print(json.dumps(result, indent=2, ensure_ascii=False))
        
        if result.get('success'):
            data = result.get('data', {})
            print(f"\n✅ Estrazione completata con successo!")
            print(f"   - Codici ATECO trovati: {len(data.get('codici_ateco', []))}")
            print(f"   - Confidence: {data.get('confidence', 0):.0%}")
            print(f"   - Tipo business: {data.get('tipo_business', 'N/D')}")
            return True
        else:
            print(f"❌ Estrazione fallita: {result.get('error', {}).get('message')}")
            return False
    else:
        print(f"⚠️  File di test '{TEST_PDF_PATH}' non trovato")
        print("   Crea un file visura di test per testare l'estrazione")
        
        # Test con testo di esempio
        print("\n📝 Test con testo di esempio...")
        extractor = VisuraExtractor()
        
        # Simula estrazione da testo
        test_text = """
        CODICE ATECO: 62.01.00
        OGGETTO SOCIALE: Sviluppo di software e consulenza informatica
        SEDE LEGALE: Via Roma 123, 00100 Roma (RM)
        """
        
        # Test regex patterns
        codici = extractor.patterns['ateco'].findall(test_text)
        print(f"   Codici ATECO estratti: {codici}")
        
        if codici:
            print("✅ Regex ATECO funzionante")
            return True
        else:
            print("❌ Regex ATECO non funzionante")
            return False

def test_api_endpoint():
    """Test dell'endpoint API"""
    print("\n" + "="*60)
    print("TEST 2: Endpoint API /api/extract-visura")
    print("="*60)
    
    # Verifica che il server sia attivo
    try:
        response = requests.get(f"{API_BASE_URL}/health")
        if response.status_code == 200:
            print("✅ Server API attivo")
        else:
            print("❌ Server API non risponde correttamente")
            return False
    except requests.exceptions.ConnectionError:
        print("❌ Server API non raggiungibile")
        print("   Avvia il server con: python ateco_lookup.py --file tabella_ATECO.xlsx --serve")
        return False
    
    # Test upload file
    if Path(TEST_PDF_PATH).exists():
        print(f"\n📤 Upload file: {TEST_PDF_PATH}")
        
        with open(TEST_PDF_PATH, 'rb') as f:
            files = {'file': (TEST_PDF_PATH, f, 'application/pdf')}
            
            try:
                response = requests.post(
                    f"{API_BASE_URL}/api/extract-visura",
                    files=files
                )
                
                if response.status_code == 200:
                    result = response.json()
                    print("\n📊 Risposta API:")
                    print(json.dumps(result, indent=2, ensure_ascii=False))
                    
                    if result.get('success'):
                        data = result.get('data', {})
                        print(f"\n✅ Estrazione via API completata!")
                        print(f"   - Processing time: {result.get('processing_time_ms', 0)}ms")
                        
                        # Verifica arricchimento ATECO
                        if 'ateco_details' in data:
                            print(f"   - Codici ATECO arricchiti: {len(data['ateco_details'])}")
                            for detail in data['ateco_details'][:2]:
                                print(f"     • {detail['code']}: {detail['description'][:50]}...")
                        
                        return True
                    else:
                        print(f"❌ Estrazione fallita: {result.get('error', {}).get('message')}")
                        return False
                else:
                    print(f"❌ Errore HTTP {response.status_code}: {response.text}")
                    return False
                    
            except Exception as e:
                print(f"❌ Errore durante chiamata API: {e}")
                return False
    else:
        print(f"⚠️  File di test '{TEST_PDF_PATH}' non trovato")
        
        # Test con file non valido
        print("\n📝 Test validazione file...")
        
        # Test file non PDF
        files = {'file': ('test.txt', b'test content', 'text/plain')}
        response = requests.post(f"{API_BASE_URL}/api/extract-visura", files=files)
        
        if response.status_code == 400:
            error = response.json()
            if 'PDF' in error.get('detail', {}).get('message', ''):
                print("✅ Validazione tipo file funzionante")
                return True
        
        print("❌ Validazione non funzionante correttamente")
        return False

def test_integration():
    """Test integrazione completa"""
    print("\n" + "="*60)
    print("TEST 3: Integrazione con lookup ATECO")
    print("="*60)
    
    # Simula estrazione e poi lookup
    test_codes = ["62.01.00", "47.91.10"]
    
    print(f"\n🔍 Test lookup per codici: {test_codes}")
    
    for code in test_codes:
        try:
            response = requests.get(
                f"{API_BASE_URL}/lookup",
                params={"code": code}
            )
            
            if response.status_code == 200:
                data = response.json()
                print(f"\n✅ Codice {code}:")
                print(f"   - Descrizione: {data.get('TITOLO_ATECO_2022', 'N/D')[:50]}...")
                
                if 'normative' in data:
                    print(f"   - Normative: {len(data['normative'])}")
                if 'certificazioni' in data:
                    print(f"   - Certificazioni: {len(data['certificazioni'])}")
            else:
                print(f"❌ Errore lookup per {code}")
                
        except Exception as e:
            print(f"❌ Errore: {e}")
            return False
    
    return True

def main():
    """Esegue tutti i test"""
    print("\n🚀 AVVIO TEST ESTRAZIONE VISURE CAMERALI")
    print("="*60)
    
    # Verifica dipendenze
    print("\n📦 Verifica dipendenze...")
    try:
        import pdfplumber
        print("✅ pdfplumber installato")
    except ImportError:
        print("❌ pdfplumber non installato")
        print("   Installa con: pip install pdfplumber")
        sys.exit(1)
    
    try:
        import fastapi
        import uvicorn
        print("✅ FastAPI/uvicorn installati")
    except ImportError:
        print("⚠️  FastAPI/uvicorn non installati (necessari per API)")
        print("   Installa con: pip install fastapi uvicorn python-multipart")
    
    # Esegui test
    results = []
    
    # Test 1: Estrattore standalone
    results.append(("Estrattore Standalone", test_standalone_extractor()))
    
    # Test 2: API endpoint (solo se server attivo)
    results.append(("API Endpoint", test_api_endpoint()))
    
    # Test 3: Integrazione
    results.append(("Integrazione", test_integration()))
    
    # Riepilogo
    print("\n" + "="*60)
    print("RIEPILOGO TEST")
    print("="*60)
    
    for test_name, passed in results:
        status = "✅ PASSED" if passed else "❌ FAILED"
        print(f"{test_name:30} {status}")
    
    all_passed = all(r[1] for r in results)
    
    if all_passed:
        print("\n🎉 TUTTI I TEST PASSATI! 🍾")
        print("Il sistema di estrazione visure è pronto all'uso!")
    else:
        print("\n⚠️  Alcuni test non sono passati")
        print("Verifica i messaggi di errore sopra")
    
    return 0 if all_passed else 1

if __name__ == "__main__":
    sys.exit(main())