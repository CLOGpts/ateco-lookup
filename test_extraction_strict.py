#!/usr/bin/env python3
"""
TEST ESTRAZIONE STRICT - Verifica che il sistema a 3 campi funzioni
"""

import re
from typing import Optional

def test_partita_iva_extraction():
    """Test estrazione P.IVA"""
    test_cases = [
        ("Partita IVA: 12345678901 registrata", "12345678901"),
        ("P.IVA 98765432109", "98765432109"),
        ("Codice Fiscale: 11111111111", "11111111111"),
        ("P.IVA: ABC123456789", None),  # Non valida
        ("Numero 123456789", None),  # Solo 9 cifre
    ]
    
    print("🔍 TEST PARTITA IVA:")
    for text, expected in test_cases:
        result = extract_partita_iva(text)
        status = "✅" if result == expected else "❌"
        print(f"  {status} Input: '{text[:30]}...' → {result}")
    print()

def test_codice_ateco_extraction():
    """Test estrazione ATECO"""
    test_cases = [
        ("Codice ATECO: 62.01", "62.01"),
        ("ATECO 47.91.10", "47.91.10"),
        ("Attività prevalente: 70.22", "70.22"),
        ("Anno 20.23 non è ATECO", None),  # Anno, non ATECO
        ("Codice: 123.45.678", None),  # Formato errato
    ]
    
    print("🔍 TEST CODICE ATECO:")
    for text, expected in test_cases:
        result = extract_codice_ateco(text)
        status = "✅" if result == expected else "❌"
        print(f"  {status} Input: '{text[:30]}...' → {result}")
    print()

def test_oggetto_sociale_extraction():
    """Test estrazione Oggetto Sociale"""
    test_cases = [
        ("OGGETTO SOCIALE: Produzione e commercializzazione di software per la gestione aziendale", True),
        ("Oggetto: Consulenza", False),  # Troppo corto
        ("OGGETTO: La società ha per oggetto la prestazione di servizi informatici", True),
        ("HA DEPOSITATO IL BILANCIO", False),  # Non è oggetto sociale
    ]
    
    print("🔍 TEST OGGETTO SOCIALE:")
    for text, should_find in test_cases:
        result = extract_oggetto_sociale(text)
        found = result is not None
        status = "✅" if found == should_find else "❌"
        print(f"  {status} Input: '{text[:40]}...' → {'TROVATO' if found else 'NON TROVATO'}")
    print()

def test_confidence_calculation():
    """Test calcolo confidence"""
    test_cases = [
        (None, None, None, 0),
        ("12345678901", None, None, 33),
        ("12345678901", "62.01", None, 66),
        ("12345678901", "62.01", "Produzione software...", 100),
    ]
    
    print("🔍 TEST CONFIDENCE:")
    for piva, ateco, oggetto, expected_score in test_cases:
        score = calculate_confidence(piva, ateco, oggetto)
        status = "✅" if score == expected_score else "❌"
        fields = []
        if piva: fields.append("P.IVA")
        if ateco: fields.append("ATECO")
        if oggetto: fields.append("OggSoc")
        print(f"  {status} Campi: {fields or ['NESSUNO']} → {score}%")
    print()

# FUNZIONI DI ESTRAZIONE (copiate dal backend_fix_visura.py)

def extract_partita_iva(text: str) -> Optional[str]:
    """Estrae P.IVA con validazione 11 cifre"""
    patterns = [
        r'(?:Partita IVA|P\.?\s?IVA|VAT)[\s:]+(\d{11})',
        r'(?:Codice Fiscale|C\.F\.)[\s:]+(\d{11})',
        r'\b(\d{11})\b'
    ]
    
    for pattern in patterns:
        matches = re.finditer(pattern, text, re.IGNORECASE)
        for match in matches:
            piva = match.group(1)
            if re.match(r'^\d{11}$', piva):
                return piva
    return None

def extract_codice_ateco(text: str) -> Optional[str]:
    """Estrae ATECO con validazione formato"""
    patterns = [
        r'(?:Codice ATECO|ATECO|Attività prevalente)[\s:]+(\d{2}[.\s]\d{2}(?:[.\s]\d{1,2})?)',
        r'\b(\d{2}\.\d{2}(?:\.\d{1,2})?)\b'
    ]
    
    for pattern in patterns:
        matches = re.finditer(pattern, text, re.IGNORECASE)
        for match in matches:
            ateco = match.group(1)
            ateco_clean = re.sub(r'\s+', '.', ateco)
            ateco_clean = re.sub(r'\.+', '.', ateco_clean)
            
            if re.match(r'^\d{2}\.\d{2}(?:\.\d{1,2})?$', ateco_clean):
                first_part = int(ateco_clean.split('.')[0])
                if first_part not in [19, 20, 21]:  # Escludi anni
                    return ateco_clean
    return None

def extract_oggetto_sociale(text: str) -> Optional[str]:
    """Estrae Oggetto Sociale con validazione"""
    patterns = [
        r'(?:OGGETTO SOCIALE|Oggetto sociale|Oggetto)[\s:]+([^\n]+(?:\n(?![A-Z]{2,}:)[^\n]+)*)',
    ]
    
    business_keywords = ['produzione', 'commercio', 'servizi', 'consulenza', 
                        'vendita', 'gestione', 'prestazione']
    
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE | re.MULTILINE | re.DOTALL)
        if match:
            oggetto = match.group(1)
            oggetto_clean = ' '.join(oggetto.split())
            
            if len(oggetto_clean) >= 30:
                has_business = any(kw in oggetto_clean.lower() for kw in business_keywords)
                if has_business:
                    if len(oggetto_clean) > 500:
                        oggetto_clean = oggetto_clean[:500] + '...'
                    return oggetto_clean
    return None

def calculate_confidence(piva, ateco, oggetto) -> int:
    """Calcola confidence score"""
    score = 0
    if piva: score += 33
    if ateco: score += 33
    if oggetto: score += 34
    return score

if __name__ == "__main__":
    print("=" * 60)
    print("🧪 TEST SISTEMA ESTRAZIONE STRICT (3 CAMPI)")
    print("=" * 60)
    print()
    
    test_partita_iva_extraction()
    test_codice_ateco_extraction()
    test_oggetto_sociale_extraction()
    test_confidence_calculation()
    
    print("=" * 60)
    print("✅ TEST COMPLETATI")
    print("=" * 60)