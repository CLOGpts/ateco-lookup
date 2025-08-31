#!/usr/bin/env python3
"""
Estrae le VERE mappature categoria->eventi dall'Excel
Analizzando il foglio 'work' con la logica corretta
"""

import json
import zipfile
import xml.etree.ElementTree as ET
import re

def estrai_mappature_reali():
    """Estrae le mappature REALI dal foglio work"""
    
    print("="*80)
    print("ESTRAZIONE MAPPATURE CORRETTE DAL FOGLIO 'work'")
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
        
        # Apri il foglio 'work' (sheet5.xml)
        with z.open('xl/worksheets/sheet5.xml') as f:
            tree = ET.parse(f)
            root = tree.getroot()
            
            # Namespace
            ns = {'': 'http://schemas.openxmlformats.org/spreadsheetml/2006/main'}
            
            # Dizionario per memorizzare i dati per colonna
            dati_colonne = {}
            
            # Estrai tutte le celle
            for row in root.findall('.//row', ns):
                for cell in row.findall('.//c', ns):
                    cell_ref = cell.get('r', '')
                    
                    # Estrai colonna e riga
                    match = re.match(r'([A-Z]+)(\d+)', cell_ref)
                    if match:
                        col = match.group(1)
                        row_num = int(match.group(2))
                        
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
                            if col not in dati_colonne:
                                dati_colonne[col] = {}
                            dati_colonne[col][row_num] = value
    
    # Analizza le colonne del foglio 'work'
    print("\n📊 ANALISI COLONNE DEL FOGLIO 'work'")
    print("-"*80)
    
    # Mappatura attesa basata sulla documentazione
    # Colonne pari = eventi, colonne dispari = categorie (potenzialmente)
    colonne_eventi = ['B', 'D', 'F', 'H', 'J', 'L', 'N', 'P']
    
    mappature = {}
    
    # Per ogni colonna di eventi
    for col in colonne_eventi:
        if col in dati_colonne:
            print(f"\n📁 Colonna {col}:")
            
            # Estrai tutti i valori non vuoti
            eventi = []
            for row in sorted(dati_colonne[col].keys()):
                val = dati_colonne[col][row]
                if val and val.strip() and row > 1:  # Salta header
                    eventi.append(val.strip())
            
            if eventi:
                # Analizza il pattern dei codici
                codici = []
                for evt in eventi:
                    # Cerca pattern tipo "501 - descrizione"
                    match = re.match(r'^(\d+)\s*-\s*(.+)', evt)
                    if match:
                        codici.append(int(match.group(1)))
                
                if codici:
                    min_code = min(codici)
                    max_code = max(codici)
                    
                    # Determina la categoria basandosi sui codici
                    categoria = None
                    if 100 <= min_code < 200:
                        categoria = "Execution_delivery_Problemi_di_produzione_o_consegna"
                    elif 200 <= min_code < 300:
                        categoria = "Business_disruption"
                    elif 300 <= min_code < 400:
                        categoria = "Employment_practices_Dipendenti"  
                    elif 400 <= min_code < 500:
                        categoria = "Damage_Danni"
                    elif 500 <= min_code < 600:
                        categoria = "Clients_product_Clienti"
                    elif 600 <= min_code < 700:
                        categoria = "Internal_Fraud_Frodi_interne"
                    elif 700 <= min_code < 800:
                        categoria = "External_fraud_Frodi_esterne"
                    
                    if categoria:
                        if categoria not in mappature:
                            mappature[categoria] = []
                        mappature[categoria].extend(eventi)
                        
                        print(f"  Categoria identificata: {categoria}")
                        print(f"  Range codici: {min_code}-{max_code}")
                        print(f"  Totale eventi: {len(eventi)}")
                        print(f"  Primo evento: {eventi[0][:60]}...")
                        if len(eventi) > 1:
                            print(f"  Ultimo evento: {eventi[-1][:60]}...")
    
    # Ora estrai anche le descrizioni dalle righe 1000+ del foglio Analisi As-IS
    print("\n\n📊 ESTRAZIONE DESCRIZIONI (VLOOKUP) DAL FOGLIO 'Analisi As-IS'")
    print("-"*80)
    
    descrizioni = {}
    
    with zipfile.ZipFile('Operational Risk Mapping Globale - Copia.xlsx', 'r') as z:
        # Ricarica stringhe condivise (per sicurezza)
        shared_strings = []
        if 'xl/sharedStrings.xml' in z.namelist():
            with z.open('xl/sharedStrings.xml') as f:
                tree = ET.parse(f)
                root = tree.getroot()
                for si in root.findall('.//{http://schemas.openxmlformats.org/spreadsheetml/2006/main}si'):
                    t_elem = si.find('.//{http://schemas.openxmlformats.org/spreadsheetml/2006/main}t')
                    if t_elem is not None and t_elem.text:
                        shared_strings.append(t_elem.text)
        
        # Apri foglio Analisi As-IS (sheet2)
        with z.open('xl/worksheets/sheet2.xml') as f:
            tree = ET.parse(f)
            root = tree.getroot()
            ns = {'': 'http://schemas.openxmlformats.org/spreadsheetml/2006/main'}
            
            # Cerca nelle righe 1000+
            for row in root.findall('.//row', ns):
                row_num = int(row.get('r', 0))
                
                if 1000 <= row_num <= 1300:
                    row_data = {}
                    
                    for cell in row.findall('.//c', ns):
                        cell_ref = cell.get('r', '')
                        match = re.match(r'([A-Z]+)(\d+)', cell_ref)
                        
                        if match:
                            col = match.group(1)
                            
                            # Ci interessano colonne F e G
                            if col in ['F', 'G']:
                                v_elem = cell.find('.//v', ns)
                                if v_elem is not None and v_elem.text:
                                    cell_type = cell.get('t', '')
                                    
                                    if cell_type == 's':
                                        idx = int(v_elem.text)
                                        if idx < len(shared_strings):
                                            value = shared_strings[idx]
                                        else:
                                            value = ""
                                    else:
                                        value = v_elem.text
                                    
                                    row_data[col] = value
                    
                    # Se abbiamo sia F che G, è una coppia evento-descrizione
                    if 'F' in row_data and 'G' in row_data:
                        evento = row_data['F'].strip()
                        desc = row_data['G'].strip()
                        if evento and desc:
                            descrizioni[evento] = desc
    
    print(f"✓ Trovate {len(descrizioni)} coppie evento-descrizione per VLOOKUP")
    
    # Mostra statistiche finali
    print("\n\n📈 STATISTICHE FINALI CORRETTE")
    print("-"*80)
    
    for categoria in sorted(mappature.keys()):
        eventi = mappature[categoria]
        print(f"\n{categoria}:")
        print(f"  • Totale eventi: {len(eventi)}")
        
        # Analizza range codici
        codici = []
        for evt in eventi:
            match = re.match(r'^(\d+)', evt)
            if match:
                codici.append(int(match.group(1)))
        
        if codici:
            print(f"  • Range codici: {min(codici)}-{max(codici)}")
            
            # Cerca il codice 99 (varie)
            for evt in eventi:
                if '99 -' in evt:
                    print(f"  • Evento 'varie': {evt[:60]}...")
                    break
    
    # Salva i dati corretti
    dati_corretti = {
        'mappature_categoria_eventi': mappature,
        'descrizioni_vlookup': descrizioni,
        'statistiche': {
            'totale_categorie': len(mappature),
            'totale_eventi': sum(len(e) for e in mappature.values()),
            'totale_descrizioni': len(descrizioni)
        }
    }
    
    with open('mappature_corrette_final.json', 'w', encoding='utf-8') as f:
        json.dump(dati_corretti, f, ensure_ascii=False, indent=2)
    
    print("\n\n✅ SALVATO: mappature_corrette_final.json")
    
    return dati_corretti

if __name__ == "__main__":
    try:
        dati = estrai_mappature_reali()
        
        print("\n" + "="*80)
        print("RIEPILOGO MAPPATURE CORRETTE")
        print("="*80)
        
        # Mostra sintesi per verificare
        print("\nRANGE DI CODICI PER CATEGORIA:")
        print("-"*40)
        
        categorie_ordinate = [
            ("Execution_delivery", "100-199"),
            ("Business_disruption", "200-299"),
            ("Employment_practices", "300-399"),
            ("Damage_Danni", "400-499"),
            ("Clients_product", "500-599"),
            ("Internal_Fraud", "600-699"),
            ("External_fraud", "700-799")
        ]
        
        for cat_short, range_atteso in categorie_ordinate:
            # Trova la categoria completa
            for cat_full in dati['mappature_categoria_eventi'].keys():
                if cat_short in cat_full:
                    eventi = dati['mappature_categoria_eventi'][cat_full]
                    print(f"{cat_short:25} {range_atteso:10} → {len(eventi)} eventi")
                    break
        
        print("\n✅ Ora possiamo aggiornare il server con i dati CORRETTI!")
        
    except Exception as e:
        print(f"\n❌ ERRORE: {e}")
        import traceback
        traceback.print_exc()