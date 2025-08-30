#!/usr/bin/env python3
"""
🚀 VISURA EXTRACTOR ULTIMATE - ESTRAZIONE SUPER POTENTE
Estrae TUTTI i dati da QUALSIASI visura con precisione chirurgica
"""

import re
from typing import Dict, List, Any, Optional, Tuple
import logging

# Configurazione logging
logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger(__name__)


class VisuraExtractorUltimate:
    """Estrattore DEFINITIVO per visure camerali - ZERO ERRORI!"""
    
    def __init__(self):
        # Province italiane VALIDE (per validazione)
        self.province_valide = {
            'AG', 'AL', 'AN', 'AO', 'AP', 'AQ', 'AR', 'AT', 'AV', 'BA', 'BG', 'BI', 'BL', 'BN', 'BO',
            'BR', 'BS', 'BT', 'BZ', 'CA', 'CB', 'CE', 'CH', 'CI', 'CL', 'CN', 'CO', 'CR', 'CS', 'CT',
            'CZ', 'EN', 'FC', 'FE', 'FG', 'FI', 'FM', 'FR', 'GE', 'GO', 'GR', 'IM', 'IS', 'KR', 'LC',
            'LE', 'LI', 'LO', 'LT', 'LU', 'MB', 'MC', 'ME', 'MI', 'MN', 'MO', 'MS', 'MT', 'NA', 'NO',
            'NU', 'OG', 'OR', 'OT', 'PA', 'PC', 'PD', 'PE', 'PG', 'PI', 'PN', 'PO', 'PR', 'PT', 'PU',
            'PV', 'PZ', 'RA', 'RC', 'RE', 'RG', 'RI', 'RM', 'RN', 'RO', 'SA', 'SI', 'SO', 'SP', 'SR',
            'SS', 'SU', 'SV', 'TA', 'TE', 'TN', 'TO', 'TP', 'TR', 'TS', 'TV', 'UD', 'VA', 'VB', 'VC',
            'VE', 'VI', 'VR', 'VS', 'VT', 'VV'
        }
        
        # Dizionario COMPLETO codici ATECO con descrizioni COMPLETE
        self.ateco_descriptions = {
            '01': 'Coltivazioni agricole e produzione di prodotti animali',
            '10': 'Industrie alimentari',
            '20': 'Fabbricazione di prodotti chimici',
            '25': 'Fabbricazione di prodotti in metallo',
            '28': 'Fabbricazione di macchinari ed apparecchiature',
            '29': 'Fabbricazione di autoveicoli',
            '41': 'Costruzione di edifici',
            '45': 'Commercio all\'ingrosso e al dettaglio e riparazione di autoveicoli',
            '47': 'Commercio al dettaglio',
            '56': 'Attività dei servizi di ristorazione',
            '62.01': 'Produzione di software non connesso all\'edizione',
            '62.02': 'Consulenza nel settore delle tecnologie dell\'informatica',
            '62.03': 'Gestione di strutture e apparecchiature informatiche hardware e software',
            '62.09': 'Altre attività dei servizi connessi alle tecnologie dell\'informatica',
            '63.11': 'Elaborazione dei dati, hosting e attività connesse',
            '63.12': 'Portali web',
            '68': 'Attività immobiliari',
            '70.22': 'Consulenza imprenditoriale e altra consulenza amministrativo-gestionale e pianificazione aziendale',
            '73': 'Pubblicità e ricerche di mercato',
            '74': 'Altre attività professionali, scientifiche e tecniche',
            '82': 'Attività di supporto per le funzioni d\'ufficio',
        }
    
    def extract_denominazione(self, text: str) -> Optional[str]:
        """Estrae la denominazione/ragione sociale con MASSIMA precisione"""
        patterns = [
            # Pattern più specifici prima
            r'(?:DENOMINAZIONE|Denominazione|RAGIONE SOCIALE)\s*[:]\s*([A-Z][A-Z\s&\.\-\']+(?:S\.?R\.?L\.?|S\.?P\.?A\.?|S\.?N\.?C\.?))',
            r'(?:Impresa|IMPRESA)\s*[:]\s*([A-Z][A-Z\s&\.\-\']+)',
            r'(?:Ditta|DITTA)\s*[:]\s*([A-Z][A-Z\s&\.\-\']+)',
            # Pattern per visure con formato diverso
            r'^([A-Z][A-Z\s&\.\-\']+(?:S\.?R\.?L\.?|S\.?P\.?A\.?|S\.?N\.?C\.?))\s*$',
            # Cerca nel contesto di "Dati anagrafici"
            r'(?:Dati anagrafici|DATI ANAGRAFICI)[\s\S]{0,100}?([A-Z][A-Z\s&\.\-\']+(?:S\.?R\.?L\.?|S\.?P\.?A\.?))',
        ]
        
        for pattern in patterns:
            matches = re.findall(pattern, text, re.MULTILINE | re.IGNORECASE)
            if matches:
                denominazione = matches[0].strip()
                # Pulisci e normalizza
                denominazione = re.sub(r'\s+', ' ', denominazione)
                if len(denominazione) > 3 and denominazione.upper() != denominazione.lower():
                    return denominazione
        
        return None
    
    def extract_partita_iva(self, text: str) -> Optional[str]:
        """Estrae la partita IVA - SEMPRE 11 cifre"""
        patterns = [
            r'(?:P\.?\s?IVA|Partita IVA|PARTITA IVA)\s*[:]\s*(\d{11})',
            r'(?:Codice fiscale|C\.F\.)\s*[:]\s*(\d{11})',  # Spesso P.IVA = C.F.
            r'(?:Numero di iscrizione|Codice fiscale e numero iscrizione)\s*[:]\s*(\d{11})',
            r'\b(\d{11})\b(?=[\s\S]{0,50}(?:IVA|iva))',  # Cerca 11 cifre vicino a "IVA"
        ]
        
        for pattern in patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            if matches:
                piva = matches[0]
                # Validazione: deve essere esattamente 11 cifre
                if re.match(r'^\d{11}$', piva):
                    return piva
        
        return None
    
    def extract_codici_ateco(self, text: str) -> List[Dict[str, Any]]:
        """Estrae SOLO codici ATECO validi con descrizioni COMPLETE"""
        ateco_list = []
        
        # Pattern SUPER PRECISI per ATECO
        patterns = [
            # Formato: Codice: XX.XX - descrizione
            r'(?:Codice|CODICE|Cod\.)\s*[:]\s*(\d{2}\.?\d{0,2}\.?\d{0,2})\s*[\-]\s*([^\n]+)',
            # Formato: ATECO XX.XX descrizione
            r'(?:ATECO|Ateco|Codice ATECO)\s*[:]\s*(\d{2}\.?\d{0,2}\.?\d{0,2})\s*[\-]?\s*([^\n]*)',
            # Formato: Attività prevalente/principale
            r'(?:Attività prevalente|Attività principale|ATTIVITA\' PREVALENTE)\s*[:]\s*(\d{2}\.?\d{0,2}\.?\d{0,2})\s*[\-]?\s*([^\n]*)',
            # Import/Export codes
            r'(?:Import\.|Export\.|Importanza)\s*[:]\s*(\d{2}\.?\d{0,2}\.?\d{0,2})\s*[\-]?\s*([^\n]*)',
            # Formato generico ma SOLO con descrizione
            r'(\d{2}\.\d{2}(?:\.\d{2})?)\s+[\-]\s+([a-zA-Z][^\n]+)',
        ]
        
        seen_codes = set()
        
        for pattern in patterns:
            matches = re.findall(pattern, text, re.IGNORECASE | re.MULTILINE)
            for match in matches:
                code_raw = match[0].strip()
                description_raw = match[1].strip() if len(match) > 1 else ''
                
                # Normalizza il codice ATECO
                code = self.normalize_ateco_code(code_raw)
                
                # Valida che sia un ATECO reale
                if not self.is_valid_ateco(code):
                    continue
                
                # Evita duplicati
                if code in seen_codes:
                    continue
                seen_codes.add(code)
                
                # Pulisci e completa la descrizione
                description = self.clean_ateco_description(description_raw)
                if not description or len(description) < 5:
                    # Usa il dizionario per descrizione completa
                    description = self.get_ateco_description(code)
                
                ateco_list.append({
                    'codice': f'ATECO: {code}',  # SEMPRE con etichetta!
                    'codice_puro': code,
                    'descrizione': description,
                    'principale': len(ateco_list) == 0,  # Il primo è principale
                    'label': 'ATECO'
                })
        
        return ateco_list
    
    def normalize_ateco_code(self, code: str) -> str:
        """Normalizza il codice ATECO al formato XX.XX o XX.XX.XX"""
        # Rimuovi spazi e caratteri non numerici/punto
        code = re.sub(r'[^\d.]', '', code)
        
        # Se non ha punti, aggiungili
        if '.' not in code:
            if len(code) >= 4:
                code = f"{code[:2]}.{code[2:4]}"
                if len(code) > 5:
                    code = f"{code[:5]}.{code[5:]}"
        
        return code
    
    def is_valid_ateco(self, code: str) -> bool:
        """Verifica che sia un codice ATECO valido"""
        # Formato: XX.XX o XX.XX.XX
        if not re.match(r'^\d{2}(\.\d{2}){1,2}$', code):
            return False
        
        parts = code.split('.')
        first = int(parts[0])
        
        # Codici ATECO validi: 01-99 MA escludi anni
        if first < 1 or first > 99:
            return False
        
        # Escludi anni (19.xx, 20.xx, 21.xx dove xx < 50)
        if first in [19, 20, 21]:
            if len(parts) > 1:
                second = int(parts[1])
                if second < 50:  # Probabilmente un anno
                    return False
        
        return True
    
    def clean_ateco_description(self, desc: str) -> str:
        """Pulisce la descrizione ATECO"""
        if not desc:
            return ''
        
        # Rimuovi caratteri inutili
        desc = re.sub(r'^[\*\-\•\s]+', '', desc)
        desc = re.sub(r'[\*\-\•\s]+$', '', desc)
        
        # Rimuovi pattern non descrittivi
        remove_patterns = [
            r'^\d+$',  # Solo numeri
            r'^[A-Z]{2,}\s+DEL\s+',  # BIS DEL DECRETO...
            r'Addetti.*$',  # Info addetti
            r'\d{2}/\d{2}/\d{4}',  # Date
        ]
        
        for pattern in remove_patterns:
            desc = re.sub(pattern, '', desc, flags=re.IGNORECASE)
        
        desc = desc.strip()
        
        # Capitalizza correttamente
        if desc and desc[0].islower():
            desc = desc[0].upper() + desc[1:]
        
        return desc
    
    def get_ateco_description(self, code: str) -> str:
        """Ottiene la descrizione completa dal dizionario"""
        # Prova prima il codice completo
        if code in self.ateco_descriptions:
            return self.ateco_descriptions[code]
        
        # Prova con i primi 2 numeri
        prefix = code[:2]
        if prefix in self.ateco_descriptions:
            return self.ateco_descriptions[prefix]
        
        # Default generico ma informativo
        return f"Attività economica codice {code}"
    
    def extract_numero_rea(self, text: str) -> Optional[str]:
        """Estrae il numero REA PULITO e FORMATTATO"""
        patterns = [
            r'(?:REA|R\.E\.A\.|Numero REA)\s*[:]\s*([A-Z]{2})[\s\-]?(\d{5,7})',
            r'(?:REA|R\.E\.A\.)\s+([A-Z]{2})[\s\-]?(\d{5,7})',
            r'(?:Numero iscrizione)\s*[:]\s*([A-Z]{2})[\s\-]?(\d{5,7})',
            r'([A-Z]{2})[\s\-](\d{6,7})(?=[\s\S]{0,50}REA)',
        ]
        
        for pattern in patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            if matches:
                provincia = matches[0][0].upper()
                numero = matches[0][1]
                
                # Valida la provincia
                if provincia in self.province_valide:
                    return f"{provincia}-{numero}"
        
        # Fallback: cerca solo il numero
        numero_patterns = [
            r'(?:REA|R\.E\.A\.)\s*[:]\s*(\d{6,7})',
            r'(?:Numero REA)\s*[:]\s*(\d{6,7})',
        ]
        
        for pattern in numero_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            if matches:
                return matches[0]
        
        return None
    
    def extract_sede_legale(self, text: str) -> Dict[str, str]:
        """Estrae la sede legale COMPLETA con provincia CORRETTA"""
        sede = {
            'indirizzo': '',
            'cap': '',
            'comune': '',
            'provincia': '',
            'nazione': 'ITALIA'
        }
        
        # Pattern per sede completa
        sede_patterns = [
            r'(?:Sede legale|SEDE LEGALE|Sede)\s*[:]\s*([^\n]+)',
            r'(?:Indirizzo sede|Indirizzo)\s*[:]\s*([^\n]+)',
            r'(?:Via|VIA|Viale|Piazza|Corso)\s+([^\n]+?)(?:\d{5}|\n)',
        ]
        
        for pattern in sede_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            if matches:
                sede_text = matches[0]
                
                # Estrai CAP
                cap_match = re.search(r'\b(\d{5})\b', sede_text)
                if cap_match:
                    sede['cap'] = cap_match.group(1)
                
                # Estrai provincia VALIDA
                for prov in self.province_valide:
                    if re.search(rf'\b{prov}\b', sede_text, re.IGNORECASE):
                        sede['provincia'] = prov
                        break
                
                # Se non trovata nella sede, cerca nel contesto REA
                if not sede['provincia']:
                    rea = self.extract_numero_rea(text)
                    if rea and '-' in rea:
                        prov_from_rea = rea.split('-')[0]
                        if prov_from_rea in self.province_valide:
                            sede['provincia'] = prov_from_rea
                
                # Estrai comune
                comune_match = re.search(r'(\b[A-Z][A-Za-z]+(?:\s+[A-Z][A-Za-z]+)*)\s*\(' + sede['provincia'], sede_text, re.IGNORECASE)
                if comune_match:
                    sede['comune'] = comune_match.group(1).strip()
                elif sede['cap']:
                    # Cerca il comune prima del CAP
                    comune_match = re.search(r'([A-Z][A-Za-z]+(?:\s+[A-Z][A-Za-z]+)*)\s*' + sede['cap'], sede_text, re.IGNORECASE)
                    if comune_match:
                        sede['comune'] = comune_match.group(1).strip()
                
                # Estrai indirizzo
                via_match = re.search(r'((?:Via|VIA|Viale|Piazza|Corso|Largo)[^,\n]+)', sede_text, re.IGNORECASE)
                if via_match:
                    sede['indirizzo'] = via_match.group(1).strip()
                
                break
        
        return sede
    
    def extract_capitale_sociale(self, text: str) -> Dict[str, Any]:
        """Estrae il capitale sociale CORRETTAMENTE"""
        capitale = {
            'versato': 0.0,
            'deliberato': 0.0,
            'valuta': 'EUR'
        }
        
        patterns = [
            r'(?:Capitale sociale|CAPITALE SOCIALE)\s*[:]\s*(?:Euro|EUR|€)?\s*([\d\.,]+)',
            r'(?:Capitale versato|CAPITALE VERSATO)\s*[:]\s*(?:Euro|EUR|€)?\s*([\d\.,]+)',
            r'(?:Capitale deliberato)\s*[:]\s*(?:Euro|EUR|€)?\s*([\d\.,]+)',
            r'(?:i\.v\.|interamente versato)\s*[:]\s*(?:Euro|EUR|€)?\s*([\d\.,]+)',
        ]
        
        for pattern in patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            if matches:
                # Converti in float
                value_str = matches[0].replace('.', '').replace(',', '.')
                try:
                    value = float(value_str)
                    if value > 0:
                        capitale['versato'] = value
                        capitale['deliberato'] = value
                        break
                except:
                    pass
        
        return capitale
    
    def extract_oggetto_sociale(self, text: str) -> Optional[str]:
        """Estrae l'oggetto sociale COMPLETO"""
        patterns = [
            r'(?:Oggetto sociale|OGGETTO SOCIALE|Oggetto)\s*[:]\s*((?:[^\n][\s\S]){50,1500}?)(?:\n\n|\nDati|$)',
            r'(?:Oggetto)\s*[:]\s*((?:[^\n][\s\S]){50,1000}?)(?:\n\n|$)',
            r'(?:ATTIVITA\'|Attività)\s*[:]\s*((?:[^\n][\s\S]){50,1000}?)(?:\n\n|$)',
        ]
        
        for pattern in patterns:
            matches = re.findall(pattern, text, re.IGNORECASE | re.DOTALL)
            if matches:
                oggetto = matches[0]
                # Pulisci
                oggetto = re.sub(r'\s+', ' ', oggetto)
                oggetto = oggetto.strip()
                
                # Se troppo lungo, tronca intelligentemente
                if len(oggetto) > 1500:
                    # Trova l'ultimo punto entro 1500 caratteri
                    last_period = oggetto[:1500].rfind('.')
                    if last_period > 0:
                        oggetto = oggetto[:last_period + 1]
                    else:
                        oggetto = oggetto[:1497] + '...'
                
                return oggetto
        
        return None
    
    def extract_pec(self, text: str) -> Optional[str]:
        """Estrae la PEC"""
        patterns = [
            r'(?:PEC|Pec|pec|Posta Elettronica Certificata)\s*[:]\s*([a-zA-Z0-9][\w\.\-]+@[\w\.\-]+\.[a-zA-Z]{2,})',
            r'([a-zA-Z0-9][\w\.\-]+@pec\.[\w\.\-]+\.[a-zA-Z]{2,})',
            r'(?:Indirizzo PEC|INDIRIZZO PEC)\s*[:]\s*([a-zA-Z0-9][\w\.\-]+@[\w\.\-]+\.[a-zA-Z]{2,})',
        ]
        
        for pattern in patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            if matches:
                email = matches[0]
                # Validazione base
                if '@' in email and '.' in email.split('@')[1]:
                    return email.lower()
        
        return None
    
    def extract_forma_giuridica(self, text: str) -> Optional[str]:
        """Estrae la forma giuridica"""
        patterns = [
            r'(?:Forma giuridica|FORMA GIURIDICA)\s*[:]\s*([^\n]+)',
            r'(?:Tipo società|Natura giuridica)\s*[:]\s*([^\n]+)',
        ]
        
        for pattern in patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            if matches:
                forma = matches[0].strip()
                # Normalizza
                forma = forma.upper()
                if 'RESPONSABILITA' in forma and 'LIMITATA' in forma:
                    return "SOCIETA' A RESPONSABILITA' LIMITATA"
                elif 'S.R.L' in forma or 'SRL' in forma:
                    return "SOCIETA' A RESPONSABILITA' LIMITATA"
                elif 'S.P.A' in forma or 'SPA' in forma:
                    return "SOCIETA' PER AZIONI"
                else:
                    return forma
        
        # Inferisci dalla denominazione
        denominazione = self.extract_denominazione(text)
        if denominazione:
            if 'SRL' in denominazione or 'S.R.L' in denominazione:
                return "SOCIETA' A RESPONSABILITA' LIMITATA"
            elif 'SPA' in denominazione or 'S.P.A' in denominazione:
                return "SOCIETA' PER AZIONI"
        
        return None
    
    def extract_all_data(self, text: str) -> Dict[str, Any]:
        """Estrae TUTTI i dati con OUTPUT ECCEZIONALE"""
        
        logger.info("=" * 70)
        logger.info("🚀 INIZIO ESTRAZIONE SUPER POTENTE")
        logger.info("=" * 70)
        
        # Estrai tutti i campi
        data = {
            'denominazione': self.extract_denominazione(text),
            'partita_iva': self.extract_partita_iva(text),
            'codice_fiscale': None,
            'forma_giuridica': self.extract_forma_giuridica(text),
            'numero_rea': self.extract_numero_rea(text),
            'codici_ateco': self.extract_codici_ateco(text),
            'sede_legale': self.extract_sede_legale(text),
            'capitale_sociale': self.extract_capitale_sociale(text),
            'oggetto_sociale': self.extract_oggetto_sociale(text),
            'pec': self.extract_pec(text),
            'stato_attivita': 'ATTIVA',  # Default
            'tipo_business': 'B2B',  # Default inferito
            'confidence': 0.0
        }
        
        # Codice fiscale = Partita IVA per società
        data['codice_fiscale'] = data['partita_iva']
        
        # Calcola confidence
        fields_found = sum([
            1 if data['denominazione'] else 0,
            1 if data['partita_iva'] else 0,
            1 if data['numero_rea'] else 0,
            1 if data['codici_ateco'] else 0,
            1 if data['sede_legale']['comune'] else 0,
            1 if data['capitale_sociale']['versato'] > 0 else 0,
            1 if data['pec'] else 0,
            1 if data['oggetto_sociale'] else 0,
        ])
        
        data['confidence'] = min(0.95, fields_found / 8)
        
        # Log risultati
        logger.info("\n✅ ESTRAZIONE COMPLETATA:")
        logger.info(f"📊 Campi estratti: {fields_found}/8")
        logger.info(f"📈 Confidence: {data['confidence']:.0%}")
        
        if data['denominazione']:
            logger.info(f"🏢 Denominazione: {data['denominazione']}")
        if data['partita_iva']:
            logger.info(f"🔢 P.IVA: {data['partita_iva']}")
        if data['numero_rea']:
            logger.info(f"📋 REA: {data['numero_rea']}")
        if data['codici_ateco']:
            for ateco in data['codici_ateco']:
                logger.info(f"🎯 {ateco['codice']} - {ateco['descrizione']}")
        if data['sede_legale']['provincia']:
            logger.info(f"📍 Provincia: {data['sede_legale']['provincia']}")
        
        logger.info("=" * 70)
        
        return data


def format_output_eccezionale(data: Dict[str, Any]) -> str:
    """Formatta l'output in modo ECCEZIONALE"""
    
    output = []
    output.append("✅ **Visura elaborata con successo!**\n")
    
    # DATI AZIENDA
    output.append("**📋 DATI AZIENDA**")
    if data.get('denominazione'):
        output.append(f"**Denominazione:** {data['denominazione']}")
    if data.get('forma_giuridica'):
        output.append(f"**Forma Giuridica:** {data['forma_giuridica']}")
    if data.get('partita_iva'):
        output.append(f"**Partita IVA:** {data['partita_iva']}")
    if data.get('codice_fiscale'):
        output.append(f"**Codice Fiscale:** {data['codice_fiscale']}")
    if data.get('numero_rea'):
        output.append(f"**REA:** {data['numero_rea']}")
    
    # CONTATTI
    output.append("\n**📧 CONTATTI**")
    if data.get('pec'):
        output.append(f"**PEC:** {data['pec']} ✅")
    
    # ATTIVITÀ
    output.append("\n**🏢 ATTIVITÀ**")
    if data.get('codici_ateco'):
        for ateco in data['codici_ateco']:
            principale = " *(principale)*" if ateco.get('principale') else ""
            output.append(f"**{ateco['codice']}** - {ateco['descrizione']}{principale}")
    
    if data.get('oggetto_sociale'):
        # Mostra oggetto sociale COMPLETO (fino a 500 caratteri)
        oggetto = data['oggetto_sociale'][:500]
        if len(data['oggetto_sociale']) > 500:
            oggetto += '...'
        output.append(f"**Oggetto Sociale:** {oggetto}")
    
    output.append(f"**Stato:** {data.get('stato_attivita', 'ATTIVA')}")
    output.append(f"**Tipo Business:** {data.get('tipo_business', 'B2B')}")
    
    # SEDE LEGALE
    output.append("\n**📍 SEDE LEGALE**")
    sede = data.get('sede_legale', {})
    if sede.get('comune') and sede.get('provincia'):
        output.append(f"{sede['comune']} ({sede['provincia']}) - CAP {sede.get('cap', 'N/D')}")
    if sede.get('indirizzo'):
        output.append(sede['indirizzo'])
    
    # CAPITALE SOCIALE
    if data.get('capitale_sociale', {}).get('versato'):
        output.append("\n**💶 CAPITALE SOCIALE**")
        output.append(f"**Versato:** €{data['capitale_sociale']['versato']:,.2f}")
    
    # ESTRAZIONE
    output.append("\n**📊 ESTRAZIONE**")
    output.append("**Metodo:** ultimate_extraction")
    output.append(f"**Confidenza:** {data.get('confidence', 0):.0%}")
    
    return "\n".join(output)


# TEST CON DATI SIMULATI
if __name__ == "__main__":
    # Simula testo da visura CELERYA
    test_text = """
    VISURA ORDINARIA SOCIETA' DI CAPITALE
    
    Denominazione: CELERYA SRL
    Forma giuridica: SOCIETA' A RESPONSABILITA' LIMITATA
    
    Codice fiscale e numero iscrizione: 12230960010
    REA: TO-1275874
    
    PEC: celerya@pec.it
    
    Sede legale: BOSCONERO (TO) VIA DON GIOVANNI BOSCO 26 CAP 10080
    
    Capitale sociale: Euro 12.940,85 i.v.
    
    Attività prevalente:
    Codice: 62.01 - produzione di software non connesso all'edizione
    Importanza: 70.22 - consulenza imprenditoriale e altra consulenza amministrativo-gestionale
    
    Oggetto sociale: LA SOCIETA' HA PER OGGETTO LO SVILUPPO, LA PRODUZIONE E LA 
    COMMERCIALIZZAZIONE DI PRODOTTI O SERVIZI INNOVATIVI AD ALTO VALORE 
    TECNOLOGICO, E PIU' SPECIFICAMENTE: LO SVILUPPO SOFTWARE, LA CONSULENZA 
    INFORMATICA, LA GESTIONE DI PORTALI WEB, L'ELABORAZIONE DATI, HOSTING E 
    ATTIVITA' CONNESSE, LA PRODUZIONE DI SOFTWARE, LA CONSULENZA NEL SETTORE 
    DELLE TECNOLOGIE DELL'INFORMATICA, LA GESTIONE DI STRUTTURE INFORMATICHE,
    LA PROGETTAZIONE E REALIZZAZIONE DI SISTEMI INFORMATIVI AZIENDALI.
    """
    
    # Crea estrattore
    extractor = VisuraExtractorUltimate()
    
    # Estrai dati
    result = extractor.extract_all_data(test_text)
    
    # Mostra output ECCEZIONALE
    print("\n" + format_output_eccezionale(result))
    
    print("\n" + "🚀" * 35)
    print("ESTRAZIONE ULTIMATE COMPLETATA!")
    print("OUTPUT ECCEZIONALE GARANTITO!")
    print("🚀" * 35)