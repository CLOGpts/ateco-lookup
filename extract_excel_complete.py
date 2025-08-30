#!/usr/bin/env python3
"""
ESTRATTORE COMPLETO EXCEL - Sistema avanzato
Estrae tutti i dati dal file Excel per il sistema di Risk Assessment
"""

import json
import zipfile
import xml.etree.ElementTree as ET
import re
import os
from typing import Dict, List, Any

class ExcelExtractor:
    def __init__(self, excel_file_path: str):
        """Inizializza l'estrattore Excel"""
        self.excel_file = excel_file_path
        self.workbook = None
        self.worksheets = {}
        self.shared_strings = []
        
        # Namespace per XML Excel
        self.ns = {
            'main': 'http://schemas.openxmlformats.org/spreadsheetml/2006/main',
            'r': 'http://schemas.openxmlformats.org/officeDocument/2006/relationships'
        }
    
    def extract_all_data(self) -> Dict[str, Any]:
        """Estrae tutti i dati dall'Excel"""
        try:
            print(f"🔄 Apertura file Excel: {self.excel_file}")
            
            with zipfile.ZipFile(self.excel_file, 'r') as zip_file:
                # Lista tutti i file nell'archivio
                print("\n📁 Contenuto dell'archivio Excel:")
                for file_info in zip_file.filelist:
                    print(f"  • {file_info.filename}")
                
                # Estrai shared strings
                self._extract_shared_strings(zip_file)
                
                # Estrai informazioni sui worksheets
                self._extract_worksheets_info(zip_file)
                
                # Estrai i dati dai worksheets
                all_data = self._extract_all_worksheets_data(zip_file)
                
                return all_data
                
        except Exception as e:
            print(f"❌ Errore nell'estrazione: {e}")
            return {}
    
    def _extract_shared_strings(self, zip_file: zipfile.ZipFile):
        """Estrae le stringhe condivise"""
        try:
            with zip_file.open('xl/sharedStrings.xml') as f:
                tree = ET.parse(f)
                root = tree.getroot()
                
                self.shared_strings = []
                for si in root.findall('main:si', self.ns):
                    text_elem = si.find('main:t', self.ns)
                    if text_elem is not None:
                        self.shared_strings.append(text_elem.text or "")
                    else:
                        # Può contenere formattazione ricca
                        texts = []
                        for r in si.findall('.//main:t', self.ns):
                            if r.text:
                                texts.append(r.text)
                        self.shared_strings.append(''.join(texts))
                
                print(f"✅ Estratte {len(self.shared_strings)} stringhe condivise")
                
        except Exception as e:
            print(f"⚠️ Errore estrazione shared strings: {e}")
            self.shared_strings = []
    
    def _extract_worksheets_info(self, zip_file: zipfile.ZipFile):
        """Estrae informazioni sui worksheets"""
        try:
            # Prima ottieni la lista dei file worksheet effettivamente disponibili
            available_sheets = []
            for filename in zip_file.namelist():
                if filename.startswith('xl/worksheets/sheet') and filename.endswith('.xml'):
                    available_sheets.append(filename)
            available_sheets.sort()
            
            print(f"📁 File worksheet disponibili: {available_sheets}")
            
            with zip_file.open('xl/workbook.xml') as f:
                tree = ET.parse(f)
                root = tree.getroot()
                
                sheets = root.find('main:sheets', self.ns)
                if sheets is not None:
                    sheet_index = 0
                    for sheet in sheets.findall('main:sheet', self.ns):
                        sheet_id = sheet.get('sheetId')
                        sheet_name = sheet.get('name')
                        rel_id = sheet.get('{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id')
                        
                        # Usa il file disponibile in sequenza
                        if sheet_index < len(available_sheets):
                            filename = available_sheets[sheet_index]
                        else:
                            filename = f'xl/worksheets/sheet{sheet_index + 1}.xml'
                        
                        self.worksheets[sheet_name] = {
                            'id': sheet_id,
                            'name': sheet_name,
                            'rel_id': rel_id,
                            'filename': filename
                        }
                        
                        sheet_index += 1
                
                print(f"✅ Trovati {len(self.worksheets)} worksheets:")
                for name, info in self.worksheets.items():
                    print(f"  • {name} → {info['filename']}")
                    
        except Exception as e:
            print(f"❌ Errore estrazione worksheets info: {e}")
    
    def _extract_all_worksheets_data(self, zip_file: zipfile.ZipFile) -> Dict[str, Any]:
        """Estrae i dati da tutti i worksheets"""
        all_data = {
            'worksheets': {},
            'events_lookup': {},
            'categories_mapping': {},
            'summary': {
                'total_sheets': len(self.worksheets),
                'sheet_names': list(self.worksheets.keys())
            }
        }
        
        for sheet_name, sheet_info in self.worksheets.items():
            print(f"\n🔍 Elaborazione foglio: {sheet_name}")
            
            try:
                sheet_data = self._extract_worksheet_data(zip_file, sheet_info)
                all_data['worksheets'][sheet_name] = sheet_data
                
                # Se è un foglio con eventi/lookup, estraili
                if 'event' in sheet_name.lower() or 'lookup' in sheet_name.lower():
                    lookup_data = self._extract_events_from_sheet(sheet_data)
                    all_data['events_lookup'].update(lookup_data)
                
                # Se contiene mappature di categorie
                if 'categor' in sheet_name.lower() or 'mapping' in sheet_name.lower():
                    cat_data = self._extract_categories_from_sheet(sheet_data)
                    all_data['categories_mapping'].update(cat_data)
                
            except Exception as e:
                print(f"❌ Errore elaborazione {sheet_name}: {e}")
                all_data['worksheets'][sheet_name] = {'error': str(e)}
        
        # Statistiche finali
        total_events = len(all_data['events_lookup'])
        total_categories = len(all_data['categories_mapping'])
        
        all_data['summary'].update({
            'total_events': total_events,
            'total_categories': total_categories
        })
        
        print(f"\n📊 RIEPILOGO ESTRAZIONE:")
        print(f"✅ Fogli elaborati: {len(all_data['worksheets'])}")
        print(f"✅ Eventi estratti: {total_events}")
        print(f"✅ Categorie estratte: {total_categories}")
        
        return all_data
    
    def _extract_worksheet_data(self, zip_file: zipfile.ZipFile, sheet_info: Dict) -> Dict[str, Any]:
        """Estrae i dati da un singolo worksheet"""
        try:
            with zip_file.open(sheet_info['filename']) as f:
                tree = ET.parse(f)
                root = tree.getroot()
                
                # Trova le dimensioni del foglio
                dimension = root.find('main:dimension', self.ns)
                ref = dimension.get('ref') if dimension is not None else "A1:Z100"
                
                # Estrai tutte le celle
                cells_data = {}
                rows_data = []
                
                sheet_data = root.find('main:sheetData', self.ns)
                if sheet_data is not None:
                    for row in sheet_data.findall('main:row', self.ns):
                        row_num = int(row.get('r', 0))
                        row_cells = {}
                        
                        for cell in row.findall('main:c', self.ns):
                            cell_ref = cell.get('r', '')
                            cell_type = cell.get('t', '')
                            
                            # Estrai valore della cella
                            value_elem = cell.find('main:v', self.ns)
                            if value_elem is not None:
                                cell_value = value_elem.text
                                
                                # Se è una stringa condivisa
                                if cell_type == 's' and cell_value:
                                    try:
                                        string_index = int(cell_value)
                                        if 0 <= string_index < len(self.shared_strings):
                                            cell_value = self.shared_strings[string_index]
                                    except (ValueError, IndexError):
                                        pass
                                
                                row_cells[cell_ref] = cell_value
                                cells_data[cell_ref] = cell_value
                        
                        if row_cells:
                            rows_data.append({
                                'row': row_num,
                                'cells': row_cells
                            })
                
                return {
                    'name': sheet_info['name'],
                    'dimension': ref,
                    'total_rows': len(rows_data),
                    'total_cells': len(cells_data),
                    'rows': rows_data[:50],  # Limita a prime 50 righe per performance
                    'all_cells': cells_data
                }
                
        except Exception as e:
            print(f"❌ Errore lettura worksheet {sheet_info['name']}: {e}")
            return {'error': str(e)}
    
    def _extract_events_from_sheet(self, sheet_data: Dict) -> Dict[str, str]:
        """Estrae eventi e descrizioni da un foglio"""
        events = {}
        
        if 'all_cells' not in sheet_data:
            return events
        
        cells = sheet_data['all_cells']
        
        # Cerca pattern di eventi (codice - descrizione)
        for cell_ref, value in cells.items():
            if isinstance(value, str) and value:
                # Pattern per codici evento: 3 cifre seguiti da spazio e trattino
                if re.match(r'^\d{3}\s*-', value):
                    # Estrai codice e descrizione
                    parts = value.split('-', 1)
                    if len(parts) >= 2:
                        code = parts[0].strip()
                        description = parts[1].strip()
                        events[code] = description
                        events[value] = description  # Anche chiave completa
                        
                        # Aggiungi anche versioni formattate
                        formatted_key = f"{code} - {description}"
                        events[formatted_key] = description
        
        # Se il foglio è "work", estrai anche le categorie strutturate
        if sheet_data.get('name', '').lower() == 'work':
            print(f"🎯 Elaborazione speciale per foglio WORK")
            
            # Cerca pattern di categorie con underscore
            for cell_ref, value in cells.items():
                if isinstance(value, str) and '_' in value:
                    # Potrebbe essere un nome di categoria
                    if any(cat in value.lower() for cat in ['fraud', 'employment', 'client', 'damage', 'business', 'execution']):
                        events[f"CATEGORY_{value}"] = value
        
        return events
    
    def _extract_categories_from_sheet(self, sheet_data: Dict) -> Dict[str, Any]:
        """Estrae categorie e mappature da un foglio"""
        categories = {}
        
        if 'all_cells' not in sheet_data:
            return categories
        
        cells = sheet_data['all_cells']
        
        # Cerca nomi di categorie tipiche
        category_patterns = [
            r'internal.*fraud|frodi.*intern',
            r'external.*fraud|frodi.*estern',
            r'employment|dipendenti',
            r'client|customer|clienti',
            r'damage|danni',
            r'business.*disruption',
            r'execution|delivery|produzione|consegna'
        ]
        
        for cell_ref, value in cells.items():
            if isinstance(value, str) and value:
                for pattern in category_patterns:
                    if re.search(pattern, value, re.IGNORECASE):
                        # Normalizza il nome della categoria
                        normalized = re.sub(r'[^a-zA-Z_]', '_', value).strip('_')
                        categories[normalized] = {
                            'original_name': value,
                            'cell_reference': cell_ref,
                            'sheet': sheet_data.get('name', 'Unknown')
                        }
                        break
        
        return categories


def main():
    """Funzione principale per l'estrazione"""
    excel_file = "Operational Risk Mapping Globale - Copia.xlsx"
    
    if not os.path.exists(excel_file):
        print(f"❌ File non trovato: {excel_file}")
        return
    
    print("🚀 AVVIO ESTRAZIONE COMPLETA EXCEL")
    print("="*60)
    
    extractor = ExcelExtractor(excel_file)
    all_data = extractor.extract_all_data()
    
    if all_data:
        # Salva i dati estratti
        output_file = "excel_data_complete.json"
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(all_data, f, ensure_ascii=False, indent=2)
        
        print(f"\n✅ Dati salvati in: {output_file}")
        print(f"📊 Dimensione file: {os.path.getsize(output_file)} bytes")
        
        # Crea anche un file di lookup separato
        lookup_file = "excel_lookups_complete.json"
        lookup_data = {
            "events_lookup": all_data.get('events_lookup', {}),
            "categories_mapping": all_data.get('categories_mapping', {}),
            "data": all_data.get('events_lookup', {})  # Per compatibilità con excel_system_final.py
        }
        
        with open(lookup_file, 'w', encoding='utf-8') as f:
            json.dump(lookup_data, f, ensure_ascii=False, indent=2)
        
        print(f"✅ Lookup salvati in: {lookup_file}")
        
    else:
        print("❌ Nessun dato estratto!")


if __name__ == "__main__":
    main()