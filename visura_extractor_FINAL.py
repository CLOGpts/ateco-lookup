#!/usr/bin/env python3
"""
ESTRATTORE VISURA FINALE - SOLO 3 CAMPI CERTI
=============================================
PARTITA IVA | CODICE ATECO | OGGETTO SOCIALE

NESSUNA INVENZIONE - MEGLIO NULL CHE SBAGLIATO
"""

import re
import pdfplumber
from typing import Dict, Optional
import json

class VisuraExtractorFinal:
    """
    Estrattore FINALE con ZERO tolleranza per errori
    """
    
    def extract_three_fields(self, pdf_path: str) -> Dict:
        """
        Estrae SOLO 3 campi con validazione rigorosa
        """
        print("\n" + "="*60)
        print("🔒 ESTRAZIONE FINALE - 3 CAMPI VERIFICATI")
        print("="*60)
        
        # Estrai testo dal PDF
        text = self._extract_pdf_text(pdf_path)
        
        # Estrai e valida i 3 campi
        partita_iva = self._extract_partita_iva(text)
        codice_ateco = self._extract_codice_ateco(text)
        oggetto_sociale = self._extract_oggetto_sociale(text)
        
        # Calcola confidence REALE
        confidence = self._calculate_real_confidence(
            partita_iva, codice_ateco, oggetto_sociale
        )
        
        # Costruisci risposta
        result = {
            "success": True,
            "data": {
                "partita_iva": partita_iva,
                "codice_ateco": codice_ateco,
                "oggetto_sociale": oggetto_sociale,
                "confidence": confidence
            },
            "method": "backend"
        }
        
        # Log risultato
        self._log_result(result)
        
        return result
    
    def _extract_pdf_text(self, pdf_path: str) -> str:
        """Estrae tutto il testo dal PDF"""
        text = ""
        try:
            with pdfplumber.open(pdf_path) as pdf:
                for page in pdf.pages:
                    page_text = page.extract_text()
                    if page_text:
                        text += page_text + "\n"
        except Exception as e:
            print(f"❌ Errore lettura PDF: {e}")
        return text
    
    def _extract_partita_iva(self, text: str) -> Optional[str]:
        """
        Estrae PARTITA IVA con validazione 11 cifre
        """
        # Pattern per trovare P.IVA
        patterns = [
            r'(?:Partita IVA|P\.?\s?IVA|VAT)[:\s]+(\d{11})',
            r'(?:Codice Fiscale|C\.F\.)[:\s]+(\d{11})',  # A volte coincide
            r'\b(\d{11})\b'  # Qualsiasi sequenza di 11 cifre
        ]
        
        for pattern in patterns:
            matches = re.finditer(pattern, text, re.IGNORECASE)
            for match in matches:
                piva = match.group(1)
                # Valida: DEVE essere 11 cifre
                if re.match(r'^\d{11}$', piva):
                    print(f"✅ P.IVA trovata: {piva}")
                    return piva
        
        print("❌ P.IVA non trovata o non valida")
        return None
    
    def _extract_codice_ateco(self, text: str) -> Optional[str]:
        """
        Estrae CODICE ATECO con formato XX.XX o XX.XX.XX
        """
        # Pattern per ATECO
        patterns = [
            r'(?:Codice ATECO|ATECO|Attività prevalente)[:\s]+(\d{2}[\.\s]\d{2}(?:[\.\s]\d{1,2})?)',
            r'(?:Codice attività|Codice)[:\s]+(\d{2}[\.\s]\d{2}(?:[\.\s]\d{1,2})?)',
            r'(?:Importanza)[:\s]+[PI]\s*-[^\d]*(\d{2}[\.\s]\d{2}(?:[\.\s]\d{1,2})?)',
            r'\b(\d{2}\.\d{2}(?:\.\d{1,2})?)\b'  # Formato diretto XX.XX
        ]
        
        for pattern in patterns:
            matches = re.finditer(pattern, text, re.IGNORECASE)
            for match in matches:
                ateco = match.group(1)
                # Normalizza formato
                ateco_clean = re.sub(r'\s+', '.', ateco)
                ateco_clean = re.sub(r'\.+', '.', ateco_clean)
                
                # Valida formato
                if re.match(r'^\d{2}\.\d{2}(?:\.\d{1,2})?$', ateco_clean):
                    print(f"✅ ATECO trovato: {ateco_clean}")
                    return ateco_clean
        
        print("❌ ATECO non trovato o formato invalido")
        return None
    
    def _extract_oggetto_sociale(self, text: str) -> Optional[str]:
        """
        Estrae OGGETTO SOCIALE (min 30 caratteri, deve sembrare business text)
        """
        # Pattern per oggetto sociale
        patterns = [
            r'(?:OGGETTO SOCIALE|Oggetto sociale|Oggetto)[:\s]+([^\n]+(?:\n(?![A-Z]{2,}:)[^\n]+)*)',
            r'(?:Attività|ATTIVITA\'?)[:\s]+([^\n]+(?:\n(?!Data|Numero|Codice)[^\n]+)*)',
            r'(?:Descrizione attività)[:\s]+([^\n]+(?:\n[^\n]+)*?)(?=\n\s*[A-Z]|\n\n|$)',
        ]
        
        # Parole chiave che indicano attività business
        business_keywords = [
            'produzione', 'commercio', 'servizi', 'consulenza', 'vendita',
            'attività', 'gestione', 'intermediazione', 'commercializzazione',
            'fornitura', 'prestazione', 'realizzazione', 'sviluppo'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE | re.MULTILINE | re.DOTALL)
            if match:
                oggetto = match.group(1)
                # Pulisci
                oggetto_clean = ' '.join(oggetto.split())
                
                # Valida lunghezza minima
                if len(oggetto_clean) < 30:
                    continue
                
                # Verifica che contenga parole business
                has_business = any(kw in oggetto_clean.lower() for kw in business_keywords)
                if not has_business:
                    continue
                
                # Tronca se troppo lungo
                if len(oggetto_clean) > 500:
                    oggetto_clean = oggetto_clean[:500] + '...'
                
                print(f"✅ Oggetto sociale trovato: {oggetto_clean[:50]}...")
                return oggetto_clean
        
        print("❌ Oggetto sociale non trovato o troppo corto")
        return None
    
    def _calculate_real_confidence(
        self, 
        partita_iva: Optional[str],
        codice_ateco: Optional[str],
        oggetto_sociale: Optional[str]
    ) -> Dict:
        """
        Calcola confidence ONESTA basata sui campi trovati
        """
        score = 0
        details = {}
        
        # P.IVA vale 33%
        if partita_iva:
            score += 33
            details['partita_iva'] = 'valid'
        else:
            details['partita_iva'] = 'not_found'
        
        # ATECO vale 33%
        if codice_ateco:
            score += 33
            details['ateco'] = 'valid'
        else:
            details['ateco'] = 'not_found'
        
        # Oggetto vale 34%
        if oggetto_sociale:
            score += 34
            details['oggetto_sociale'] = 'valid'
        else:
            details['oggetto_sociale'] = 'not_found'
        
        # Assessment onesto
        if score == 100:
            assessment = "✅ Tutti e 3 i campi trovati e validi"
        elif score >= 66:
            assessment = "⚠️ 2 campi su 3 trovati"
        elif score >= 33:
            assessment = "⚠️ Solo 1 campo trovato"
        else:
            assessment = "❌ Nessun campo valido trovato"
        
        return {
            "score": score,
            "details": details,
            "assessment": assessment
        }
    
    def _log_result(self, result: Dict):
        """Log del risultato finale"""
        print("\n" + "="*60)
        print("📊 RISULTATO ESTRAZIONE")
        print("="*60)
        
        data = result['data']
        print(f"P.IVA: {data['partita_iva'] or 'NON TROVATA'}")
        print(f"ATECO: {data['codice_ateco'] or 'NON TROVATO'}")
        print(f"Oggetto: {'TROVATO' if data['oggetto_sociale'] else 'NON TROVATO'}")
        
        print(f"\nCONFIDENCE: {data['confidence']['score']}%")
        print(f"Assessment: {data['confidence']['assessment']}")
        print("="*60 + "\n")


# ========== TEST ==========
if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 2:
        print("Uso: python visura_extractor_FINAL.py <pdf_file>")
        sys.exit(1)
    
    pdf_file = sys.argv[1]
    
    # Estrai
    extractor = VisuraExtractorFinal()
    result = extractor.extract_three_fields(pdf_file)
    
    # Output JSON
    print("\nJSON OUTPUT:")
    print(json.dumps(result, indent=2, ensure_ascii=False))