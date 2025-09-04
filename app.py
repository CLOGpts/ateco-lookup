#!/usr/bin/env python3
"""
FIX BACKEND VISURA - INTEGRAZIONE SISTEMA STRICT
================================================
Questo file va integrato nel backend su Render per fixare l'errore 500
"""

from flask import Flask, request, jsonify
from flask_cors import CORS
import pdfplumber
import re
import os
from typing import Dict, Optional
import traceback

app = Flask(__name__)
CORS(app)

class VisuraExtractorStrict:
    """
    Estrattore STRICT - Solo 3 campi fondamentali
    """
    
    def extract_three_fields(self, pdf_path: str) -> Dict:
        """
        Estrae SOLO Partita IVA, Codice ATECO, Oggetto Sociale
        """
        try:
            # Estrai testo dal PDF
            text = self._extract_pdf_text(pdf_path)
            
            # Estrai i 3 campi fondamentali
            partita_iva = self._extract_partita_iva(text)
            codice_ateco = self._extract_codice_ateco(text)
            oggetto_sociale = self._extract_oggetto_sociale(text)
            
            # Calcola confidence REALE (0, 33, 66, 100)
            confidence = self._calculate_real_confidence(
                partita_iva, codice_ateco, oggetto_sociale
            )
            
            # Costruisci risposta compatibile con frontend
            result = {
                "success": True,
                "denominazione": "ESTRATTA DA VISURA",  # Placeholder per compatibilità
                "partita_iva": partita_iva,
                "codici_ateco": [],
                "oggetto_sociale": oggetto_sociale,
                "confidence": confidence['score'] / 100,  # Converti in decimale
                "extraction_method": "backend",
                "sede_legale": {
                    "comune": "N/D",
                    "provincia": "N/D",
                    "cap": "N/D"
                }
            }
            
            # Aggiungi ATECO se trovato
            if codice_ateco:
                result["codici_ateco"] = [{
                    "codice": codice_ateco,
                    "descrizione": self._get_ateco_description(codice_ateco),
                    "principale": True
                }]
            
            return result
            
        except Exception as e:
            print(f"❌ Errore estrazione: {e}")
            traceback.print_exc()
            return {
                "success": False,
                "error": str(e)
            }
    
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
        Estrae PARTITA IVA con validazione rigorosa (11 cifre)
        """
        patterns = [
            r'(?:Partita IVA|P\.?\s?IVA|VAT)[\s:]+(\d{11})',
            r'(?:Codice Fiscale|C\.F\.)[\s:]+(\d{11})',
            r'\b(\d{11})\b'
        ]
        
        for pattern in patterns:
            matches = re.finditer(pattern, text, re.IGNORECASE)
            for match in matches:
                piva = match.group(1)
                if re.match(r'^\d{11}$', piva):
                    return piva
        
        return None
    
    def _extract_codice_ateco(self, text: str) -> Optional[str]:
        """
        Estrae CODICE ATECO con validazione formato XX.XX
        """
        patterns = [
            r'(?:Codice ATECO|ATECO|Attività prevalente)[\s:]+(\d{2}[.\s]\d{2}(?:[.\s]\d{1,2})?)',
            r'(?:Codice attività|Codice)[\s:]+(\d{2}[.\s]\d{2}(?:[.\s]\d{1,2})?)',
            r'(?:Importanza)[\s:]+[PI]\s*-[^\d]*(\d{2}[.\s]\d{2}(?:[.\s]\d{1,2})?)',
            r'\b(\d{2}\.\d{2}(?:\.\d{1,2})?)\b'
        ]
        
        for pattern in patterns:
            matches = re.finditer(pattern, text, re.IGNORECASE)
            for match in matches:
                ateco = match.group(1)
                # Normalizza formato
                ateco_clean = re.sub(r'\s+', '.', ateco)
                ateco_clean = re.sub(r'\.+', '.', ateco_clean)
                
                # Valida formato e escludi anni (19.xx, 20.xx, 21.xx)
                if re.match(r'^\d{2}\.\d{2}(?:\.\d{1,2})?$', ateco_clean):
                    first_part = int(ateco_clean.split('.')[0])
                    # Escludi range che potrebbero essere anni
                    if first_part not in [19, 20, 21]:
                        return ateco_clean
        
        return None
    
    def _extract_oggetto_sociale(self, text: str) -> Optional[str]:
        """
        Estrae OGGETTO SOCIALE (min 30 caratteri)
        """
        patterns = [
            r'(?:OGGETTO SOCIALE|Oggetto sociale|Oggetto)[\s:]+([^\n]+(?:\n(?![A-Z]{2,}:)[^\n]+)*)',
            r'(?:Attività|ATTIVITA\'?)[\s:]+([^\n]+(?:\n(?!Data|Numero|Codice)[^\n]+)*)',
            r'(?:Descrizione attività)[\s:]+([^\n]+(?:\n[^\n]+)*?)(?=\n\s*[A-Z]|\n\n|$)',
        ]
        
        business_keywords = [
            'produzione', 'commercio', 'servizi', 'consulenza', 'vendita',
            'attività', 'gestione', 'intermediazione', 'commercializzazione',
            'fornitura', 'prestazione', 'realizzazione', 'sviluppo'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE | re.MULTILINE | re.DOTALL)
            if match:
                oggetto = match.group(1)
                oggetto_clean = ' '.join(oggetto.split())
                
                # Valida lunghezza e contenuto
                if len(oggetto_clean) >= 30:
                    has_business = any(kw in oggetto_clean.lower() for kw in business_keywords)
                    if has_business:
                        # Tronca se troppo lungo
                        if len(oggetto_clean) > 500:
                            oggetto_clean = oggetto_clean[:500] + '...'
                        return oggetto_clean
        
        return None
    
    def _calculate_real_confidence(self, piva, ateco, oggetto) -> Dict:
        """
        Calcola confidence ONESTA (0, 33, 66, 100)
        """
        score = 0
        details = {}
        
        if piva:
            score += 33
            details['partita_iva'] = 'valid'
        else:
            details['partita_iva'] = 'not_found'
        
        if ateco:
            score += 33
            details['ateco'] = 'valid'
        else:
            details['ateco'] = 'not_found'
        
        if oggetto:
            score += 34
            details['oggetto_sociale'] = 'valid'
        else:
            details['oggetto_sociale'] = 'not_found'
        
        # Assessment
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
    
    def _get_ateco_description(self, codice: str) -> str:
        """
        Mappa descrizioni ATECO comuni
        """
        ateco_map = {
            "62.01": "Produzione di software",
            "62.02": "Consulenza informatica",
            "62.03": "Gestione di strutture informatizzate",
            "62.09": "Altre attività dei servizi connessi alle tecnologie dell'informatica",
            "47.91": "Commercio al dettaglio per corrispondenza o Internet",
            "46.51": "Commercio all'ingrosso di computer e software",
            "70.22": "Consulenza imprenditoriale e gestionale"
        }
        return ateco_map.get(codice, "Attività economica")


@app.route('/api/extract-visura', methods=['POST'])
def extract_visura():
    """
    Endpoint per estrazione visura con sistema STRICT
    """
    try:
        # Verifica che ci sia un file
        if 'file' not in request.files:
            return jsonify({"success": False, "error": "Nessun file fornito"}), 400
        
        file = request.files['file']
        
        # Salva temporaneamente il file
        temp_path = f"/tmp/{file.filename}"
        file.save(temp_path)
        
        # Estrai con sistema STRICT
        extractor = VisuraExtractorStrict()
        result = extractor.extract_three_fields(temp_path)
        
        # Rimuovi file temporaneo
        try:
            os.remove(temp_path)
        except:
            pass
        
        # Ritorna risultato
        if result.get('success'):
            return jsonify(result), 200
        else:
            return jsonify(result), 500
            
    except Exception as e:
        print(f"❌ ERRORE ENDPOINT: {e}")
        traceback.print_exc()
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@app.route('/health', methods=['GET'])
def health():
    """Health check endpoint"""
    return jsonify({"status": "healthy", "version": "STRICT-1.0"}), 200


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=True)