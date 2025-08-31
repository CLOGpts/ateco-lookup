#!/usr/bin/env python3
"""
Analisi PRECISA riga per riga delle righe 1000+ del foglio Analisi As-IS
Per capire ESATTAMENTE la struttura
"""

import zipfile
import xml.etree.ElementTree as ET
import re
import json

def analisi_precisa():
    print("="*80)
    print("ANALISI PRECISA RIGHE 1000+ - FOGLIO ANALISI AS-IS")
    print("="*80)
    
    with zipfile.ZipFile('Operational Risk Mapping Globale - Copia.xlsx', 'r') as z:
        # Carica stringhe condivise
        shared_strings = []
        if 'xl/sharedStrings.xml' in z.namelist():
            with z.open('xl/sharedStrings.xml') as f:
                tree = ET.parse(f)
                root = tree.getroot()
                for si in root.findall('.//{http://schemas.openxmlformats.org/spreadsheetml/2006/main}si'):
                    t_elem = si.find('.//{http://schemas.openxmlformats.org/spreadsheetml/2006/main}t')
                    if t_elem is not None and t_elem.text:
                        shared_strings.append(t_elem.text)
        
        print(f"✓ Stringhe condivise: {len(shared_strings)}\n")
        
        # Apri foglio Analisi As-IS (sheet2)
        with z.open('xl/worksheets/sheet2.xml') as f:
            tree = ET.parse(f)
            root = tree.getroot()
            ns = {'': 'http://schemas.openxmlformats.org/spreadsheetml/2006/main'}
            
            # Dizionario per memorizzare TUTTE le celle delle righe 1000+
            righe_dati = {}
            
            for row in root.findall('.//row', ns):
                row_num = int(row.get('r', 0))
                
                # Solo righe 1000-1300
                if 1000 <= row_num <= 1300:
                    righe_dati[row_num] = {}
                    
                    for cell in row.findall('.//c', ns):
                        cell_ref = cell.get('r', '')
                        match = re.match(r'([A-Z]+)(\d+)', cell_ref)
                        
                        if match:
                            col = match.group(1)
                            
                            # Estrai valore
                            v_elem = cell.find('.//v', ns)
                            if v_elem is not None and v_elem.text:
                                cell_type = cell.get('t', '')
                                
                                if cell_type == 's':  # Stringa condivisa
                                    idx = int(v_elem.text)
                                    if idx < len(shared_strings):
                                        value = shared_strings[idx]
                                    else:
                                        value = f"[idx {idx}]"
                                else:
                                    value = v_elem.text
                                
                                righe_dati[row_num][col] = value
    
    # ANALISI DETTAGLIATA
    print("\n📊 STRUTTURA DETTAGLIATA RIGHE 1000-1050")
    print("-"*80)
    print("Riga | Col E (Categoria?)     | Col F (Evento)         | Col G (Descrizione)")
    print("-"*80)
    
    for row in range(1000, 1051):
        if row in righe_dati:
            data = righe_dati[row]
            col_e = data.get('E', '')[:20].ljust(20)
            col_f = data.get('F', '')[:20].ljust(20)
            col_g = data.get('G', '')[:20].ljust(20) if data.get('G') else ''
            
            if any([col_e, col_f, col_g]):
                print(f"{row} | {col_e} | {col_f} | {col_g}")
    
    # TROVA IL PATTERN
    print("\n\n🔍 ANALISI DEL PATTERN")
    print("-"*80)
    
    # Raccogli tutti gli eventi con codici
    eventi_con_codici = []
    for row in righe_dati:
        if 'F' in righe_dati[row]:
            evento = righe_dati[row]['F']
            if evento and re.match(r'^\d{3}\s*-', evento):
                descrizione = righe_dati[row].get('G', '')
                eventi_con_codici.append({
                    'riga': row,
                    'evento': evento,
                    'descrizione': descrizione,
                    'codice': int(evento.split('-')[0].strip())
                })
    
    # Ordina per codice
    eventi_con_codici.sort(key=lambda x: x['codice'])
    
    # Raggruppa per range di codici
    ranges = {
        '100-199': [],
        '200-299': [],
        '300-399': [],
        '400-499': [],
        '500-599': [],
        '600-699': [],
        '700-799': []
    }
    
    for evento in eventi_con_codici:
        codice = evento['codice']
        if 100 <= codice < 200:
            ranges['100-199'].append(evento)
        elif 200 <= codice < 300:
            ranges['200-299'].append(evento)
        elif 300 <= codice < 400:
            ranges['300-399'].append(evento)
        elif 400 <= codice < 500:
            ranges['400-499'].append(evento)
        elif 500 <= codice < 600:
            ranges['500-599'].append(evento)
        elif 600 <= codice < 700:
            ranges['600-699'].append(evento)
        elif 700 <= codice < 800:
            ranges['700-799'].append(evento)
    
    # Mostra statistiche per range
    print("\n📈 EVENTI PER RANGE DI CODICI:")
    for range_key in sorted(ranges.keys()):
        eventi = ranges[range_key]
        if eventi:
            print(f"\n{range_key}: {len(eventi)} eventi")
            print(f"  Primo: {eventi[0]['evento'][:50]}")
            if len(eventi) > 1:
                print(f"  Ultimo: {eventi[-1]['evento'][:50]}")
            
            # Determina categoria probabile
            codice_min = int(range_key.split('-')[0])
            if codice_min == 100:
                cat = "Damage_Danni"
            elif codice_min == 200:
                cat = "Business_disruption"
            elif codice_min == 300:
                cat = "Employment_practices_Dipendenti"
            elif codice_min == 400:
                cat = "Execution_delivery"
            elif codice_min == 500:
                cat = "Clients_product_Clienti"
            elif codice_min == 600:
                cat = "Internal_Fraud_Frodi_interne"
            elif codice_min == 700:
                cat = "External_fraud_Frodi_esterne"
            else:
                cat = "???"
            
            print(f"  → Categoria: {cat}")
    
    # COSTRUISCI MAPPATURE DEFINITIVE
    print("\n\n✅ COSTRUZIONE MAPPATURE DEFINITIVE")
    print("-"*80)
    
    mappature_definitive = {
        "Damage_Danni": [],
        "Business_disruption": [],
        "Employment_practices_Dipendenti": [],
        "Execution_delivery_Problemi_di_produzione_o_consegna": [],
        "Clients_product_Clienti": [],
        "Internal_Fraud_Frodi_interne": [],
        "External_fraud_Frodi_esterne": []
    }
    
    # Mappatura VLOOKUP (F -> G)
    vlookup_map = {}
    
    for evento in eventi_con_codici:
        codice = evento['codice']
        evento_text = evento['evento']
        desc = evento['descrizione']
        
        # Aggiungi alla mappatura VLOOKUP
        if evento_text and desc:
            vlookup_map[evento_text] = desc
        
        # Assegna alla categoria corretta
        if 100 <= codice < 200:
            mappature_definitive["Damage_Danni"].append(evento_text)
        elif 200 <= codice < 300:
            mappature_definitive["Business_disruption"].append(evento_text)
        elif 300 <= codice < 400:
            mappature_definitive["Employment_practices_Dipendenti"].append(evento_text)
        elif 400 <= codice < 500:
            mappature_definitive["Execution_delivery_Problemi_di_produzione_o_consegna"].append(evento_text)
        elif 500 <= codice < 600:
            mappature_definitive["Clients_product_Clienti"].append(evento_text)
        elif 600 <= codice < 700:
            mappature_definitive["Internal_Fraud_Frodi_interne"].append(evento_text)
        elif 700 <= codice < 800:
            mappature_definitive["External_fraud_Frodi_esterne"].append(evento_text)
    
    # Statistiche finali
    print("\nMAPPATURE FINALI:")
    for cat, eventi in mappature_definitive.items():
        if eventi:
            print(f"\n{cat}: {len(eventi)} eventi")
            if eventi:
                # Range codici
                codici = []
                for e in eventi:
                    try:
                        c = int(e.split('-')[0].strip())
                        codici.append(c)
                    except:
                        pass
                if codici:
                    print(f"  Range: {min(codici)}-{max(codici)}")
    
    # Salva tutto
    risultato = {
        'mappature_categoria_eventi': mappature_definitive,
        'vlookup_map': vlookup_map,
        'statistiche': {
            'totale_categorie': 7,
            'totale_eventi': sum(len(e) for e in mappature_definitive.values()),
            'totale_vlookup': len(vlookup_map)
        }
    }
    
    with open('MAPPATURE_EXCEL_PERFETTE.json', 'w', encoding='utf-8') as f:
        json.dump(risultato, f, ensure_ascii=False, indent=2)
    
    print(f"\n✅ SALVATO: MAPPATURE_EXCEL_PERFETTE.json")
    print(f"   Eventi totali: {risultato['statistiche']['totale_eventi']}")
    print(f"   VLOOKUP mappings: {risultato['statistiche']['totale_vlookup']}")
    
    return risultato

if __name__ == "__main__":
    analisi_precisa()