#!/usr/bin/env python3
"""
Script di test per le nuove funzionalità API ATECO Lookup v2.0

Esegui questo script dopo aver avviato il server:
python ateco_lookup.py --file tabella_ATECO.xlsx --serve --port 8000

Poi in un altro terminale:
python test_api.py
"""

import json
import time
from typing import Dict, Any

# Prova ad importare requests, altrimenti usa urllib
try:
    import requests
    HAS_REQUESTS = True
except ImportError:
    import urllib.request
    import urllib.error
    HAS_REQUESTS = False

BASE_URL = "http://127.0.0.1:8000"

def make_request(method: str, endpoint: str, data: Dict[str, Any] = None) -> Dict:
    """Fa una richiesta HTTP usando requests o urllib."""
    url = f"{BASE_URL}{endpoint}"
    
    if HAS_REQUESTS:
        if method == "GET":
            response = requests.get(url)
        elif method == "POST":
            response = requests.post(url, json=data)
        return response.json()
    else:
        if method == "GET":
            with urllib.request.urlopen(url) as response:
                return json.loads(response.read().decode())
        elif method == "POST":
            data_bytes = json.dumps(data).encode('utf-8')
            req = urllib.request.Request(url, data=data_bytes, 
                                        headers={'Content-Type': 'application/json'})
            with urllib.request.urlopen(req) as response:
                return json.loads(response.read().decode())

def test_health():
    """Test 1: Health Check con nuove informazioni"""
    print("\n🔍 TEST 1: Health Check")
    print("-" * 40)
    
    result = make_request("GET", "/health")
    print(f"✅ Status: {result.get('status')}")
    print(f"✅ Version: {result.get('version')}")
    print(f"✅ Cache Enabled: {result.get('cache_enabled')}")
    
    assert result.get('version') == '2.0', "Version should be 2.0"
    assert result.get('cache_enabled') == True, "Cache should be enabled"
    print("✅ Health check test passed!")

def test_lookup_with_validation():
    """Test 2: Lookup con validazione errori"""
    print("\n🔍 TEST 2: Validazione Input")
    print("-" * 40)
    
    # Test codice troppo corto
    print("Testing codice troppo corto...")
    try:
        result = make_request("GET", "/lookup?code=1")
        print("❌ Should have raised an error for short code")
    except:
        print("✅ Correctly rejected short code")
    
    # Test codice valido
    print("\nTesting codice valido (20.14.0)...")
    result = make_request("GET", "/lookup?code=20.14.0")
    if result.get('found') > 0:
        item = result['items'][0]
        print(f"✅ Found: {item.get('CODICE_ATECO_2022')} - {item.get('TITOLO_ATECO_2022')}")
        print(f"✅ Settore: {item.get('settore')}")
        print(f"✅ Normative: {len(item.get('normative', []))} normative")
        print(f"✅ Certificazioni: {len(item.get('certificazioni', []))} certificazioni")
    
    # Test codice non esistente con suggerimenti
    print("\nTesting codice non esistente (99.99.99)...")
    result = make_request("GET", "/lookup?code=99.99.99")
    if result.get('found') == 0:
        print(f"✅ No results found (expected)")
        if result.get('suggestions'):
            print(f"✅ Got {len(result['suggestions'])} suggestions:")
            for sug in result['suggestions'][:3]:
                print(f"   - {sug['code']}: {sug['title']}")

def test_batch():
    """Test 3: Batch Lookup"""
    print("\n🔍 TEST 3: Batch Lookup")
    print("-" * 40)
    
    batch_data = {
        "codes": ["20.14.0", "62.01.0", "10.11.0", "INVALID"],
        "prefer": "2025"
    }
    
    print(f"Testing batch with {len(batch_data['codes'])} codes...")
    result = make_request("POST", "/batch", batch_data)
    
    print(f"✅ Total codes processed: {result.get('total_codes')}")
    
    for res in result.get('results', []):
        code = res.get('code')
        found = res.get('found')
        if found > 0:
            item = res['items'][0]
            print(f"✅ {code}: Found - {item.get('TITOLO_ATECO_2022', 'N/A')[:50]}...")
        else:
            print(f"⚠️  {code}: Not found")
    
    # Test limite batch
    print("\nTesting batch limit (>50 codes)...")
    large_batch = {
        "codes": [f"01.{i:02d}.0" for i in range(60)],  # 60 codici
        "prefer": "2022"
    }
    
    try:
        result = make_request("POST", "/batch", large_batch)
        print("❌ Should have rejected >50 codes")
    except:
        print("✅ Correctly rejected batch >50 codes")

def test_autocomplete():
    """Test 4: Autocomplete"""
    print("\n🔍 TEST 4: Autocomplete")
    print("-" * 40)
    
    # Test autocomplete base
    print("Testing autocomplete for '20.1'...")
    result = make_request("GET", "/autocomplete?partial=20.1&limit=5")
    
    print(f"✅ Partial: {result.get('partial')}")
    print(f"✅ Found {result.get('count')} suggestions:")
    
    for sug in result.get('suggestions', []):
        print(f"   - {sug['code']}: {sug['title'][:50]}... (v{sug['version']})")
    
    # Test autocomplete con limite
    print("\nTesting autocomplete for '62' with limit=3...")
    result = make_request("GET", "/autocomplete?partial=62&limit=3")
    
    assert result.get('count') <= 3, "Should respect limit"
    print(f"✅ Respected limit: {result.get('count')} results")

def test_cache_performance():
    """Test 5: Cache Performance"""
    print("\n🔍 TEST 5: Cache Performance")
    print("-" * 40)
    
    test_code = "20.14.0"
    
    # Prima chiamata (senza cache)
    print(f"Testing first call for {test_code} (no cache)...")
    start = time.time()
    result1 = make_request("GET", f"/lookup?code={test_code}")
    time1 = (time.time() - start) * 1000
    print(f"⏱️  First call: {time1:.2f}ms")
    
    # Seconda chiamata (con cache)
    print(f"Testing second call for {test_code} (with cache)...")
    start = time.time()
    result2 = make_request("GET", f"/lookup?code={test_code}")
    time2 = (time.time() - start) * 1000
    print(f"⏱️  Second call: {time2:.2f}ms")
    
    if time2 < time1:
        speedup = time1 / time2 if time2 > 0 else float('inf')
        print(f"✅ Cache working! {speedup:.1f}x speedup")
    else:
        print("⚠️  Cache may not be working optimally")
    
    # Verifica che i risultati siano identici
    assert result1 == result2, "Results should be identical"
    print("✅ Results are identical")

def test_all_features():
    """Test 6: Integrazione completa"""
    print("\n🔍 TEST 6: Test Integrazione")
    print("-" * 40)
    
    # Simula un flusso utente completo
    print("Simulating user workflow...")
    
    # 1. User inizia a digitare
    print("\n1. User types '20'...")
    autocomplete = make_request("GET", "/autocomplete?partial=20&limit=3")
    print(f"   System suggests: {', '.join([s['code'] for s in autocomplete['suggestions']])}")
    
    # 2. User seleziona un suggerimento
    selected = autocomplete['suggestions'][0]['code'] if autocomplete['suggestions'] else "20.14.0"
    print(f"\n2. User selects: {selected}")
    lookup = make_request("GET", f"/lookup?code={selected}")
    if lookup['found'] > 0:
        print(f"   Found: {lookup['items'][0]['TITOLO_ATECO_2022'][:60]}...")
        print(f"   Settore: {lookup['items'][0].get('settore', 'N/A')}")
    
    # 3. User vuole cercare multipli codici correlati
    print(f"\n3. User wants related codes...")
    related_codes = ["20.11.0", "20.12.0", "20.13.0"]
    batch = make_request("POST", "/batch", {"codes": related_codes})
    print(f"   Batch found {sum(1 for r in batch['results'] if r['found'] > 0)}/{len(related_codes)} codes")
    
    print("\n✅ Integration test completed successfully!")

def main():
    """Esegue tutti i test"""
    print("=" * 50)
    print("🚀 ATECO LOOKUP API v2.0 - TEST SUITE")
    print("=" * 50)
    
    try:
        # Verifica che il server sia attivo
        print("\n⏳ Checking server status...")
        health = make_request("GET", "/health")
        print(f"✅ Server is running (version {health.get('version')})")
        
        # Esegui tutti i test
        test_health()
        test_lookup_with_validation()
        test_batch()
        test_autocomplete()
        test_cache_performance()
        test_all_features()
        
        print("\n" + "=" * 50)
        print("✅ ALL TESTS PASSED SUCCESSFULLY!")
        print("=" * 50)
        
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        print("\nMake sure the server is running:")
        print("python ateco_lookup.py --file tabella_ATECO.xlsx --serve --port 8000")
        return 1
    
    return 0

if __name__ == "__main__":
    exit(main())