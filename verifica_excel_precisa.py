#!/usr/bin/env python3
"""
Script di VERIFICA PRECISA dei dati Excel
Legge direttamente dal file Excel originale e mostra ESATTAMENTE cosa c'è
"""

import json
import sys

# Prova ad usare diverse librerie per leggere Excel
try:
    # Metodo 1: openpyxl (preferito per .xlsx)
    import openpyxl
    METODO = "openpyxl"
    print("✓ Uso openpyxl per leggere l'Excel")
except ImportError:
    try:
        # Metodo 2: pandas
        import pandas as pd
        METODO = "pandas"
        print("✓ Uso pandas per leggere l'Excel")
    except ImportError:
        try:
            # Metodo 3: xlrd
            import xlrd
            METODO = "xlrd"
            print("✓ Uso xlrd per leggere l'Excel")
        except ImportError:
            print("❌ ERRORE: Nessuna libreria Excel disponibile!")
            print("Installa con: pip install openpyxl")
            sys.exit(1)

def leggi_con_openpyxl():
    """Estrae dati precisi usando openpyxl"""
    print("\n" + "="*60)
    print("ESTRAZIONE PRECISA DAI FOGLI EXCEL")
    print("="*60)
    
    wb = openpyxl.load_workbook('Operational Risk Mapping Globale - Copia.xlsx', data_only=True)
    
    # 1. ANALISI FOGLIO "work" - LE MAPPATURE
    print("\n📋 FOGLIO 'work' - Mappature Categoria → Eventi")
    print("-"*50)
    
    ws_work = wb['work']
    mappature = {}
    
    # Colonne del foglio work (come da documentazione)
    colonne_categorie = [
        ('B', 'Internal_Fraud_Frodi_interne'),
        ('D', 'External_fraud_Frodi_esterne'),
        ('F', 'Employment_practices_Dipendenti'),
        ('H', 'Clients_product_Clienti'),
        ('J', 'Damage_Danni'),
        ('L', 'Business_disruption'),
        ('N', 'Execution_delivery_Problemi_di_produzione_o_consegna')
    ]
    
    # Per ogni categoria, leggi gli eventi dalla colonna
    for col_letter, categoria in colonne_categorie:
        eventi = []
        
        # Leggi dalla riga 2 fino a quando trovi celle vuote
        for row in range(2, 200):  # Massimo 200 righe
            cell = ws_work[f'{col_letter}{row}']
            if cell.value and str(cell.value).strip():
                evento = str(cell.value).strip()
                eventi.append(evento)
        
        # Per Execution, leggi anche la colonna P (ha 2 colonne)
        if categoria == 'Execution_delivery_Problemi_di_produzione_o_consegna':
            for row in range(2, 200):
                cell = ws_work[f'P{row}']
                if cell.value and str(cell.value).strip():
                    evento = str(cell.value).strip()
                    eventi.append(evento)
        
        mappature[categoria] = eventi
        print(f"\n{categoria}:")
        print(f"  Colonna: {col_letter}")
        print(f"  N° eventi: {len(eventi)}")
        if len(eventi) > 0:
            print(f"  Primo evento: {eventi[0]}")
            print(f"  Ultimo evento: {eventi[-1]}")
    
    # 2. ANALISI FOGLIO "Analisi As-IS" - TABELLA VLOOKUP
    print("\n\n📊 FOGLIO 'Analisi As-IS' - Tabella VLOOKUP")
    print("-"*50)
    
    ws_analisi = wb['Analisi As-IS']
    
    # La tabella VLOOKUP è nelle righe 1001-1200, colonne F e G
    print("\nTabella nascosta (righe 1001-1200):")
    
    descrizioni = {}
    for row in range(1001, 1201):
        # Colonna F = Codice evento
        cell_f = ws_analisi[f'F{row}']
        # Colonna G = Descrizione
        cell_g = ws_analisi[f'G{row}']
        
        if cell_f.value and cell_g.value:
            evento = str(cell_f.value).strip()
            descrizione = str(cell_g.value).strip()
            descrizioni[evento] = descrizione
    
    print(f"  Totale coppie evento-descrizione: {len(descrizioni)}")
    
    # Mostra alcuni esempi
    if descrizioni:
        print("\n  Primi 3 esempi di VLOOKUP:")
        for i, (evt, desc) in enumerate(list(descrizioni.items())[:3]):
            print(f"\n  [{i+1}] Evento: {evt}")
            print(f"      Descrizione: {desc[:100]}...")
    
    # 3. VERIFICA FORMULA VLOOKUP
    print("\n\n🔍 VERIFICA FORMULA VLOOKUP")
    print("-"*50)
    
    # Cerca la formula nella colonna G (righe 5-456)
    formule_trovate = []
    for row in range(5, 50):  # Controllo prime righe
        cell = ws_analisi[f'G{row}']
        if hasattr(cell, 'formula') and cell.formula:
            formule_trovate.append((row, cell.formula))
    
    if formule_trovate:
        print(f"Formula trovata nella riga {formule_trovate[0][0]}:")
        print(f"  {formule_trovate[0][1]}")
    
    # 4. STATISTICHE COMPLETE
    print("\n\n📈 STATISTICHE FINALI")
    print("-"*50)
    
    totale_eventi = sum(len(eventi) for eventi in mappature.values())
    print(f"  Categorie totali: {len(mappature)}")
    print(f"  Eventi totali mappati: {totale_eventi}")
    print(f"  Descrizioni nella lookup: {len(descrizioni)}")
    
    # Verifica corrispondenze
    print("\n  Verifica corrispondenze:")
    
    # Tutti gli eventi dalle mappature
    tutti_eventi = []
    for eventi in mappature.values():
        tutti_eventi.extend(eventi)
    
    # Controlla quali eventi non hanno descrizione
    senza_desc = []
    for evento in tutti_eventi:
        if evento not in descrizioni:
            senza_desc.append(evento)
    
    if senza_desc:
        print(f"  ⚠️ {len(senza_desc)} eventi SENZA descrizione:")
        for e in senza_desc[:5]:
            print(f"     - {e}")
    else:
        print("  ✅ TUTTI gli eventi hanno una descrizione!")
    
    # Controlla quali descrizioni non hanno evento mappato
    desc_orfane = []
    for evento_desc in descrizioni.keys():
        if evento_desc not in tutti_eventi:
            desc_orfane.append(evento_desc)
    
    if desc_orfane:
        print(f"\n  ⚠️ {len(desc_orfane)} descrizioni SENZA evento mappato:")
        for e in desc_orfane[:5]:
            print(f"     - {e}")
    
    # 5. SALVA I DATI CORRETTI
    print("\n\n💾 SALVATAGGIO DATI CORRETTI")
    print("-"*50)
    
    dati_corretti = {
        "mappature_categoria_eventi": mappature,
        "descrizioni_vlookup": descrizioni,
        "statistiche": {
            "totale_categorie": len(mappature),
            "totale_eventi": totale_eventi,
            "totale_descrizioni": len(descrizioni),
            "eventi_senza_desc": len(senza_desc),
            "desc_senza_evento": len(desc_orfane)
        }
    }
    
    # Salva il JSON corretto
    with open('dati_excel_verificati.json', 'w', encoding='utf-8') as f:
        json.dump(dati_corretti, f, ensure_ascii=False, indent=2)
    
    print("  ✓ Salvato: dati_excel_verificati.json")
    
    return dati_corretti

def leggi_con_pandas():
    """Estrae dati usando pandas"""
    print("\n" + "="*60)
    print("ESTRAZIONE CON PANDAS")
    print("="*60)
    
    # Leggi foglio work
    df_work = pd.read_excel('Operational Risk Mapping Globale - Copia.xlsx', 
                            sheet_name='work', header=None)
    
    # Leggi foglio Analisi As-IS
    df_analisi = pd.read_excel('Operational Risk Mapping Globale - Copia.xlsx', 
                               sheet_name='Analisi As-IS', header=None)
    
    print("\nFoglio 'work' dimensioni:", df_work.shape)
    print("Foglio 'Analisi As-IS' dimensioni:", df_analisi.shape)
    
    # Estrai mappature dal foglio work
    mappature = {}
    
    # Colonne: B=1, D=3, F=5, H=7, J=9, L=11, N=13, P=15
    colonne_map = {
        1: 'Internal_Fraud_Frodi_interne',
        3: 'External_fraud_Frodi_esterne',
        5: 'Employment_practices_Dipendenti',
        7: 'Clients_product_Clienti',
        9: 'Damage_Danni',
        11: 'Business_disruption',
        13: 'Execution_delivery_Problemi_di_produzione_o_consegna'
    }
    
    for col_idx, categoria in colonne_map.items():
        # Prendi colonna dal dataframe (salta riga header)
        eventi = df_work.iloc[1:, col_idx].dropna().astype(str).str.strip()
        eventi = [e for e in eventi if e and e != 'nan']
        
        # Per Execution, aggiungi anche colonna P (indice 15)
        if categoria == 'Execution_delivery_Problemi_di_produzione_o_consegna':
            eventi_p = df_work.iloc[1:, 15].dropna().astype(str).str.strip()
            eventi_p = [e for e in eventi_p if e and e != 'nan']
            eventi.extend(eventi_p)
        
        mappature[categoria] = eventi
        print(f"\n{categoria}: {len(eventi)} eventi")
    
    # Estrai descrizioni dalle righe 1000+ del foglio Analisi
    print("\n\nEstrazione tabella VLOOKUP...")
    
    # Le righe 1000-1199 corrispondono agli indici 1000-1199
    # Colonne F=5, G=6
    descrizioni = {}
    for idx in range(1000, 1200):
        if idx < len(df_analisi):
            evento = df_analisi.iloc[idx, 5]  # Colonna F
            desc = df_analisi.iloc[idx, 6]    # Colonna G
            
            if pd.notna(evento) and pd.notna(desc):
                descrizioni[str(evento).strip()] = str(desc).strip()
    
    print(f"Trovate {len(descrizioni)} descrizioni")
    
    # Salva
    dati = {
        "mappature_categoria_eventi": mappature,
        "descrizioni_vlookup": descrizioni
    }
    
    with open('dati_excel_verificati.json', 'w', encoding='utf-8') as f:
        json.dump(dati, f, ensure_ascii=False, indent=2)
    
    return dati

# ESECUZIONE PRINCIPALE
if __name__ == "__main__":
    try:
        if METODO == "openpyxl":
            dati = leggi_con_openpyxl()
        elif METODO == "pandas":
            dati = leggi_con_pandas()
        else:
            print("Metodo xlrd non ancora implementato")
            sys.exit(1)
        
        print("\n" + "="*60)
        print("✅ VERIFICA COMPLETATA!")
        print("="*60)
        print("\nProssimi passi:")
        print("1. Controlla il file 'dati_excel_verificati.json'")
        print("2. Aggiorna excel_server_simple.py con i dati corretti")
        print("3. Testa con test_finale.html")
        
    except Exception as e:
        print(f"\n❌ ERRORE: {e}")
        import traceback
        traceback.print_exc()