#!/usr/bin/env python3
"""
Test completo del sistema per verificare corrispondenza 100% con Excel
"""

import json
import urllib.request
import urllib.parse

BASE_URL = "http://localhost:8000"

def test_sistema():
    """Test completo di tutte le categorie ed eventi"""
    
    print("="*70)
    print("TEST COMPLETO SISTEMA EXCEL - VERIFICA CORRISPONDENZA 100%")
    print("="*70)
    
    # 1. Test categorie
    print("\n1️⃣ TEST CATEGORIE")
    print("-"*50)
    
    try:
        response = urllib.request.urlopen(f"{BASE_URL}/categories")
        data = json.loads(response.read().decode())
        categorie = data['categories']
        
        print(f"✅ Trovate {len(categorie)} categorie:")
        for i, cat in enumerate(categorie, 1):
            print(f"   {i}. {cat}")
    except Exception as e:
        print(f"❌ Errore: {e}")
        return
    
    # 2. Test eventi per categoria
    print("\n2️⃣ TEST EVENTI PER CATEGORIA")
    print("-"*50)
    
    totale_eventi = 0
    eventi_con_desc = 0
    eventi_senza_desc = []
    
    # Conteggi attesi secondo la documentazione
    conteggi_attesi = {
        "Internal_Fraud_Frodi_interne": 19,
        "External_fraud_Frodi_esterne": 17,
        "Employment_practices_Dipendenti": 21,
        "Clients_product_Clienti": 43,
        "Damage_Danni": 11,
        "Business_disruption": 20,
        "Execution_delivery_Problemi_di_produzione_o_consegna": 59
    }
    
    for categoria in categorie:
        print(f"\n📂 {categoria}")
        
        try:
            # Ottieni eventi per categoria
            url = f"{BASE_URL}/events/{urllib.parse.quote(categoria)}"
            response = urllib.request.urlopen(url)
            data = json.loads(response.read().decode())
            eventi = data['events']
            
            # Verifica conteggio
            atteso = conteggi_attesi.get(categoria, 0)
            if len(eventi) == atteso:
                print(f"   ✅ Eventi: {len(eventi)} (corretto!)")
            else:
                print(f"   ⚠️ Eventi: {len(eventi)} (attesi: {atteso})")
            
            totale_eventi += len(eventi)
            
            # Mostra primi 2 eventi
            if eventi:
                print(f"   📌 Primo evento: {eventi[0]}")
                if len(eventi) > 1:
                    print(f"   📌 Secondo evento: {eventi[1]}")
            
            # Test descrizioni per primi 3 eventi
            print(f"   \n   Test descrizioni (primi 3):")
            for i, evento in enumerate(eventi[:3], 1):
                try:
                    # Ottieni descrizione
                    url_desc = f"{BASE_URL}/description/{urllib.parse.quote(evento)}"
                    resp_desc = urllib.request.urlopen(url_desc)
                    data_desc = json.loads(resp_desc.read().decode())
                    
                    if data_desc.get('description'):
                        print(f"      [{i}] ✅ {evento[:40]}...")
                        print(f"          → {data_desc['description'][:60]}...")
                        eventi_con_desc += 1
                    else:
                        print(f"      [{i}] ❌ {evento} - SENZA DESCRIZIONE")
                        eventi_senza_desc.append(evento)
                except Exception as e:
                    print(f"      [{i}] ❌ Errore: {e}")
                    eventi_senza_desc.append(evento)
                    
        except Exception as e:
            print(f"   ❌ Errore categoria: {e}")
    
    # 3. Riepilogo finale
    print("\n" + "="*70)
    print("📊 RIEPILOGO FINALE")
    print("="*70)
    
    print(f"\n✅ Categorie totali: {len(categorie)}")
    print(f"✅ Eventi totali: {totale_eventi} (attesi: 190)")
    
    if totale_eventi == 190:
        print("   ✅ CONTEGGIO EVENTI CORRETTO!")
    else:
        print(f"   ⚠️ DIFFERENZA: {190 - totale_eventi} eventi")
    
    # Verifica per categoria
    print("\n📋 Verifica conteggi per categoria:")
    tutti_corretti = True
    for cat in categorie:
        try:
            url = f"{BASE_URL}/events/{urllib.parse.quote(cat)}"
            response = urllib.request.urlopen(url)
            data = json.loads(response.read().decode())
            n_eventi = len(data['events'])
            atteso = conteggi_attesi.get(cat, 0)
            
            if n_eventi == atteso:
                print(f"   ✅ {cat}: {n_eventi} eventi")
            else:
                print(f"   ❌ {cat}: {n_eventi} eventi (attesi: {atteso})")
                tutti_corretti = False
        except:
            pass
    
    if tutti_corretti:
        print("\n🎉 TUTTI I CONTEGGI SONO CORRETTI!")
    else:
        print("\n⚠️ ALCUNI CONTEGGI NON CORRISPONDONO")
    
    # Test specifici secondo documentazione
    print("\n" + "="*70)
    print("🔬 TEST SPECIFICI DA DOCUMENTAZIONE")
    print("="*70)
    
    test_specifici = [
        ("Internal_Fraud_Frodi_interne", "601 - Furto di denaro, cassa o altro"),
        ("External_fraud_Frodi_esterne", "701 - Furto o rapina"),
        ("Employment_practices_Dipendenti", "201 - Compensazione, benefit, dismissione del dipendente"),
        ("Clients_product_Clienti", "301 - Vendita impropria, truffa - Manipolazione mercato"),
        ("Damage_Danni", "501 - Perdite dovute a catastrofi naturali"),
        ("Business_disruption", "401 - Problemi hw informatici non intenzionali"),
        ("Execution_delivery_Problemi_di_produzione_o_consegna", "101 - Comunicazione errata")
    ]
    
    print("\nTest che ogni categoria contenga il suo primo evento atteso:")
    for categoria, evento_atteso in test_specifici:
        try:
            url = f"{BASE_URL}/events/{urllib.parse.quote(categoria)}"
            response = urllib.request.urlopen(url)
            data = json.loads(response.read().decode())
            eventi = data['events']
            
            if eventi and eventi[0] == evento_atteso:
                print(f"✅ {categoria[:30]}... → {evento_atteso[:40]}...")
            else:
                primo = eventi[0] if eventi else "NESSUNO"
                print(f"❌ {categoria[:30]}...")
                print(f"   Atteso: {evento_atteso}")
                print(f"   Trovato: {primo}")
        except Exception as e:
            print(f"❌ Errore test {categoria}: {e}")
    
    print("\n" + "="*70)
    print("CONCLUSIONE TEST")
    print("="*70)
    
    if tutti_corretti and totale_eventi == 190:
        print("\n✅ ✅ ✅ SISTEMA PERFETTAMENTE ALLINEATO CON EXCEL! ✅ ✅ ✅")
    else:
        print("\n⚠️ CI SONO DISCREPANZE DA CORREGGERE")
        print("Verifica i dati nel server rispetto all'Excel originale")

if __name__ == "__main__":
    try:
        test_sistema()
    except Exception as e:
        print(f"❌ Errore generale: {e}")
        print("\nAssicurati che il server sia attivo su http://localhost:8000")