#!/usr/bin/env python3
"""
Estrattore dati da Visure Camerali PDF
Estrae: Codici ATECO, Oggetto Sociale, Sedi, Tipo Business
"""
import re
import time
import logging
from typing import Dict, List, Optional, Tuple
import pdfplumber
from functools import lru_cache

# Configurazione logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class VisuraExtractor:
    """Classe per estrarre dati strutturati da visure camerali PDF"""
    
    def __init__(self):
        # Compila regex una volta sola per performance
        self.patterns = {
            'ateco': re.compile(r'\b\d{2}[\.]\d{2}(?:[\.]\d{1,2})?\b'),
            'cap': re.compile(r'\b\d{5}\b'),
            'piva': re.compile(r'(?:P\.?\s?IVA|Partita IVA|P\.IVA)[:\s]*(\d{11})'),
            'cf': re.compile(r'(?:C\.?\s?F\.?|Codice Fiscale)[:\s]*([A-Z0-9]{16})'),
            'indirizzo': re.compile(
                r'(?:Via|Viale|Piazza|Corso|Largo|Vicolo|V\.le|P\.zza|C\.so)\s+'
                r'[A-Za-zÀ-ú\s\'\-]+(?:\s+n\.?\s*\d+[A-Za-z]*)?'
            ),
        }
        
        # Keywords per identificare tipo business
        self.b2b_keywords = [
            'per terzi', 'alle imprese', 'consulenza', 'servizi professionali',
            'ingrosso', 'industriale', 'produzione', 'fornitura', 'appalti',
            'business', 'aziende', 'società', 'enti', 'pubblica amministrazione'
        ]
        
        self.b2c_keywords = [
            'al dettaglio', 'consumatori', 'retail', 'negozio', 'e-commerce',
            'vendita diretta', 'pubblico', 'privati', 'clienti finali',
            'bar', 'ristorante', 'pizzeria', 'parrucchiere', 'estetista'
        ]
    
    def extract_from_pdf(self, pdf_path: str) -> Dict:
        """
        Estrae tutti i dati rilevanti dal PDF della visura
        
        Args:
            pdf_path: Path del file PDF da processare
            
        Returns:
            Dict con i dati estratti o errore
        """
        start_time = time.time()
        
        try:
            with pdfplumber.open(pdf_path) as pdf:
                # Unisci tutto il testo del PDF
                full_text = ""
                for page_num, page in enumerate(pdf.pages, 1):
                    text = page.extract_text()
                    if text:
                        full_text += f"\n--- PAGINA {page_num} ---\n"
                        full_text += text
                
                if not full_text.strip():
                    return self._error_response("PDF_VUOTO", "Il PDF non contiene testo estraibile")
                
                # Log per debug
                logger.info(f"Estratto {len(full_text)} caratteri da {len(pdf.pages)} pagine")
                
                # Estrai tutti i dati
                codici_ateco = self.extract_ateco(full_text)
                oggetto_sociale = self.extract_oggetto_sociale(full_text)
                sedi = self.extract_sedi(full_text)
                tipo_business = self.infer_business_type(full_text, oggetto_sociale)
                
                # Calcola confidence score
                confidence = self._calculate_confidence(
                    codici_ateco, oggetto_sociale, sedi
                )
                
                # Prepara risposta
                result = {
                    'success': True,
                    'data': {
                        'codici_ateco': codici_ateco,
                        'oggetto_sociale': oggetto_sociale,
                        'sedi': sedi,
                        'tipo_business': tipo_business,
                        'confidence': confidence
                    },
                    'extraction_method': 'regex',
                    'processing_time_ms': int((time.time() - start_time) * 1000),
                    'pages_processed': len(pdf.pages)
                }
                
                # Se confidence troppo bassa, suggerisci controllo manuale
                if confidence < 0.5:
                    result['warning'] = "Confidence bassa, verificare manualmente i dati estratti"
                
                return result
                
        except Exception as e:
            logger.error(f"Errore durante estrazione: {str(e)}")
            return self._error_response("EXTRACTION_ERROR", str(e))
    
    def extract_ateco(self, text: str) -> List[str]:
        """
        Estrae tutti i codici ATECO dal testo
        
        Pattern: XX.XX.XX o XX.XX.X o XX.XX
        """
        codici = []
        
        # Cerca nelle sezioni tipiche
        sections = [
            r'ATTIVIT[AÀ][\s\S]{0,500}',
            r'CODICE ATECO[\s\S]{0,200}',
            r'CODICI? ATTIVIT[AÀ][\s\S]{0,200}',
            r'CLASSIFICAZIONE ATTIVIT[AÀ][\s\S]{0,200}'
        ]
        
        for section_pattern in sections:
            matches = re.finditer(section_pattern, text, re.IGNORECASE)
            for match in matches:
                section_text = match.group()
                ateco_matches = self.patterns['ateco'].findall(section_text)
                codici.extend(ateco_matches)
        
        # Cerca anche nel testo completo se non trovati
        if not codici:
            codici = self.patterns['ateco'].findall(text)
        
        # Rimuovi duplicati mantenendo l'ordine
        seen = set()
        unique_codici = []
        for code in codici:
            if code not in seen:
                seen.add(code)
                unique_codici.append(code)
        
        logger.info(f"Trovati {len(unique_codici)} codici ATECO: {unique_codici}")
        return unique_codici
    
    def extract_oggetto_sociale(self, text: str) -> str:
        """
        Estrae l'oggetto sociale / descrizione attività
        """
        oggetto = ""
        
        # Pattern per trovare la sezione oggetto sociale
        patterns = [
            r'OGGETTO SOCIALE[:\s]*([^\n]{20,}(?:\n[^\n]+)*?)(?=\n\s*(?:CAPITALE|DURATA|SISTEMA|POTERI|$))',
            r'OGGETTO[:\s]*([^\n]{20,}(?:\n[^\n]+)*?)(?=\n\s*(?:CAPITALE|DURATA|SISTEMA|POTERI|$))',
            r'ATTIVIT[AÀ] ESERCITATA[:\s]*([^\n]{20,}(?:\n[^\n]+)*?)(?=\n\s*(?:CODICE|CAPITALE|DURATA|$))',
            r'ATTIVIT[AÀ][:\s]*([^\n]{20,}(?:\n[^\n]+)*?)(?=\n\s*(?:CODICE|CAPITALE|DURATA|$))'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE | re.MULTILINE)
            if match:
                oggetto = match.group(1)
                break
        
        # Pulizia testo
        if oggetto:
            # Rimuovi spazi multipli e newline
            oggetto = re.sub(r'\s+', ' ', oggetto)
            # Rimuovi caratteri speciali non necessari
            oggetto = oggetto.strip(' .-;')
            # Limita lunghezza
            if len(oggetto) > 1000:
                oggetto = oggetto[:997] + "..."
        
        logger.info(f"Estratto oggetto sociale di {len(oggetto)} caratteri")
        return oggetto
    
    def extract_sedi(self, text: str) -> Dict:
        """
        Estrae sede legale e unità locali
        """
        sedi = {
            'sede_legale': None,
            'unita_locali': []
        }
        
        # Estrai sede legale
        sede_patterns = [
            r'SEDE LEGALE[:\s]*([^\n]+(?:\n[^\n]+){0,3})',
            r'SEDE[:\s]*([^\n]+(?:\n[^\n]+){0,3})',
            r'INDIRIZZO SEDE[:\s]*([^\n]+(?:\n[^\n]+){0,3})'
        ]
        
        for pattern in sede_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                sede_text = match.group(1)
                sede_info = self._parse_indirizzo(sede_text)
                if sede_info:
                    sedi['sede_legale'] = sede_info
                    break
        
        # Estrai unità locali
        ul_pattern = r'UNIT[AÀ] LOCAL[IE][\s\S]{0,2000}'
        ul_match = re.search(ul_pattern, text, re.IGNORECASE)
        
        if ul_match:
            ul_text = ul_match.group()
            # Cerca tutti gli indirizzi nella sezione UL
            indirizzi = self.patterns['indirizzo'].findall(ul_text)
            caps = self.patterns['cap'].findall(ul_text)
            
            # Associa indirizzi e CAP
            for i, indirizzo in enumerate(indirizzi[:5]):  # Max 5 UL
                ul_info = self._parse_indirizzo(indirizzo)
                if ul_info:
                    # Prova ad associare il CAP
                    if i < len(caps):
                        ul_info['cap'] = caps[i]
                    sedi['unita_locali'].append(ul_info)
        
        logger.info(f"Trovata sede legale: {sedi['sede_legale'] is not None}")
        logger.info(f"Trovate {len(sedi['unita_locali'])} unità locali")
        
        return sedi
    
    def _parse_indirizzo(self, text: str) -> Optional[Dict]:
        """
        Parser helper per indirizzi
        """
        if not text:
            return None
        
        # Pulisci il testo
        text = re.sub(r'\s+', ' ', text).strip()
        
        # Cerca componenti
        result = {
            'indirizzo': '',
            'cap': '',
            'citta': '',
            'provincia': ''
        }
        
        # Estrai indirizzo via/piazza
        via_match = self.patterns['indirizzo'].search(text)
        if via_match:
            result['indirizzo'] = via_match.group().strip()
        
        # Estrai CAP
        cap_match = self.patterns['cap'].search(text)
        if cap_match:
            result['cap'] = cap_match.group()
        
        # Estrai città e provincia (pattern: CITTÀ (PR))
        citta_pattern = r'([A-Z][A-Za-zÀ-ú\s\'\-]+)\s*\(([A-Z]{2})\)'
        citta_match = re.search(citta_pattern, text)
        if citta_match:
            result['citta'] = citta_match.group(1).strip()
            result['provincia'] = citta_match.group(2)
        
        # Se abbiamo almeno indirizzo o città, ritorna il risultato
        if result['indirizzo'] or result['citta']:
            return result
        
        return None
    
    def infer_business_type(self, text: str, oggetto_sociale: str) -> str:
        """
        Inferisce il tipo di business (B2B, B2C, B2B/B2C)
        basandosi su keywords nell'oggetto sociale e nel testo completo
        """
        # Combina testo da analizzare
        text_to_analyze = (oggetto_sociale + " " + text[:2000]).lower()
        
        # Conta keywords
        b2b_score = sum(1 for keyword in self.b2b_keywords if keyword in text_to_analyze)
        b2c_score = sum(1 for keyword in self.b2c_keywords if keyword in text_to_analyze)
        
        # Cerca anche codici ATECO tipici
        ateco_codes = self.patterns['ateco'].findall(text)
        for code in ateco_codes:
            # Commercio al dettaglio (47.*)
            if code.startswith('47.'):
                b2c_score += 2
            # Servizi professionali (62.*, 63.*, 70.*, 71.*)
            elif code.startswith(('62.', '63.', '70.', '71.')):
                b2b_score += 2
            # Produzione/Industria (10-33)
            elif any(code.startswith(f'{i}.') for i in range(10, 34)):
                b2b_score += 1
            # Alloggio e ristorazione (55.*, 56.*)
            elif code.startswith(('55.', '56.')):
                b2c_score += 2
        
        logger.info(f"Business type scores - B2B: {b2b_score}, B2C: {b2c_score}")
        
        # Determina tipo
        if b2b_score > 0 and b2c_score > 0:
            return "B2B/B2C"
        elif b2b_score > b2c_score:
            return "B2B"
        elif b2c_score > b2b_score:
            return "B2C"
        else:
            # Default basato su alcuni indizi aggiuntivi
            if 'consumator' in text_to_analyze or 'cliente' in text_to_analyze:
                return "B2C"
            elif 'impres' in text_to_analyze or 'aziend' in text_to_analyze:
                return "B2B"
            else:
                return "B2B/B2C"  # Non determinabile
    
    def _calculate_confidence(self, ateco: List, oggetto: str, sedi: Dict) -> float:
        """
        Calcola un punteggio di confidence basato sui dati estratti
        """
        score = 0.0
        
        # ATECO trovati (40% del peso)
        if ateco:
            score += 0.4
        
        # Oggetto sociale trovato (30% del peso)
        if oggetto and len(oggetto) > 50:
            score += 0.3
        elif oggetto:
            score += 0.15
        
        # Sede legale trovata (20% del peso)
        if sedi.get('sede_legale'):
            score += 0.2
        
        # Unità locali trovate (10% del peso)
        if sedi.get('unita_locali'):
            score += 0.1
        
        return round(score, 2)
    
    def _error_response(self, code: str, message: str) -> Dict:
        """Helper per creare risposte di errore consistenti"""
        return {
            'success': False,
            'error': {
                'code': code,
                'message': message,
                'details': 'Verifica che il file sia una visura camerale valida'
            }
        }

# Funzione di utilità per test standalone
if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        pdf_file = sys.argv[1]
        extractor = VisuraExtractor()
        result = extractor.extract_from_pdf(pdf_file)
        
        import json
        print(json.dumps(result, indent=2, ensure_ascii=False))
    else:
        print("Uso: python visura_extractor.py <file.pdf>")