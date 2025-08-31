#!/usr/bin/env python3
"""
Analisi CERTOSINA delle righe 1000+ del foglio Analisi As-IS
Qui c'è TUTTO l'albero delle mappature!
"""

import json
import zipfile
import xml.etree.ElementTree as ET
import re

def analizza_righe_1000():
    """Estrae TUTTO dalle righe 1000+ del foglio Analisi As-IS"""
    
    print("="*80)
    print("ANALISI CERTOSINA RIGHE 1000+ - FOGLIO ANALISI AS-IS")
    print("="*80)
    
    # Apri il file Excel come ZIP
    with zipfile.ZipFile('Operational Risk Mapping Globale - Copia.xlsx', 'r') as z:
        # Estrai stringhe condivise
        shared_strings = []
        if 'xl/sharedStrings.xml' in z.namelist():
            with z.open('xl/sharedStrings.xml') as f:
                tree = ET.parse(f)
                root = tree.getroot()
                for si in root.findall('.//{http://schemas.openxmlformats.org/spreadsheetml/2006/main}si'):
                    t_elem = si.find('.//{http://schemas.openxmlformats.org/spreadsheetml/2006/main}t')
                    if t_elem is not None and t_elem.text:
                        shared_strings.append(t_elem.text)
        
        print(f"✓ Caricate {len(shared_strings)} stringhe condivise\n")
        
        # Trova il foglio Analisi As-IS (sheet2)
        with z.open('xl/worksheets/sheet2.xml') as f:
            tree = ET.parse(f)
            root = tree.getroot()
            
            # Namespace
            ns = {'': 'http://schemas.openxmlformats.org/spreadsheetml/2006/main'}
            
            # Dizionario per memorizzare i dati per riga/colonna
            dati_righe_1000 = {}
            
            # Trova tutte le celle
            for row in root.findall('.//row', ns):
                row_num = int(row.get('r', 0))
                
                # Ci interessano solo le righe >= 1000
                if row_num >= 1000:
                    for cell in row.findall('.//c', ns):
                        cell_ref = cell.get('r', '')
                        
                        # Estrai colonna e riga
                        match = re.match(r'([A-Z]+)(\d+)', cell_ref)
                        if match:
                            col = match.group(1)
                            row = int(match.group(2))
                            
                            # Estrai valore
                            v_elem = cell.find('.//v', ns)
                            if v_elem is not None and v_elem.text:
                                cell_type = cell.get('t', '')
                                
                                if cell_type == 's':  # Stringa condivisa
                                    idx = int(v_elem.text)
                                    if idx < len(shared_strings):
                                        value = shared_strings[idx]
                                    else:
                                        value = f"[String index {idx}]"
                                else:
                                    value = v_elem.text
                                
                                # Salva il dato
                                if row not in dati_righe_1000:
                                    dati_righe_1000[row] = {}
                                dati_righe_1000[row][col] = value
    
    # Analizza i dati trovati
    print("\n📊 ANALISI DATI TROVATI DALLE RIGHE 1000+\n")
    print("-"*80)
    
    # Organizza per colonne di interesse (E, F, G sono le principali)
    colonna_e = {}  # Categoria
    colonna_f = {}  # Evento
    colonna_g = {}  # Descrizione
    
    for row in sorted(dati_righe_1000.keys()):
        if row <= 1300:  # Limitiamo l'analisi
            dati_riga = dati_righe_1000[row]
            
            if 'E' in dati_riga:
                colonna_e[row] = dati_riga['E']
            if 'F' in dati_riga:
                colonna_f[row] = dati_riga['F']
            if 'G' in dati_riga:
                colonna_g[row] = dati_riga['G']
    
    # Mostra struttura colonna E (Categorie)
    print("\n🔍 COLONNA E - CATEGORIE (righe 1000+):")
    print("-"*50)
    categorie_trovate = {}
    for row, val in sorted(colonna_e.items())[:20]:
        print(f"  Riga {row}: {val}")
        if val and val.strip():
            # Conta occorrenze per capire struttura
            if val not in categorie_trovate:
                categorie_trovate[val] = []
            categorie_trovate[val].append(row)
    
    print(f"\n  Categorie uniche trovate: {len(categorie_trovate)}")
    for cat, righe in list(categorie_trovate.items())[:7]:
        print(f"    • {cat}: appare in {len(righe)} righe")
    
    # Mostra struttura colonna F (Eventi)
    print("\n\n🔍 COLONNA F - EVENTI (righe 1000+):")
    print("-"*50)
    eventi_trovati = {}
    for row, val in sorted(colonna_f.items())[:10]:
        print(f"  Riga {row}: {val[:60]}..." if len(val) > 60 else f"  Riga {row}: {val}")
        if val and val.strip():
            eventi_trovati[row] = val
    
    print(f"\n  Totale eventi trovati: {len(eventi_trovati)}")
    
    # Mostra struttura colonna G (Descrizioni)
    print("\n\n🔍 COLONNA G - DESCRIZIONI (righe 1000+):")
    print("-"*50)
    descrizioni_trovate = {}
    for row, val in sorted(colonna_g.items())[:10]:
        print(f"  Riga {row}: {val[:60]}..." if len(val) > 60 else f"  Riga {row}: {val}")
        if val and val.strip():
            descrizioni_trovate[row] = val
    
    print(f"\n  Totale descrizioni trovate: {len(descrizioni_trovate)}")
    
    # ANALISI DELL'ALBERO - Cerca pattern categoria->evento
    print("\n\n🌳 ANALISI ALBERO CATEGORIA → EVENTO → DESCRIZIONE")
    print("-"*80)
    
    # Costruisci l'albero
    albero = {}
    categoria_corrente = None
    
    for row in sorted(dati_righe_1000.keys()):
        if row > 1300:
            break
            
        # Se c'è una categoria in colonna E
        if row in colonna_e and colonna_e[row].strip():
            categoria_corrente = colonna_e[row].strip()
            if categoria_corrente not in albero:
                albero[categoria_corrente] = []
            print(f"\n📁 CATEGORIA: {categoria_corrente}")
        
        # Se c'è un evento in colonna F con la categoria corrente
        if row in colonna_f and categoria_corrente:
            evento = colonna_f[row].strip()
            descrizione = colonna_g.get(row, "").strip()
            
            if evento:
                albero[categoria_corrente].append({
                    'riga': row,
                    'evento': evento,
                    'descrizione': descrizione
                })
                print(f"    └─ [{row}] {evento[:50]}...")
                if descrizione:
                    print(f"         → {descrizione[:50]}...")
    
    # Statistiche finali
    print("\n\n📈 STATISTICHE ALBERO COMPLETO:")
    print("-"*50)
    
    for categoria, eventi in albero.items():
        print(f"\n{categoria}:")
        print(f"  • Totale eventi: {len(eventi)}")
        if eventi:
            print(f"  • Primo evento: {eventi[0]['evento'][:50]}...")
            print(f"  • Ultimo evento: {eventi[-1]['evento'][:50]}...")
    
    # Salva l'albero completo
    print("\n\n💾 SALVATAGGIO ALBERO COMPLETO")
    print("-"*50)
    
    # Prepara struttura per export
    export_data = {
        'albero_completo': {},
        'mappatura_vlookup': {},
        'statistiche': {}
    }
    
    # Costruisci mappature pulite
    for categoria, eventi in albero.items():
        export_data['albero_completo'][categoria] = []
        for evt in eventi:
            export_data['albero_completo'][categoria].append(evt['evento'])
            # Mappa evento -> descrizione per VLOOKUP
            if evt['evento'] and evt['descrizione']:
                export_data['mappatura_vlookup'][evt['evento']] = evt['descrizione']
    
    # Statistiche
    export_data['statistiche'] = {
        'totale_categorie': len(albero),
        'totale_eventi': sum(len(e) for e in albero.values()),
        'totale_descrizioni': len(export_data['mappatura_vlookup']),
        'eventi_per_categoria': {cat: len(eventi) for cat, eventi in albero.items()}
    }
    
    # Salva JSON
    with open('albero_excel_righe_1000.json', 'w', encoding='utf-8') as f:
        json.dump(export_data, f, ensure_ascii=False, indent=2)
    
    print("✓ Salvato: albero_excel_righe_1000.json")
    
    # Mostra riepilogo
    print("\n" + "="*80)
    print("RIEPILOGO FINALE")
    print("="*80)
    print(f"✓ Categorie trovate: {len(albero)}")
    print(f"✓ Eventi totali: {sum(len(e) for e in albero.values())}")
    print(f"✓ Descrizioni mappate: {len(export_data['mappatura_vlookup'])}")
    
    return export_data

if __name__ == "__main__":
    try:
        dati = analizza_righe_1000()
        print("\n✅ ANALISI COMPLETATA!")
        print("\nOra possiamo fare i test comparativi:")
        print("1. Tu leggi dall'Excel")
        print("2. Io leggo dal JSON estratto")
        print("3. Verifichiamo che tutto corrisponda!")
    except Exception as e:
        print(f"\n❌ ERRORE: {e}")
        import traceback
        traceback.print_exc()