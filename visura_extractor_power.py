# 🚀 BACKEND POWER UPGRADE - Estrazione Visure Camerali
# Questo codice va integrato nel backend Python su Render

import re
import pdfplumber
from typing import Dict, List, Any, Optional
import json

class VisuraExtractorPower:
    """Estrattore potente per visure camerali - estrae TUTTO!"""
    
    def __init__(self):
        # Pattern regex ottimizzati per ogni campo
        self.patterns = {
            # DATI CRITICI - PRIORITÀ MASSIMA
            'denominazione': [
                r'(?:DENOMINAZIONE|Denominazione|RAGIONE SOCIALE)[\s:]*([^\n]+)',
                r'(?:Impresa|IMPRESA)[\s:]*([^\n]+)',
                r'(?:Societa\'|SOCIETA\'|Società|SOCIETÀ)[\s:]*([^\n]+)',
                r'^\s*([A-Z][A-Z\s&\.\-\']+(?:S\.?R\.?L\.?|S\.?P\.?A\.?|S\.?N\.?C\.?|S\.?A\.?S\.?))\s*$',
            ],
            
            'partita_iva': [
                r'(?:P\.?\s?IVA|Partita IVA|PARTITA IVA)[\s:]*(\d{11})',
                r'(?:Codice fiscale e numero iscrizione|C\.F\.)[\s:]*(\d{11})',
                r'(?:VAT|Vat Number)[\s:]*(?:IT)?(\d{11})',
                r'\b(\d{11})\b(?=.*(?:IVA|iva|P\.IVA))',
            ],
            
            'codice_fiscale': [
                r'(?:C\.?F\.?|Codice Fiscale|CODICE FISCALE)[\s:]*([A-Z0-9]{11,16})',
                r'(?:Cod\.\s?Fisc\.)[\s:]*([A-Z0-9]{11,16})',
                r'(?:codice fiscale)[\s:]*([A-Z0-9]{11,16})',
            ],
            
            'pec': [
                r'(?:PEC|Pec|pec|Posta Elettronica Certificata)[\s:]*([a-zA-Z0-9][a-zA-Z0-9\.\-\_]+@[a-zA-Z0-9][a-zA-Z0-9\.\-]+\.[a-zA-Z]{2,})',
                r'(?:Indirizzo PEC|INDIRIZZO PEC)[\s:]*([a-zA-Z0-9\.\-\_]+@[a-zA-Z0-9\.\-]+\.[a-zA-Z]{2,})',
                r'([a-zA-Z0-9\.\-\_]+@pec\.[a-zA-Z0-9\.\-]+\.[a-zA-Z]{2,})',
                r'(?:E-mail certificata)[\s:]*([a-zA-Z0-9\.\-\_]+@[a-zA-Z0-9\.\-]+\.[a-zA-Z]{2,})',
            ],
            
            # DATI REGISTRO IMPRESE
            'numero_rea': [
                r'(?:REA|R\.E\.A\.|Numero REA)[\s:]*([A-Z]{2}[\s\-]?\d{5,7})',
                r'(?:Numero iscrizione al Registro Imprese)[\s:]*([A-Z]{2}[\s\-]?\d{5,7})',
                r'(?:CCIAA)[\s:]*[^\n]*?([A-Z]{2}[\s\-]?\d{5,7})',
                r'(?:n\.|numero|nr\.?)\s*([A-Z]{2}[\s\-]?\d{5,7})',
                r'REA\s+([A-Z]{2})\s*[\-]?\s*(\d{5,7})',  # REA TO-1234567
            ],
            
            'camera_commercio': [
                r'(?:CCIAA di|Camera di Commercio di|C\.C\.I\.A\.A\. di)[\s:]*([A-Z][A-Za-z\s]+?)(?:\n|$|REA)',
                r'(?:Registro Imprese di)[\s:]*([A-Z][A-Za-z\s]+?)(?:\n|$)',
                r'(?:Ufficio di)[\s:]*([A-Z][A-Za-z\s]+?)(?:\n|$)',
            ],
            
            'forma_giuridica': [
                r'(?:Forma giuridica|FORMA GIURIDICA)[\s:]*([^\n]+)',
                r'(?:Tipo società|Natura giuridica)[\s:]*([^\n]+)',
                r'\b(S\.?R\.?L\.?(?:\s+unipersonale)?|S\.?P\.?A\.?|S\.?N\.?C\.?|S\.?A\.?S\.?|S\.?S\.?|SOCIETA\'\s+A\s+RESPONSABILITA\'\s+LIMITATA)\b',
            ],
            
            # CAPITALE SOCIALE
            'capitale_sociale': [
                r'(?:Capitale sociale|CAPITALE SOCIALE)[\s:]*(?:Euro|EUR|€)?\s*([\d\.,]+)',
                r'(?:Capitale deliberato)[\s:]*(?:Euro|EUR|€)?\s*([\d\.,]+)',
                r'(?:Capitale versato)[\s:]*(?:Euro|EUR|€)?\s*([\d\.,]+)',
                r'(?:i\.v\.|interamente versato)[\s:]*(?:Euro|EUR|€)?\s*([\d\.,]+)',
            ],
            
            # ATTIVITÀ
            'ateco_codes': [
                r'(?:Codice ATECO|ATECO|Attività prevalente|Codice attività)[\s:]*(\d{2}[\.\d]*)',
                r'(?:Codice:|Attività:)[\s:]*(\d{2}[\.\d]*)',
                r'(?:Import.:\s*)(\d{2}[\.\d]*)',
                r'\b(\d{2}\.\d{2}(?:\.\d{2})?)\b',
            ],
            
            # SEDE
            'indirizzo': [
                r'(?:Sede legale|SEDE LEGALE|Indirizzo sede)[\s:]*([^\n]+)',
                r'(?:Via|VIA|Viale|Piazza|Corso|Largo)[\s:]*([^\n]+?)(?:\d{5}|\n|$)',
                r'(?:Indirizzo)[\s:]*([^\n]+)',
            ],
            
            'cap': [
                r'(?:CAP|C\.A\.P\.)[\s:]*(\d{5})',
                r'\b(\d{5})\b(?=\s*[A-Z][a-z]+(?:\s+\([A-Z]{2}\))?)',
                r'(?:Sede.*?)\b(\d{5})\b',
            ],
            
            'comune': [
                r'(?:Comune|COMUNE)[\s:]*([A-Z][A-Za-z\s]+?)(?:\([A-Z]{2}\)|\n|$)',
                r'\d{5}\s+([A-Z][A-Za-z\s]+?)(?:\s+\([A-Z]{2}\)|\n|$)',
                r'(?:Località|Città)[\s:]*([A-Z][A-Za-z\s]+)',
            ],
            
            'provincia': [
                r'(?:Provincia|PROVINCIA|Prov\.)[\s:]*\(?([A-Z]{2})\)?',
                r'(?:[A-Z][a-z]+)\s+\(([A-Z]{2})\)',
                r'\b\(([A-Z]{2})\)\b',
            ],
            
            # CONTATTI
            'email': [
                r'(?:E-mail|Email|Mail)[\s:]*([a-zA-Z0-9\.\-\_]+@[a-zA-Z0-9\.\-]+\.[a-zA-Z]{2,})',
                r'(?:Posta elettronica)[\s:]*([a-zA-Z0-9\.\-\_]+@[a-zA-Z0-9\.\-]+\.[a-zA-Z]{2,})',
                r'\b([a-zA-Z0-9\.\-\_]+@[a-zA-Z0-9\.\-]+\.[a-zA-Z]{2,})\b(?!.*pec)',
            ],
            
            'telefono': [
                r'(?:Tel\.|Telefono|TEL|Phone)[\s:]*([+\d\s\-\(\)]+)',
                r'(?:Numero di telefono)[\s:]*([+\d\s\-\(\)]+)',
                r'(?:Recapito telefonico)[\s:]*([+\d\s\-\(\)]+)',
            ],
            
            'sito_web': [
                r'(?:Sito web|Sito internet|Web|Website)[\s:]*((?:www\.|http)[^\s\n]+)',
                r'(?:URL)[\s:]*((?:www\.|http)[^\s\n]+)',
                r'\b(www\.[a-zA-Z0-9\-]+\.[a-zA-Z]{2,}(?:\.[a-zA-Z]{2,})?)\b',
            ],
            
            # DATE
            'data_costituzione': [
                r'(?:Data costituzione|DATA COSTITUZIONE)[\s:]*(\d{2}[\/\-]\d{2}[\/\-]\d{4})',
                r'(?:Costituita il|Data atto di costituzione)[\s:]*(\d{2}[\/\-]\d{2}[\/\-]\d{4})',
                r'(?:Data di costituzione)[\s:]*(\d{2}[\/\-]\d{2}[\/\-]\d{4})',
            ],
            
            'data_iscrizione': [
                r'(?:Data iscrizione|DATA ISCRIZIONE)[\s:]*(\d{2}[\/\-]\d{2}[\/\-]\d{4})',
                r'(?:Iscritta dal)[\s:]*(\d{2}[\/\-]\d{2}[\/\-]\d{4})',
                r'(?:Data di iscrizione al R\.I\.)[\s:]*(\d{2}[\/\-]\d{2}[\/\-]\d{4})',
            ],
            
            # STATO
            'stato_attivita': [
                r'(?:Stato attività|STATO ATTIVITA\'|Status)[\s:]*(ATTIVA|INATTIVA|CESSATA|IN LIQUIDAZIONE|SOSPESA)',
                r'(?:Situazione impresa)[\s:]*(attiva|inattiva|cessata|in liquidazione)',
                r'(?:impresa\s+)(attiva|inattiva|cessata)',
            ],
        }
        
        # Mappatura codici ATECO alle descrizioni COMPLETE
        self.ateco_descriptions = {
            '62.01': 'Produzione di software non connesso all\'edizione',
            '62.02': 'Consulenza nel settore delle tecnologie dell\'informatica',
            '62.03': 'Gestione di strutture e apparecchiature informatiche hardware e software',
            '62.09': 'Altre attività dei servizi connessi alle tecnologie dell\'informatica e all\'informatica',
            '63.11': 'Elaborazione dei dati, hosting e attività connesse',
            '63.12': 'Portali web',
            '70.22': 'Consulenza imprenditoriale e altra consulenza amministrativo-gestionale',
            # Aggiungi altri codici ATECO secondo necessità
        }
    
    def clean_text(self, text: str) -> str:
        """Pulisce il testo estratto"""
        if not text:
            return ''
        # Rimuovi spazi multipli e caratteri strani
        text = re.sub(r'\s+', ' ', text)
        text = text.strip()
        return text
    
    def clean_rea(self, rea: str) -> str:
        """Pulisce il numero REA estratto"""
        if not rea:
            return ''
        
        # Rimuovi caratteri strani all'inizio
        rea = re.sub(r'^[^A-Z0-9]+', '', rea)
        
        # Pattern per REA valido: XX-NNNNNNN o XX NNNNNNN
        match = re.search(r'([A-Z]{2})[\s\-]?(\d{5,7})', rea)
        if match:
            provincia = match.group(1)
            numero = match.group(2)
            return f"{provincia}-{numero}"
        
        return rea
    
    def clean_provincia(self, provincia: str) -> str:
        """Assicura che la provincia sia sempre 2 lettere maiuscole"""
        if not provincia:
            return ''
        
        # Estrai solo lettere maiuscole
        provincia = re.sub(r'[^A-Z]', '', provincia.upper())
        
        # Deve essere esattamente 2 lettere
        if len(provincia) == 2:
            return provincia
        
        return ''
    
    def extract_with_patterns(self, text: str, patterns: List[str]) -> Optional[str]:
        """Estrae usando multipli pattern regex"""
        for pattern in patterns:
            matches = re.findall(pattern, text, re.IGNORECASE | re.MULTILINE)
            if matches:
                # Prendi il primo match valido
                result = matches[0] if isinstance(matches[0], str) else matches[0][0]
                result = self.clean_text(result)
                if result and result != 'N/D':
                    return result
        return None
    
    def parse_capitale(self, text: str) -> float:
        """Converte stringa capitale in float"""
        if not text:
            return 0.0
        # Rimuovi separatori migliaia e sostituisci virgola con punto
        text = text.replace('.', '').replace(',', '.')
        # Estrai solo numeri
        numbers = re.findall(r'[\d\.]+', text)
        if numbers:
            try:
                return float(numbers[0])
            except:
                return 0.0
        return 0.0
    
    def is_valid_ateco(self, code: str) -> bool:
        """Verifica se è un codice ATECO valido"""
        # Formato: XX.XX o XX.XX.XX dove XX sono numeri
        if not re.match(r'^\d{2}(\.\d{2}){1,2}$', code):
            return False
        
        # Il primo numero deve essere tra 01 e 99
        first_two = int(code[:2])
        if first_two < 1 or first_two > 99:
            return False
        
        # Esclude anni travestiti da codici (es: 20.21, 20.22)
        parts = code.split('.')
        if len(parts) >= 2:
            # Se sembra un anno (19xx, 20xx, 21xx)
            if first_two in [19, 20, 21] and len(parts[1]) == 2:
                second_num = int(parts[1])
                # Se il secondo numero è 00-30 potrebbe essere un anno
                if 0 <= second_num <= 30:
                    return False
        
        return True
    
    def clean_ateco_description(self, description: str) -> str:
        """Pulisce la descrizione ATECO"""
        if not description:
            return ''
            
        # Rimuovi testi inutili
        remove_patterns = [
            r'^\d+\s*$',  # Solo numeri
            r'^[A-Z]{2,}\s+DEL\s+.*',  # BIS DEL DECRETO...
            r'^\d{4}.*',  # Anni all'inizio
            r'Addetti.*$',  # Info addetti
            r'\d{2}/\d{2}/\d{4}',  # Date
            r'^[\*\-\•]+',  # Bullet points
            r'[\*\-\•]+$',  # Bullet points finali
        ]
        
        for pattern in remove_patterns:
            description = re.sub(pattern, '', description, flags=re.IGNORECASE)
        
        # Capitalizza prima lettera
        description = description.strip()
        if description and description[0].islower():
            description = description[0].upper() + description[1:]
            
        return description
    
    def extract_ateco_with_description(self, text: str) -> List[Dict[str, Any]]:
        """Estrae SOLO codici ATECO validi con descrizioni"""
        ateco_list = []
        
        # Pattern MIGLIORATI per ATECO - più specifici
        patterns = [
            # Formato con parola chiave ATECO/Codice
            r'(?:ATECO|Ateco|Codice ATECO|Codice attività|Attività prevalente)\s*[:]\s*(\d{2}\.\d{2}(?:\.\d{2})?)\s*[\-]?\s*([^\n]*)',
            # Formato standard con trattino: 62.01 - Descrizione
            r'(?:^|\s)(\d{2}\.\d{2}(?:\.\d{2})?)\s*[\-]\s*([a-zA-Z][^\n]+)',
            # Import/Export codici
            r'(?:Import\.|Export\.)\s*[:]\s*(\d{2}\.\d{2}(?:\.\d{2})?)\s*[\-]?\s*([^\n]*)',
        ]
        
        for pattern in patterns:
            matches = re.findall(pattern, text, re.IGNORECASE | re.MULTILINE)
            for match in matches:
                code = match[0].strip()
                description = match[1].strip() if len(match) > 1 else ''
                
                # VALIDAZIONE: Verifica che sia un codice ATECO valido
                if self.is_valid_ateco(code):
                    # Pulisci la descrizione
                    description = self.clean_ateco_description(description)
                    
                    # Se non c'è descrizione valida, usa il dizionario
                    if not description or len(description) < 5:
                        description = self.ateco_descriptions.get(code, 'Attività economica')
                    
                    # Assicurati che la descrizione sia completa e non troncata
                    if len(description) > 200:
                        # Se troppo lunga, tronca ma aggiungi i puntini
                        description = description[:197] + '...'
                    
                    # Aggiungi solo se non già presente
                    if code not in [a['codice'] for a in ateco_list]:
                        ateco_list.append({
                            'codice': code,
                            'descrizione': description,
                            'principale': len(ateco_list) == 0
                        })
        
        # Se non troviamo nulla con i pattern specifici, cerca con pattern più generici
        if not ateco_list:
            # Pattern generico per codici ATECO isolati
            generic_pattern = r'\b(\d{2}\.\d{2}(?:\.\d{2})?)\b'
            matches = re.findall(generic_pattern, text)
            for code in matches:
                if self.is_valid_ateco(code):
                    # Cerca descrizione nelle vicinanze
                    desc_pattern = rf'{re.escape(code)}\s*[\-:]\s*([^\n]+)'
                    desc_match = re.search(desc_pattern, text, re.IGNORECASE)
                    description = ''
                    if desc_match:
                        description = self.clean_ateco_description(desc_match.group(1))
                    
                    if not description:
                        description = self.ateco_descriptions.get(code, 'Attività economica')
                    
                    if code not in [a['codice'] for a in ateco_list]:
                        ateco_list.append({
                            'codice': code,
                            'descrizione': description,
                            'principale': len(ateco_list) == 0
                        })
                        break  # Prendi solo il primo valido se usiamo il pattern generico
        
        return ateco_list
    
    def extract_amministratori(self, text: str) -> List[Dict[str, str]]:
        """Estrae amministratori e cariche"""
        amministratori = []
        
        # Pattern per trovare amministratori
        patterns = [
            r'(?:Amministratore\s+Unico|AMMINISTRATORE UNICO)[\s:]*([A-Z][A-Za-z\s]+)',
            r'(?:Presidente CdA|Presidente del consiglio)[\s:]*([A-Z][A-Za-z\s]+)',
            r'(?:Amministratore Delegato|AD)[\s:]*([A-Z][A-Za-z\s]+)',
            r'(?:Consigliere)[\s:]*([A-Z][A-Za-z\s]+)',
            r'(?:Socio Amministratore)[\s:]*([A-Z][A-Za-z\s]+)',
        ]
        
        for pattern in patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            for match in matches:
                nome_completo = self.clean_text(match)
                if nome_completo and len(nome_completo) > 3:
                    # Estrai carica dal pattern
                    carica = pattern.split('(?:')[1].split('|')[0]
                    amministratori.append({
                        'nome_completo': nome_completo,
                        'carica': carica,
                    })
        
        return amministratori
    
    def extract_all_data(self, pdf_path: str) -> Dict[str, Any]:
        """Estrae TUTTI i dati dalla visura"""
        
        extracted_data = {
            # Inizializza con valori vuoti
            'denominazione': None,
            'partita_iva': None,
            'codice_fiscale': None,
            'pec': None,
            'forma_giuridica': None,
            'numero_rea': None,
            'camera_commercio': None,
            'capitale_sociale': {
                'versato': 0,
                'deliberato': 0,
                'valuta': 'EUR'
            },
            'codici_ateco': [],
            'sede_legale': {},
            'amministratori': [],
            'confidence': 0.0
        }
        
        # Estrai testo da tutte le pagine
        full_text = ""
        with pdfplumber.open(pdf_path) as pdf:
            for page in pdf.pages:
                page_text = page.extract_text()
                if page_text:
                    full_text += page_text + "\n"
        
        if not full_text:
            return extracted_data
        
        # ESTRAZIONE DATI CRITICI
        extracted_data['denominazione'] = self.extract_with_patterns(full_text, self.patterns['denominazione'])
        extracted_data['partita_iva'] = self.extract_with_patterns(full_text, self.patterns['partita_iva'])
        extracted_data['codice_fiscale'] = self.extract_with_patterns(full_text, self.patterns['codice_fiscale']) or extracted_data['partita_iva']
        extracted_data['pec'] = self.extract_with_patterns(full_text, self.patterns['pec'])
        
        # DATI REGISTRO IMPRESE
        rea_raw = self.extract_with_patterns(full_text, self.patterns['numero_rea'])
        extracted_data['numero_rea'] = self.clean_rea(rea_raw) if rea_raw else None
        extracted_data['camera_commercio'] = self.extract_with_patterns(full_text, self.patterns['camera_commercio'])
        extracted_data['forma_giuridica'] = self.extract_with_patterns(full_text, self.patterns['forma_giuridica'])
        
        # CAPITALE SOCIALE
        capitale_str = self.extract_with_patterns(full_text, self.patterns['capitale_sociale'])
        if capitale_str:
            capitale_value = self.parse_capitale(capitale_str)
            extracted_data['capitale_sociale'] = {
                'versato': capitale_value,
                'deliberato': capitale_value,
                'valuta': 'EUR'
            }
        
        # ATTIVITÀ - con descrizioni!
        extracted_data['codici_ateco'] = self.extract_ateco_with_description(full_text)
        extracted_data['ateco_details'] = extracted_data['codici_ateco']  # Compatibilità
        
        # OGGETTO SOCIALE
        oggetto_pattern = r'(?:Oggetto sociale|OGGETTO SOCIALE|Oggetto)[\s:]*([^\n]{50,})'
        oggetto_matches = re.findall(oggetto_pattern, full_text, re.IGNORECASE | re.DOTALL)
        if oggetto_matches:
            extracted_data['oggetto_sociale'] = self.clean_text(oggetto_matches[0])[:500]
        
        # SEDE LEGALE
        provincia_raw = self.extract_with_patterns(full_text, self.patterns['provincia'])
        extracted_data['sede_legale'] = {
            'indirizzo': self.extract_with_patterns(full_text, self.patterns['indirizzo']) or '',
            'cap': self.extract_with_patterns(full_text, self.patterns['cap']) or '',
            'comune': self.extract_with_patterns(full_text, self.patterns['comune']) or '',
            'provincia': self.clean_provincia(provincia_raw) if provincia_raw else '',
            'nazione': 'ITALIA'
        }
        
        # Struttura alternativa per compatibilità
        extracted_data['sedi'] = {
            'sede_legale': {
                'indirizzo': extracted_data['sede_legale']['indirizzo'],
                'cap': extracted_data['sede_legale']['cap'],
                'citta': extracted_data['sede_legale']['comune'],
                'provincia': extracted_data['sede_legale']['provincia']
            }
        }
        
        # CONTATTI
        extracted_data['email'] = self.extract_with_patterns(full_text, self.patterns['email'])
        extracted_data['telefono'] = self.extract_with_patterns(full_text, self.patterns['telefono'])
        extracted_data['sito_web'] = self.extract_with_patterns(full_text, self.patterns['sito_web'])
        
        # DATE
        extracted_data['data_costituzione'] = self.extract_with_patterns(full_text, self.patterns['data_costituzione'])
        extracted_data['data_iscrizione'] = self.extract_with_patterns(full_text, self.patterns['data_iscrizione'])
        
        # STATO
        stato = self.extract_with_patterns(full_text, self.patterns['stato_attivita'])
        extracted_data['stato_attivita'] = stato.upper() if stato else 'ATTIVA'
        
        # AMMINISTRATORI
        extracted_data['amministratori'] = self.extract_amministratori(full_text)
        
        # TIPO BUSINESS (inferito)
        if any(word in full_text.lower() for word in ['consumatori', 'retail', 'b2c', 'privati']):
            extracted_data['tipo_business'] = 'B2C'
        elif any(word in full_text.lower() for word in ['pubblica amministrazione', 'enti pubblici', 'b2g']):
            extracted_data['tipo_business'] = 'B2G'
        else:
            extracted_data['tipo_business'] = 'B2B'
        
        # CALCOLA CONFIDENCE
        fields_found = sum([
            1 if extracted_data.get('denominazione') else 0,
            1 if extracted_data.get('partita_iva') else 0,
            1 if extracted_data.get('pec') else 0,
            1 if extracted_data.get('numero_rea') else 0,
            1 if extracted_data.get('codici_ateco') else 0,
            1 if extracted_data.get('capitale_sociale', {}).get('versato', 0) > 0 else 0,
            1 if extracted_data.get('sede_legale', {}).get('comune') else 0,
        ])
        
        extracted_data['confidence'] = min(0.95, fields_found / 7)
        
        # Log risultati
        print(f"✅ Estratti {fields_found}/7 campi critici")
        print(f"📊 Denominazione: {extracted_data.get('denominazione', 'NON TROVATA')}")
        print(f"📊 P.IVA: {extracted_data.get('partita_iva', 'NON TROVATA')}")
        print(f"📊 PEC: {extracted_data.get('pec', 'NON TROVATA')}")
        
        return extracted_data


# ESEMPIO DI UTILIZZO NEL TUO BACKEND
def process_visura(file_path: str) -> Dict[str, Any]:
    """Funzione principale da chiamare dal tuo endpoint FastAPI"""
    
    extractor = VisuraExtractorPower()
    
    try:
        # Estrai tutti i dati
        data = extractor.extract_all_data(file_path)
        
        # Aggiungi metadati
        data['extraction_method'] = 'regex_power'
        data['pages_processed'] = 25  # O conta le pagine reali
        
        return {
            'success': True,
            'data': data,
            'extraction_method': 'pdfplumber_regex',
            'processing_time_ms': 1000  # Calcola il tempo reale
        }
        
    except Exception as e:
        print(f"❌ Errore estrazione: {str(e)}")
        return {
            'success': False,
            'error': str(e),
            'data': {}
        }


# TEST LOCALE
if __name__ == "__main__":
    # Test con una visura di esempio
    result = process_visura("visura_esempio.pdf")
    print(json.dumps(result, indent=2, ensure_ascii=False))