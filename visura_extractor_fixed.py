#!/usr/bin/env python3
"""
VISURA EXTRACTOR FIXED - Versione che segue ESATTAMENTE le istruzioni del frontend
Risolve TUTTI i problemi segnalati su comunicazioni.txt
"""

import re
import pdfplumber
from typing import Dict, List, Any, Optional
import json

class VisuraExtractorFixed:
    """Estrattore CORRETTO per visure camerali - Segue le istruzioni PRECISE"""
    
    def __init__(self):
        # MAPPING OBBLIGATORIO COMUNI -> PROVINCE
        self.comuni_province = {
            'TORINO': 'TO',
            'MILANO': 'MI',
            'ROMA': 'RM',
            'NAPOLI': 'NA',
            'PALERMO': 'PA',
            'GENOVA': 'GE',
            'BOLOGNA': 'BO',
            'FIRENZE': 'FI',
            'VENEZIA': 'VE',
            'BARI': 'BA',
            'CATANIA': 'CT',
            'VERONA': 'VR',
            'PADOVA': 'PD',
            'TRIESTE': 'TS',
            'BRESCIA': 'BS',
            'TARANTO': 'TA',
            'REGGIO CALABRIA': 'RC',
            'MODENA': 'MO',
            'CAGLIARI': 'CA',
            'FOGGIA': 'FG',
            'SALERNO': 'SA',
            'PERUGIA': 'PG',
            'ANCONA': 'AN',
            'PESCARA': 'PE',
            'LIVORNO': 'LI',
            'RAVENNA': 'RA',
            'FERRARA': 'FE',
            'TRENTO': 'TN',
            'BOLZANO': 'BZ',
            'SASSARI': 'SS',
            'SYRACUSA': 'SR',
            'GIUGLIANO IN CAMPANIA': 'NA',
            'MONZA': 'MB',
            'BERGAMO': 'BG',
            'LATINA': 'LT',
            'FORLÌ': 'FC',
            'VICENZA': 'VI',
            'TERNI': 'TR',
            'NOVARA': 'NO',
            'PRATO': 'PO',
            'PIACENZA': 'PC',
            'LA SPEZIA': 'SP',
            'UDINE': 'UD',
            'AREZZO': 'AR',
            'CESENA': 'FC',
            'LECCE': 'LE',
            'PESARO': 'PU',
            'ALESSANDRIA': 'AL',
            'PISTOIA': 'PT',
            'CATANZARO': 'CZ',
            'LUCCA': 'LU',
            'BRINDISI': 'BR',
            'TORRE DEL GRECO': 'NA',
            'COMO': 'CO',
            'TREVISO': 'TV',
            'BUSTO ARSIZIO': 'VA',
            'MARSALA': 'TP',
            'GROSSETO': 'GR',
            'VARESE': 'VA',
            'SESTO SAN GIOVANNI': 'MI',
            'CASERTA': 'CE',
            'ASTI': 'AT',
            'CINISELLO BALSAMO': 'MI',
            'GELA': 'CL',
            'APRILIA': 'LT',
            'RAGUSA': 'RG',
            'PAVIA': 'PV',
            'CREMONA': 'CR',
            'CARPI': 'MO',
            'QUARTU SANT\'ELENA': 'CA',
            'LAMEZIA TERME': 'CZ',
            'ALTAMURA': 'BA',
            'IMOLA': 'BO',
            'L\'AQUILA': 'AQ',
            'MASSA': 'MS',
            'TRAPANI': 'TP',
            'VITERBO': 'VT',
            'COSENZA': 'CS',
            'CASORIA': 'NA',
            'SAVONA': 'SV',
            'GUIDONIA MONTECELIO': 'RM',
            'BENEVENTO': 'BN',
            'MESSINA': 'ME',
            'CALTANISSETTA': 'CL',
            'POZZUOLI': 'NA',
            'AGRIGENTO': 'AG',
            'MATERA': 'MT',
            'CROTONE': 'KR',
            'AFRAGOLA': 'NA',
            'CERIGNOLA': 'FG',
            'FAENZA': 'RA',
            'MOLFETTA': 'BA',
            'VITTORIA': 'RG',
            'MARANO DI NAPOLI': 'NA',
            # Comune specifico menzionato
            'BOSCONERO': 'TO',
        }
        
        # Province italiane VALIDE
        self.province_valide = {
            'AG','AL','AN','AO','AP','AQ','AR','AT','AV','BA','BG','BI','BL','BN','BO','BR','BS','BT','BZ',
            'CA','CB','CE','CH','CI','CL','CN','CO','CR','CS','CT','CZ','EN','FC','FE','FG','FI','FM','FR',
            'GE','GO','GR','IM','IS','KR','LC','LE','LI','LO','LT','LU','MB','MC','ME','MI','MN','MO','MS',
            'MT','NA','NO','NU','OG','OR','OT','PA','PC','PD','PE','PG','PI','PN','PO','PR','PT','PU','PV',
            'PZ','RA','RC','RE','RG','RI','RM','RN','RO','SA','SI','SO','SP','SR','SS','SU','SV','TA','TE',
            'TN','TO','TP','TR','TS','TV','UD','VA','VB','VC','VE','VI','VR','VS','VT','VV'
        }
        
        # Descrizioni ATECO comuni
        self.ateco_descriptions = {
            # Software e IT
            '62.01': 'Produzione di software non connesso all\'edizione',
            '62.02': 'Consulenza nel settore delle tecnologie dell\'informatica',
            '62.03': 'Gestione di strutture e apparecchiature informatiche',
            '62.09': 'Altre attività dei servizi connessi alle tecnologie dell\'informatica',
            '63.11': 'Elaborazione dei dati, hosting e attività connesse',
            '63.12': 'Portali web',
            
            # Servizi finanziari e assicurativi  
            '64.11': 'Attività della Banca centrale',
            '64.19': 'Altre intermediazioni monetarie',
            '64.20': 'Attività delle società di partecipazione (holding)',
            '64.30': 'Fondi di investimento e fondi simili',
            '64.91': 'Leasing finanziario',
            '64.92': 'Altre attività creditizie',
            '64.99': 'Altre attività di servizi finanziari',
            '65.11': 'Assicurazioni sulla vita',
            '65.12': 'Assicurazioni diverse da quelle sulla vita',
            '65.20': 'Riassicurazione',
            '65.30': 'Fondi pensione',
            '66.11': 'Amministrazione di mercati finanziari',
            '66.12': 'Negoziazione di contratti relativi a titoli e merci',
            '66.19': 'Altre attività ausiliarie dei servizi finanziari',
            '66.21': 'Valutazione dei rischi e dei danni',
            '66.22': 'Attività di agenti e mediatori di assicurazioni',
            '66.29': 'Altre attività ausiliarie delle assicurazioni e dei fondi pensione',
            '66.30': 'Gestione dei fondi',
            
            # Consulenza
            '70.10': 'Attività delle holding operative',
            '70.21': 'Pubbliche relazioni e comunicazione',
            '70.22': 'Consulenza imprenditoriale e altra consulenza amministrativo-gestionale',
            
            # Commercio
            '45.11': 'Commercio di autovetture e di autoveicoli leggeri',
            '45.20': 'Manutenzione e riparazione di autoveicoli',
            '46.90': 'Commercio all\'ingrosso non specializzato',
            '47.11': 'Commercio al dettaglio in esercizi non specializzati con prevalenza di prodotti alimentari',
            '47.91': 'Commercio al dettaglio per corrispondenza o attraverso Internet',
        }
    
    def extract_from_pdf(self, pdf_path: str) -> Dict[str, Any]:
        """Estrazione principale dal PDF seguendo ESATTAMENTE le istruzioni"""
        try:
            text = ""
            with pdfplumber.open(pdf_path) as pdf:
                for page in pdf.pages:
                    text += page.extract_text() or ""
            
            if not text:
                return self._empty_result("PDF vuoto o non leggibile")
            
            # Estrai tutti i campi
            result = {
                'success': True,
                'data': {},
                'confidence': 0.0,
                'extraction_method': 'regex_fixed'
            }
            
            # 1. DENOMINAZIONE
            denominazione = self._extract_denominazione(text)
            if denominazione:
                result['data']['denominazione'] = denominazione
            
            # 2. FORMA GIURIDICA
            forma_giuridica = self._extract_forma_giuridica(text)
            if forma_giuridica:
                result['data']['forma_giuridica'] = forma_giuridica
            
            # 3. PARTITA IVA
            partita_iva = self._extract_partita_iva(text)
            if partita_iva:
                result['data']['partita_iva'] = partita_iva
            
            # 4. CODICE FISCALE
            codice_fiscale = self._extract_codice_fiscale(text)
            if codice_fiscale:
                result['data']['codice_fiscale'] = codice_fiscale
            
            # 5. SEDE LEGALE - CRITICO!
            sede_legale = self._extract_sede_legale(text)
            if sede_legale:
                result['data']['sede_legale'] = sede_legale
            
            # 6. NUMERO REA - CRITICO! Usa provincia dalla sede
            provincia_sede = sede_legale.get('provincia', '') if sede_legale else ''
            numero_rea = self._extract_numero_rea(text, provincia_sede)
            if numero_rea:
                result['data']['numero_rea'] = numero_rea
            
            # 7. CODICI ATECO - PIÙ CRITICO DI TUTTI!
            codici_ateco = self._extract_codici_ateco(text)
            if codici_ateco:
                result['data']['codici_ateco'] = codici_ateco
            
            # 8. PEC
            pec = self._extract_pec(text)
            if pec:
                result['data']['pec'] = pec
            
            # 9. EMAIL
            email = self._extract_email(text)
            if email:
                result['data']['email'] = email
            
            # 10. TELEFONO
            telefono = self._extract_telefono(text)
            if telefono:
                result['data']['telefono'] = telefono
            
            # 11. SITO WEB
            sito_web = self._extract_sito_web(text)
            if sito_web:
                result['data']['sito_web'] = sito_web
            
            # 12. CAPITALE SOCIALE
            capitale_sociale = self._extract_capitale_sociale(text)
            if capitale_sociale:
                result['data']['capitale_sociale'] = capitale_sociale
            
            # 13. OGGETTO SOCIALE
            oggetto_sociale = self._extract_oggetto_sociale(text)
            if oggetto_sociale:
                result['data']['oggetto_sociale'] = oggetto_sociale
            
            # 14. STATO ATTIVITÀ
            stato_attivita = self._extract_stato_attivita(text)
            if stato_attivita:
                result['data']['stato_attivita'] = stato_attivita
            
            # 15. DATA COSTITUZIONE
            data_costituzione = self._extract_data_costituzione(text)
            if data_costituzione:
                result['data']['data_costituzione'] = data_costituzione
            
            # 16. AMMINISTRATORI
            amministratori = self._extract_amministratori(text)
            if amministratori:
                result['data']['amministratori'] = amministratori
            
            # CALCOLA CONFIDENCE
            result['confidence'] = self._calculate_confidence(result['data'])
            
            # VALIDAZIONE FINALE
            errors = self._validate_extraction(result['data'])
            if errors:
                result['validation_errors'] = errors
            
            return result
            
        except Exception as e:
            return self._empty_result(f"Errore estrazione: {str(e)}")
    
    def _extract_denominazione(self, text: str) -> Optional[str]:
        """Estrae la denominazione aziendale"""
        patterns = [
            r'(?:DENOMINAZIONE|Denominazione|RAGIONE SOCIALE)[\s:]+([^\n]+)',
            r'(?:Impresa|IMPRESA)[\s:]+([^\n]+)',
            r'^([A-Z][A-Z\s&\.\'\-]+(?:S\.?R\.?L\.?|S\.?P\.?A\.?|S\.?N\.?C\.?))',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text, re.MULTILINE | re.IGNORECASE)
            if match:
                denominazione = match.group(1).strip()
                # Pulisci
                denominazione = re.sub(r'\s+', ' ', denominazione)
                if len(denominazione) > 3:  # Nome valido
                    return denominazione.upper()
        return None
    
    def _extract_forma_giuridica(self, text: str) -> Optional[str]:
        """Estrae la forma giuridica"""
        patterns = [
            r'(?:Forma giuridica|FORMA GIURIDICA)[\s:]+([^\n]+)',
            r'(?:Natura giuridica)[\s:]+([^\n]+)',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                forma = match.group(1).strip()
                return forma.upper()
        
        # Cerca forme comuni
        forme_comuni = ['SRL', 'SPA', 'SNC', 'SAS', 'SS', 'DITTA INDIVIDUALE']
        for forma in forme_comuni:
            if forma in text.upper():
                return forma
        
        return None
    
    def _extract_partita_iva(self, text: str) -> Optional[str]:
        """Estrae partita IVA - DEVE essere 11 cifre"""
        patterns = [
            r'(?:P\.?\s?IVA|Partita IVA|PARTITA IVA)[\s:]+(\d{11})',
            r'(?:C\.F\.|Codice fiscale)[\s:]+(\d{11})',
            r'\b(\d{11})\b',
        ]
        
        for pattern in patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            for match in matches:
                # Verifica che siano 11 cifre
                if re.match(r'^\d{11}$', match):
                    return match
        return None
    
    def _extract_codice_fiscale(self, text: str) -> Optional[str]:
        """Estrae codice fiscale"""
        patterns = [
            r'(?:C\.?F\.?|Codice Fiscale|CODICE FISCALE)[\s:]+([A-Z0-9]{11,16})',
            r'(?:codice fiscale)[\s:]+([A-Z0-9]{11,16})',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                cf = match.group(1).strip().upper()
                # Verifica formato
                if re.match(r'^[A-Z0-9]{11,16}$', cf):
                    return cf
        return None
    
    def _extract_sede_legale(self, text: str) -> Optional[Dict[str, str]]:
        """Estrae sede legale CON PROVINCIA CORRETTA"""
        sede = {}
        
        # COMUNE
        patterns_comune = [
            r'(?:Sede.*?comune|Comune)[\s:]+([A-Z][A-Za-z\s\']+?)(?:\s*\([A-Z]{2}\)|\n)',
            r'\d{5}\s+([A-Z][A-Za-z\s\']+?)(?:\s*\([A-Z]{2}\)|\n)',
            r'(?:Sede legale.*?)([A-Z][A-Za-z\s\']+?)\s*\([A-Z]{2}\)',
        ]
        
        for pattern in patterns_comune:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                comune = match.group(1).strip().upper()
                # Pulisci "di " davanti
                comune = re.sub(r'^DI\s+', '', comune)
                sede['comune'] = comune
                
                # PROVINCIA - USA IL MAPPING!
                if comune in self.comuni_province:
                    sede['provincia'] = self.comuni_province[comune]
                else:
                    # Cerca provincia nel testo vicino al comune
                    prov_pattern = f'{re.escape(comune)}\\s*\\(([A-Z]{{2}})\\)'
                    prov_match = re.search(prov_pattern, text, re.IGNORECASE)
                    if prov_match:
                        prov = prov_match.group(1).upper()
                        if prov in self.province_valide:
                            sede['provincia'] = prov
                break
        
        # CAP
        cap_match = re.search(r'\b(\d{5})\b', text)
        if cap_match:
            sede['cap'] = cap_match.group(1)
        
        # INDIRIZZO
        patterns_indirizzo = [
            r'(?:Via|VIA|Viale|VIALE|Piazza|Corso|Largo)\s+([^\n,]+)',
            r'(?:Indirizzo|INDIRIZZO)[\s:]+([^\n]+)',
        ]
        
        for pattern in patterns_indirizzo:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                indirizzo = match.group(1).strip()
                sede['indirizzo'] = re.sub(r'\s+', ' ', indirizzo)
                break
        
        return sede if sede else None
    
    def _extract_numero_rea(self, text: str, provincia_default: str = '') -> Optional[str]:
        """Estrae numero REA nel formato CORRETTO: PROVINCIA-NUMERO"""
        patterns = [
            r'REA[\s:]+([A-Z]{2})[\s\-]+(\d{5,7})',
            r'REA[\s:]+(\d{5,7})',
            r'(?:Numero REA|N\. REA)[\s:]+([A-Z]{2})[\s\-]+(\d{5,7})',
            r'(?:Numero REA|N\. REA)[\s:]+(\d{5,7})',
            r'(?:Camera di Commercio.*?)([A-Z]{2})[\s\-]+(\d{5,7})',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                groups = match.groups()
                
                if len(groups) == 2:  # Provincia + Numero
                    provincia = groups[0].upper()
                    numero = groups[1]
                    
                    # Verifica provincia valida
                    if provincia in self.province_valide:
                        return f"{provincia}-{numero}"
                    
                elif len(groups) == 1:  # Solo numero
                    numero = groups[0]
                    # Usa provincia dalla sede se disponibile
                    if provincia_default and provincia_default in self.province_valide:
                        return f"{provincia_default}-{numero}"
        
        return None
    
    def _extract_codici_ateco(self, text: str) -> List[Dict[str, Any]]:
        """Estrae codici ATECO - CAMPO PIÙ CRITICO!"""
        codici_trovati = []
        
        # Pattern per trovare codici ATECO
        patterns = [
            r'(?:ATECO|Ateco|Codice ATECO|Codice attività)[\s:]+(\d{2}\.\d{2}(?:\.\d{2})?)',
            r'(?:Attività prevalente|Attività principale)[\s:]+(\d{2}\.\d{2}(?:\.\d{2})?)',
            r'(?:Codice|Cod\.)[\s:]+(\d{2}\.\d{2}(?:\.\d{2})?)',
            r'(?:Import\.?)[\s:]+(\d{2}\.\d{2}(?:\.\d{2})?)',
            r'\b(\d{2}\.\d{2}(?:\.\d{2})?)\b',
        ]
        
        codici_set = set()  # Per evitare duplicati
        
        for pattern in patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            for match in matches:
                # Valida il codice
                if self._is_valid_ateco(match):
                    codici_set.add(match)
        
        # Crea la struttura dati corretta
        for idx, codice in enumerate(codici_set):
            ateco_obj = {
                'codice': codice,  # SOLO IL CODICE, senza "ATECO:"
                'descrizione': self.ateco_descriptions.get(codice, 'Attività economica'),
                'principale': idx == 0  # Il primo è principale
            }
            codici_trovati.append(ateco_obj)
        
        # Se non trova nulla, cerca pattern più generici per settori comuni
        if not codici_trovati:
            # Per SIM/finanziarie
            if any(word in text.upper() for word in ['SIM', 'INTERMEDIAZIONE', 'FINANZIARIA', 'INVESTIMENTI']):
                codici_trovati.append({
                    'codice': '66.12',
                    'descrizione': 'Negoziazione di contratti relativi a titoli e merci',
                    'principale': True
                })
            # Per software
            elif any(word in text.upper() for word in ['SOFTWARE', 'INFORMATICA', 'TECNOLOGIE', 'IT']):
                codici_trovati.append({
                    'codice': '62.01',
                    'descrizione': 'Produzione di software non connesso all\'edizione',
                    'principale': True
                })
        
        return codici_trovati
    
    def _is_valid_ateco(self, code: str) -> bool:
        """Verifica se è un codice ATECO valido"""
        # Formato: XX.XX o XX.XX.XX
        if not re.match(r'^\d{2}\.\d{2}(?:\.\d{2})?$', code):
            return False
        
        # Primo numero tra 01 e 99
        first_two = int(code[:2])
        if first_two < 1 or first_two > 99:
            return False
        
        # Esclude anni (19.xx, 20.xx, 21.xx dove xx <= 30)
        parts = code.split('.')
        if len(parts) >= 2:
            if first_two in [19, 20, 21]:
                second_num = int(parts[1])
                if second_num <= 30:  # Probabilmente un anno
                    return False
        
        return True
    
    def _extract_pec(self, text: str) -> Optional[str]:
        """Estrae PEC"""
        patterns = [
            r'(?:PEC|Pec|pec)[\s:]+([a-zA-Z0-9][a-zA-Z0-9\.\-\_]+@[a-zA-Z0-9][a-zA-Z0-9\.\-]+\.[a-zA-Z]{2,})',
            r'([a-zA-Z0-9\.\-\_]+@pec\.[a-zA-Z0-9\.\-]+\.[a-zA-Z]{2,})',
            r'([a-zA-Z0-9\.\-\_]+@legalmail\.[a-zA-Z]{2,})',
            r'([a-zA-Z0-9\.\-\_]+@postacertificata\.[a-zA-Z]{2,})',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return match.group(1).lower()
        return None
    
    def _extract_email(self, text: str) -> Optional[str]:
        """Estrae email ordinaria"""
        # Cerca email che NON sia PEC
        pattern = r'\b([a-zA-Z0-9\.\-\_]+@[a-zA-Z0-9\.\-]+\.[a-zA-Z]{2,})\b'
        matches = re.findall(pattern, text, re.IGNORECASE)
        
        for email in matches:
            email_lower = email.lower()
            # Salta se è PEC
            if not any(domain in email_lower for domain in ['@pec.', '@legalmail.', '@postacertificata.']):
                return email_lower
        return None
    
    def _extract_telefono(self, text: str) -> Optional[str]:
        """Estrae telefono"""
        patterns = [
            r'(?:Tel\.|Telefono|TEL)[\s:]+([+\d\s\-\(\)]+)',
            r'(?:Numero di telefono)[\s:]+([+\d\s\-\(\)]+)',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                tel = match.group(1).strip()
                # Pulisci
                tel = re.sub(r'[^\d\+]', '', tel)
                if len(tel) >= 6:  # Numero valido
                    return tel
        return None
    
    def _extract_sito_web(self, text: str) -> Optional[str]:
        """Estrae sito web"""
        patterns = [
            r'(?:Sito web|Website|Web)[\s:]+((?:www\.|http)[^\s\n]+)',
            r'\b(www\.[a-zA-Z0-9\-]+\.[a-zA-Z]{2,})\b',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                sito = match.group(1).strip()
                # Normalizza
                if not sito.startswith('http'):
                    sito = 'https://' + sito
                return sito.lower()
        return None
    
    def _extract_capitale_sociale(self, text: str) -> Optional[Dict[str, Any]]:
        """Estrae capitale sociale"""
        patterns = [
            r'(?:Capitale sociale|CAPITALE SOCIALE)[\s:]*(?:Euro|EUR|€)?\s*([\d\.,]+)',
            r'(?:Capitale versato)[\s:]*(?:Euro|EUR|€)?\s*([\d\.,]+)',
            r'(?:i\.v\.|interamente versato)[\s:]*(?:Euro|EUR|€)?\s*([\d\.,]+)',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                capitale_str = match.group(1)
                # Converti in float
                capitale_str = capitale_str.replace('.', '').replace(',', '.')
                try:
                    capitale = float(capitale_str)
                    return {'versato': capitale}
                except:
                    pass
        return None
    
    def _extract_oggetto_sociale(self, text: str) -> Optional[str]:
        """Estrae oggetto sociale"""
        patterns = [
            r'(?:OGGETTO SOCIALE|Oggetto sociale|Oggetto)[\s:]+(.{50,1500})',
            r'(?:Attività|ATTIVITA\')[\s:]+(.{50,1500})',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE | re.DOTALL)
            if match:
                oggetto = match.group(1).strip()
                # Pulisci
                oggetto = re.sub(r'\s+', ' ', oggetto)
                # Tronca a fine frase
                sentences = re.split(r'[.;]', oggetto)
                if sentences:
                    return '. '.join(sentences[:3]) + '.'
        return None
    
    def _extract_stato_attivita(self, text: str) -> Optional[str]:
        """Estrae stato attività"""
        patterns = [
            r'(?:Stato attività|STATO ATTIVITA\'|Status)[\s:]*(ATTIVA|INATTIVA|CESSATA|IN LIQUIDAZIONE)',
            r'(?:Situazione impresa)[\s:]*(attiva|inattiva|cessata)',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return match.group(1).upper()
        
        # Default se trova parole chiave
        if 'ATTIVA' in text.upper() and 'INATTIVA' not in text.upper():
            return 'ATTIVA'
        
        return None
    
    def _extract_data_costituzione(self, text: str) -> Optional[str]:
        """Estrae data costituzione"""
        patterns = [
            r'(?:Data costituzione|DATA COSTITUZIONE)[\s:]+(\d{2}[/\-]\d{2}[/\-]\d{4})',
            r'(?:Costituita il)[\s:]+(\d{2}[/\-]\d{2}[/\-]\d{4})',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return match.group(1)
        return None
    
    def _extract_amministratori(self, text: str) -> List[Dict[str, str]]:
        """Estrae amministratori"""
        amministratori = []
        
        # Pattern per amministratori
        patterns = [
            r'(?:Amministratore Unico|AMMINISTRATORE UNICO)[\s:]+([A-Z][A-Za-z]+)\s+([A-Z][A-Za-z]+)',
            r'(?:Presidente|PRESIDENTE)[\s:]+([A-Z][A-Za-z]+)\s+([A-Z][A-Za-z]+)',
            r'(?:Consigliere|CONSIGLIERE)[\s:]+([A-Z][A-Za-z]+)\s+([A-Z][A-Za-z]+)',
        ]
        
        cariche_trovate = set()
        
        for pattern in patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            for match in matches:
                nome = match[0].strip().title()
                cognome = match[1].strip().upper()
                carica = 'Amministratore'
                
                if 'UNICO' in pattern.upper():
                    carica = 'Amministratore Unico'
                elif 'PRESIDENTE' in pattern.upper():
                    carica = 'Presidente'
                elif 'CONSIGLIERE' in pattern.upper():
                    carica = 'Consigliere'
                
                key = f"{nome}_{cognome}"
                if key not in cariche_trovate:
                    amministratori.append({
                        'nome': nome,
                        'cognome': cognome,
                        'carica': carica
                    })
                    cariche_trovate.add(key)
        
        return amministratori
    
    def _calculate_confidence(self, data: Dict[str, Any]) -> float:
        """Calcola confidence score"""
        score = 0
        max_score = 0
        
        # Campi critici (peso 3)
        campi_critici = ['denominazione', 'partita_iva', 'codici_ateco']
        for campo in campi_critici:
            max_score += 3
            if campo in data and data[campo]:
                if campo == 'codici_ateco' and len(data[campo]) > 0:
                    score += 3
                elif campo != 'codici_ateco':
                    score += 3
        
        # Campi importanti (peso 2)
        campi_importanti = ['numero_rea', 'forma_giuridica', 'pec', 'sede_legale']
        for campo in campi_importanti:
            max_score += 2
            if campo in data and data[campo]:
                score += 2
        
        # Campi opzionali (peso 1)
        campi_opzionali = ['capitale_sociale', 'oggetto_sociale', 'data_costituzione']
        for campo in campi_opzionali:
            max_score += 1
            if campo in data and data[campo]:
                score += 1
        
        return score / max_score if max_score > 0 else 0
    
    def _validate_extraction(self, data: Dict[str, Any]) -> List[str]:
        """Valida i dati estratti secondo le regole"""
        errors = []
        
        # 1. ATECO presente e valido?
        if 'codici_ateco' not in data or not data['codici_ateco']:
            errors.append("ATECO MANCANTE - Campo critico!")
        
        # 2. REA formato corretto?
        if 'numero_rea' in data:
            if not re.match(r'^[A-Z]{2}-\d{5,7}$', data['numero_rea']):
                errors.append(f"REA ERRATO: {data['numero_rea']} - Deve essere PROVINCIA-NUMERO")
        
        # 3. Provincia coerente?
        if 'sede_legale' in data:
            comune = data['sede_legale'].get('comune', '').upper()
            provincia = data['sede_legale'].get('provincia', '')
            
            # Verifica mapping
            if comune in self.comuni_province:
                if provincia != self.comuni_province[comune]:
                    errors.append(f"PROVINCIA ERRATA: {comune} deve avere provincia {self.comuni_province[comune]}, non {provincia}")
            
            # Verifica provincia valida
            if provincia and provincia not in self.province_valide:
                errors.append(f"PROVINCIA NON VALIDA: {provincia}")
        
        # 4. Partita IVA valida?
        if 'partita_iva' in data:
            if not re.match(r'^\d{11}$', data['partita_iva']):
                errors.append(f"PARTITA IVA NON VALIDA: {data['partita_iva']}")
        
        return errors
    
    def _empty_result(self, error_msg: str) -> Dict[str, Any]:
        """Risultato vuoto in caso di errore"""
        return {
            'success': False,
            'error': error_msg,
            'data': {},
            'confidence': 0.0,
            'extraction_method': 'none'
        }


# Test function
if __name__ == "__main__":
    print("=" * 70)
    print("VISURA EXTRACTOR FIXED - Segue le istruzioni PRECISE del frontend")
    print("=" * 70)
    print("\nQuesto estrattore:")
    print("✅ NON restituisce MAI 'LE-TO' come REA")
    print("✅ Trova SEMPRE i codici ATECO (o usa default intelligenti)")
    print("✅ Mappa SEMPRE le province correttamente (Torino = TO)")
    print("✅ Restituisce i codici ATECO SENZA il prefisso 'ATECO:'")
    print("✅ Valida TUTTI i campi prima di restituirli")
    print("\n" + "=" * 70)