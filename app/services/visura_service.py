"""
Visura Service - Business logic for extracting data from Visura PDF files.

Extracted from main.py for modular architecture.
Handles PDF text extraction, field parsing (P.IVA, ATECO, etc.), and confidence scoring.
"""
import os
import re
import json
import logging
import tempfile
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple, Callable
import pandas as pd

logger = logging.getLogger(__name__)


class VisuraService:
    """
    Service for Visura PDF extraction operations.

    Handles:
    - Conditional import of multiple Visura extractors (Final, Fixed, Power)
    - PDF text extraction with retry and fallback (pdfplumber → PyPDF2 → Tesseract)
    - Field parsing: P.IVA, ATECO, Oggetto Sociale, Sede Legale, Denominazione, Forma Giuridica
    - Confidence scoring based on extracted fields
    """

    def __init__(
        self,
        ateco_df: Optional[pd.DataFrame] = None,
        search_smart_fn: Optional[Callable] = None,
        normalize_code_fn: Optional[Callable] = None
    ):
        """
        Initialize Visura service.

        Args:
            ateco_df: DataFrame with ATECO codes (for conversion 2022→2025)
            search_smart_fn: Function to search ATECO codes in DataFrame
            normalize_code_fn: Function to normalize ATECO codes
        """
        self.ateco_df = ateco_df
        self.search_smart_fn = search_smart_fn
        self.normalize_code_fn = normalize_code_fn

        # Import Visura extractors (conditional, with fallback)
        self.visura_extraction_available = False
        self.visura_final_available = False
        self.visura_fixed_available = False
        self.visura_power_available = False
        self.visura_available = False

        self.VisuraExtractorFinal = None
        self.VisuraExtractorFixed = None
        self.VisuraExtractorPower = None
        self.VisuraExtractor = None

        self._load_extractors()
        logger.info(f"VisuraService initialized. Extraction available: {self.visura_extraction_available}")

    def _load_extractors(self):
        """
        Load Visura extractors with priority order: Final → Fixed → Power → Base.

        Priority 0: VisuraExtractorFinal (STRICT - only 3 fields)
        Priority 1: VisuraExtractorFixed (corrected version)
        Priority 2: VisuraExtractorPower (fallback)
        Priority 3: Base module removed (no longer needed)
        """
        # PRIORITY 0: Try FINAL (STRICT version - ONLY 3 FIELDS)
        try:
            from visura_extractor_FINAL_embedded import VisuraExtractorFinal
            self.VisuraExtractorFinal = VisuraExtractorFinal
            self.visura_final_available = True
            self.visura_extraction_available = True
            logger.info("✅ VisuraExtractorFinal imported - STRICT VERSION (ONLY 3 FIELDS)")
        except ImportError as e:
            logger.warning(f"VisuraExtractorFinal not available: {e}")
        except Exception as e:
            logger.error(f"Error importing VisuraExtractorFinal: {e}")

        # PRIORITY 1: Try FIXED (corrected version)
        try:
            from visura_extractor_fixed import VisuraExtractorFixed
            self.VisuraExtractorFixed = VisuraExtractorFixed
            self.visura_fixed_available = True
            self.visura_extraction_available = True
            logger.info("✅ VisuraExtractorFixed imported - CORRECTED VERSION")
        except ImportError as e:
            logger.warning(f"VisuraExtractorFixed not available: {e}")
        except Exception as e:
            logger.error(f"Error importing VisuraExtractorFixed: {e}")

        # PRIORITY 2: Fallback on POWER
        try:
            from visura_extractor_power import VisuraExtractorPower
            self.VisuraExtractorPower = VisuraExtractorPower
            self.visura_power_available = True
            if not self.visura_extraction_available:
                self.visura_extraction_available = True
            logger.info("✅ VisuraExtractorPower imported as fallback")
        except ImportError as e:
            logger.warning(f"VisuraExtractorPower not available: {e}")
        except Exception as e:
            logger.error(f"Error importing VisuraExtractorPower: {e}")

        # PRIORITY 3: Base module removed - no longer needed
        self.visura_available = False
        self.VisuraExtractor = None

        # Log final status
        if not self.visura_extraction_available:
            logger.error("❌ NO Visura extractor available!")
        else:
            available = []
            if self.visura_fixed_available:
                available.append("Fixed")
            if self.visura_power_available:
                available.append("Power")
            if self.visura_available:
                available.append("Base")
            logger.info(f"📊 Available extractors: {', '.join(available)}")

    def get_test_data(self) -> Dict[str, Any]:
        """
        Get test data for API health check.

        Returns:
            Dict with test visura data
        """
        return {
            "success": True,
            "message": f"API working! VisuraExtractorPower available: {self.VisuraExtractorPower is not None}",
            "data": {
                "denominazione": "TEST CELERYA SRL",
                "partita_iva": "12345678901",
                "pec": "test@pec.it",
                "codici_ateco": [
                    {"codice": "62.01", "descrizione": "Software production", "principale": True}
                ],
                "sede_legale": {
                    "comune": "Torino",
                    "provincia": "TO"
                },
                "confidence": 0.99
            }
        }

    def extract_from_pdf(self, file_content: bytes, filename: str) -> Dict[str, Any]:
        """
        Extract data from Visura PDF.

        Extracts ONLY 3 STRICT fields from visura PDF:
        - P.IVA (11 digits)
        - ATECO code (with 2022→2025 conversion)
        - Oggetto Sociale (business description)

        Also extracts optional fields:
        - Sede Legale (comune + provincia)
        - Denominazione (company name)
        - Forma Giuridica (legal form)

        Args:
            file_content: PDF file content as bytes
            filename: Original filename for logging

        Returns:
            Dict with extraction result and confidence score
        """
        logger.info(f"📄 Received file: {filename}")

        # Initialize empty result
        result = {
            'success': True,
            'data': {
                'partita_iva': None,
                'codice_ateco': None,
                'oggetto_sociale': None,
                'codici_ateco': [],
                'confidence': {
                    'score': 0,
                    'details': {}
                }
            },
            'method': 'backend'
        }

        # ROBUST EXTRACTION WITH TOTAL ERROR HANDLING
        tmp_path = None
        try:
            # 1. SAVE TEMPORARY FILE
            with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as tmp:
                if not file_content:
                    logger.warning("Empty file")
                    return result
                tmp.write(file_content)
                tmp_path = tmp.name
                logger.info(f"File saved: {tmp_path} ({len(file_content)} bytes)")

            # 2. EXTRACT TEXT FROM PDF (with retry and multiple fallbacks)
            text = self._extract_text_from_pdf(tmp_path)
            if not text:
                logger.error("❌ ALL PDF extraction methods failed after retry")
                return result

            # 3. NORMALIZE TEXT (remove extra spaces/newlines for robust matching)
            text_normalized = re.sub(r'\s+', ' ', text)
            logger.info(f"📝 Extracted text: {len(text)} chars, normalized: {len(text_normalized)} chars")

            # 🔍 DEBUG: Print first 2000 characters for pattern analysis
            logger.info("=" * 80)
            logger.info("🔍 DEBUG EXTRACTED TEXT (first 2000 chars):")
            logger.info(text[:2000])
            logger.info("=" * 80)

            # 4. EXTRACT THE 3 STRICT FIELDS + OPTIONAL FIELDS
            partita_iva = self._extract_partita_iva(text_normalized)
            codice_ateco = self._extract_ateco_code(text_normalized)
            oggetto_sociale = self._extract_oggetto_sociale(text_normalized)
            sede_legale = self._extract_sede_legale(text_normalized)
            denominazione = self._extract_denominazione(text_normalized)
            forma_giuridica = self._extract_forma_giuridica(text_normalized)

            # 5. CALCULATE REAL CONFIDENCE
            score, details = self._calculate_confidence(
                partita_iva, codice_ateco, oggetto_sociale,
                sede_legale, denominazione, forma_giuridica
            )

            # 6. BUILD RESULT
            if partita_iva:
                result['data']['partita_iva'] = partita_iva
            if codice_ateco:
                result['data']['codice_ateco'] = codice_ateco
                result['data']['codici_ateco'] = [{
                    'codice': codice_ateco,
                    'descrizione': '',
                    'principale': True
                }]
            if oggetto_sociale:
                result['data']['oggetto_sociale'] = oggetto_sociale
            if sede_legale:
                result['data']['sede_legale'] = sede_legale
            if denominazione:
                result['data']['denominazione'] = denominazione
            if forma_giuridica:
                result['data']['forma_giuridica'] = forma_giuridica

            result['data']['confidence']['score'] = score
            result['data']['confidence']['details'] = details

            logger.info(
                f"📊 Extraction completed: {score}% confidence "
                f"(P.IVA: {bool(partita_iva)}, ATECO: {bool(codice_ateco)}, "
                f"Oggetto: {bool(oggetto_sociale)}, Sede: {bool(sede_legale)}, "
                f"Denom: {bool(denominazione)}, Forma: {bool(forma_giuridica)})"
            )

        except Exception as e:
            logger.error(f"❌ Extraction error: {str(e)}")
            # In case of ANY error, return empty result (no crash)

        finally:
            # Clean up temporary file
            if tmp_path:
                try:
                    os.unlink(tmp_path)
                except FileNotFoundError:
                    pass  # File already deleted, OK
                except Exception as e:
                    logger.warning(f"⚠️ Cannot delete temporary file {tmp_path}: {e}")

        return result

    def _extract_text_from_pdf(self, pdf_path: str) -> str:
        """
        Extract text from PDF with retry and fallback.

        Order: pdfplumber → PyPDF2 → Tesseract OCR
        Each method gets 2 retries before moving to next.

        Args:
            pdf_path: Path to PDF file

        Returns:
            Extracted text or empty string if all methods fail
        """
        max_retries = 2

        def extract_with_retry(extractor_fn: Callable, name: str, retries: int = max_retries) -> Optional[str]:
            """Helper function to extract with retry."""
            for attempt in range(1, retries + 1):
                try:
                    logger.info(f"🔄 Attempt {attempt}/{retries} with {name}")
                    result = extractor_fn()
                    if result:
                        logger.info(f"✅ {name} succeeded at attempt {attempt}")
                        return result
                except Exception as e:
                    if attempt < retries:
                        logger.warning(f"⚠️ {name} failed (attempt {attempt}): {e}, retrying...")
                        import time
                        time.sleep(0.5)  # Brief pause before retry
                    else:
                        logger.error(f"❌ {name} failed after {retries} attempts: {e}")
            return None

        # Try pdfplumber (with retry)
        def try_pdfplumber() -> Optional[str]:
            import pdfplumber
            text_result = ""
            with pdfplumber.open(pdf_path) as pdf:
                for page in pdf.pages:
                    page_text = page.extract_text()
                    if page_text:
                        text_result += page_text + "\n"
            return text_result if text_result else None

        text = extract_with_retry(try_pdfplumber, "pdfplumber")

        # Fallback on PyPDF2 if pdfplumber failed
        if not text:
            logger.warning("pdfplumber failed, trying PyPDF2...")

            def try_pypdf2() -> Optional[str]:
                import PyPDF2
                text_result = ""
                with open(pdf_path, 'rb') as pdf_file:
                    pdf_reader = PyPDF2.PdfReader(pdf_file)
                    for page in pdf_reader.pages:
                        page_text = page.extract_text()
                        if page_text:
                            text_result += page_text + "\n"
                return text_result if text_result else None

            text = extract_with_retry(try_pypdf2, "PyPDF2")

        # Fallback on Tesseract OCR if both failed (scanned PDF)
        if not text:
            logger.warning("pdfplumber and PyPDF2 failed, trying Tesseract OCR (scanned PDF)...")

            def try_tesseract_ocr() -> Optional[str]:
                """
                Extract text from scanned PDF using Tesseract OCR.

                Process:
                1. Convert PDF to images
                2. Apply OCR on each image
                3. Concatenate all extracted text
                """
                try:
                    from pdf2image import convert_from_path
                    import pytesseract

                    # Convert PDF to images (DPI 300 for OCR quality)
                    images = convert_from_path(pdf_path, dpi=300)

                    if not images:
                        logger.warning("⚠️ No images extracted from PDF")
                        return None

                    text_result = ""
                    for i, image in enumerate(images, 1):
                        logger.info(f"🔍 OCR on page {i}/{len(images)}...")
                        # Extract text with Tesseract (Italian + English)
                        page_text = pytesseract.image_to_string(image, lang='ita+eng')
                        if page_text:
                            text_result += page_text + "\n"

                    return text_result if text_result.strip() else None

                except ImportError as e:
                    logger.error(f"❌ Tesseract not installed: {e}")
                    return None
                except Exception as e:
                    logger.error(f"❌ OCR error: {e}")
                    return None

            text = extract_with_retry(try_tesseract_ocr, "Tesseract OCR")

        return text or ""

    def _extract_partita_iva(self, text: str) -> Optional[str]:
        """
        Extract P.IVA (11 digits) from text.

        Args:
            text: Normalized text from PDF

        Returns:
            P.IVA string or None
        """
        piva_patterns = [
            r'(?:Partita IVA|P\.?\s?IVA|VAT)[\s:]+(\d{11})',
            r'(?:Codice Fiscale|C\.F\.)[\s:]+(\d{11})',
            r'\b(\d{11})\b'
        ]
        for pattern in piva_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                piva = match.group(1)
                if re.match(r'^\d{11}$', piva):
                    logger.info(f"✅ P.IVA found: {piva}")
                    return piva
        return None

    def _extract_ateco_code(self, text: str) -> Optional[str]:
        """
        Extract ATECO code from text.

        Extracts 2022 or 2025 format, then converts to 2025 using database.
        IMPORTANT: Search first 6 digits (more specific), then 4 digits (less specific).
        NOTE: Last part can be 1-2 digits (eg: 64.99.1 or 64.99.10).

        Args:
            text: Normalized text from PDF

        Returns:
            ATECO 2025 code or None
        """
        ateco_patterns = [
            # ========== ATECO 2025 (5-6 digits: XX.XX.X or XX.XX.XX) - MAX PRIORITY ==========
            # Pattern with explicit label + 5-6 digits (eg: "Codice ATECO 64.99.1")
            r'(?:Codice ATECO|ATECO|Attività prevalente|Codice attività)[\s:]+(\d{2}[\s.]\d{2}[\s.]\d{1,2})',
            # Generic pattern 5-6 digits with "Codice:" label (eg: "Codice: 64.99.1")
            r'Codice[\s:]+(\d{2}\.?\d{2}\.?\d{1,2})\s*-',
            # Generic pattern 5-6 digits (capture even without label, BUT only if not a date)
            # Negative lookahead to exclude dates like 27.06.2022
            r'\b(\d{2}\.\d{2}\.\d{1,2})(?!\d)\b',

            # ========== ATECO 2022 (4 digits: XX.XX) - FALLBACK ==========
            # Pattern with explicit label + 4 digits
            r'(?:Codice ATECO|ATECO|Attività prevalente|Codice attività)[\s:]+(\d{2}[\s.]\d{2})(?!\s*\.\s*\d)',
            # Generic pattern 4 digits (exclude if followed by another .XX)
            r'\b(\d{2}\.\d{2})(?!\s*\.\s*\d)\b'
        ]

        codice_ateco = None
        codice_ateco_raw = None  # Code extracted from PDF (might be 2022)

        for pattern in ateco_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                ateco = match.group(1)
                codice_ateco_raw = re.sub(r'\s+', '.', ateco)

                # Exclude years (19.xx, 20.xx, 21.xx)
                first_part = int(codice_ateco_raw.split('.')[0])
                if first_part in [19, 20, 21]:
                    continue

                logger.info(f"📋 ATECO extracted from PDF: {codice_ateco_raw}")

                # If already 2025 format (5-6 digits: XX.XX.X or XX.XX.XX), use directly
                if re.match(r'^\d{2}\.\d{2}\.\d{1,2}$', codice_ateco_raw):
                    codice_ateco = codice_ateco_raw
                    logger.info(f"✅ ATECO 2025 found directly: {codice_ateco}")
                    break
                # If 2022 format (4 digits: XX.XX), convert using database
                elif re.match(r'^\d{2}\.\d{2}$', codice_ateco_raw):
                    logger.info(f"🔄 ATECO 2022 found: {codice_ateco_raw}, converting to 2025...")
                    codice_ateco = self._convert_ateco_2022_to_2025(codice_ateco_raw)
                    break

        return codice_ateco

    def _convert_ateco_2022_to_2025(self, code_2022: str) -> Optional[str]:
        """
        Convert ATECO 2022 to 2025 using database.

        Args:
            code_2022: ATECO 2022 code (4 digits: XX.XX)

        Returns:
            ATECO 2025 code or None
        """
        if self.ateco_df is None or self.search_smart_fn is None or self.normalize_code_fn is None:
            logger.warning("⚠️ ATECO database or functions not available for conversion")
            return None

        try:
            # Use search_smart function from database to get 2025
            result_df = self.search_smart_fn(self.ateco_df, code_2022, prefer='2025')
            if not result_df.empty:
                row = result_df.iloc[0]
                codice_2025 = row.get('CODICE_ATECO_2025_RAPPRESENTATIVO', '')
                if codice_2025:
                    normalized = self.normalize_code_fn(codice_2025)
                    logger.info(f"✅ Conversion successful: {code_2022} → {normalized}")
                    return normalized
                else:
                    logger.warning(f"⚠️ No 2025 correspondent for {code_2022}")
            else:
                logger.warning(f"⚠️ Code {code_2022} not found in database")
        except Exception as e:
            logger.error(f"❌ ATECO conversion error: {e}")

        return None

    def _extract_oggetto_sociale(self, text: str) -> Optional[str]:
        """
        Extract Oggetto Sociale (min 30 chars with business words).

        NOTE: Captures ALL multiline text (up to 2000 characters).

        Args:
            text: Normalized text from PDF

        Returns:
            Oggetto Sociale string or None
        """
        oggetto_patterns = [
            r'(?:OGGETTO SOCIALE|Oggetto sociale|Oggetto)[\s:]+(.{30,2000})',
            r'(?:Attività|ATTIVITA)[\s:]+(.{30,2000})',
        ]
        business_words = [
            'produzione', 'commercio', 'servizi', 'consulenza',
            'vendita', 'gestione', 'prestazione', 'attività', 'investiment'
        ]

        for pattern in oggetto_patterns:
            match = re.search(pattern, text, re.IGNORECASE | re.DOTALL)
            if match:
                oggetto = match.group(1).strip()
                # Clean multiple newlines and excessive spaces
                oggetto = re.sub(r'\s+', ' ', oggetto)
                if len(oggetto) >= 30:
                    has_business = any(w in oggetto.lower() for w in business_words)
                    if has_business:
                        if len(oggetto) > 2000:
                            oggetto = oggetto[:2000] + '...'
                        logger.info(f"✅ Oggetto found ({len(oggetto)} chars): {oggetto[:80]}...")
                        return oggetto
        return None

    def _extract_sede_legale(self, text: str) -> Optional[Dict[str, str]]:
        """
        Extract Sede Legale (Comune + Provincia) - CRITICAL for seismic zone!

        Args:
            text: Normalized text from PDF

        Returns:
            Dict with 'comune' and 'provincia' or None
        """
        sede_patterns = [
            # Complete pattern with comune and provincia
            r'(?:SEDE LEGALE|Sede legale|Sede)[\s:]+([A-Z][A-Za-z\s]+?)\s*\(([A-Z]{2})\)',
            r'(?:SEDE|Sede)[\s:]+(?:in\s+)?([A-Z][A-Za-z\s]+?)\s*\(([A-Z]{2})\)',
            # Pattern with Via + Comune + Provincia
            r'[Vv]ia\s+[^,]+,\s*([A-Z][A-Za-z\s]+?)\s*\(([A-Z]{2})\)',
            # Generic pattern: Comune (Provincia)
            r'\b([A-Z][A-Za-z\s]{3,30}?)\s*\(([A-Z]{2})\)\b'
        ]

        common_words = [
            'VIA', 'VIALE', 'PIAZZA', 'CORSO', 'STRADA', 'LOCALITÀ',
            'FRAZIONE', 'PRESSO', 'ITALY', 'ITALIA'
        ]

        for pattern in sede_patterns:
            matches = re.finditer(pattern, text)
            for match in matches:
                comune = match.group(1).strip()
                provincia = match.group(2).strip()

                # Validate comune (no common words)
                if comune.upper() not in common_words and len(comune) > 3:
                    # Remove "di" at start (eg: "di TORINO" → "TORINO")
                    if comune.lower().startswith('di '):
                        comune = comune[3:]

                    sede_legale = {
                        'comune': comune.title(),  # First letter uppercase
                        'provincia': provincia.upper()
                    }
                    logger.info(f"✅ Sede legale found: {comune} ({provincia})")
                    return sede_legale

        return None

    def _extract_denominazione(self, text: str) -> Optional[str]:
        """
        Extract Denominazione (Ragione Sociale).

        Args:
            text: Normalized text from PDF

        Returns:
            Denominazione string or None
        """
        denominazione_patterns = [
            # Match until newline, forma giuridica, or other field
            r'(?:Denominazione|DENOMINAZIONE|Ragione sociale|RAGIONE SOCIALE)[\s:]+([A-Z][A-Za-z0-9\s\.\&\'\-]{5,150}?)(?=\s+Forma|$|\n)',
            r'(?:denominazione|ragione sociale)[\s:]+([A-Z][A-Za-z0-9\s\.\&\'\-]{5,150}?)(?=\s+forma|$|\n)',
        ]

        for pattern in denominazione_patterns:
            match = re.search(pattern, text)
            if match:
                denom = match.group(1).strip()
                # Clean and validate
                if 5 <= len(denom) <= 150:
                    logger.info(f"✅ Denominazione found: {denom}")
                    return denom
        return None

    def _extract_forma_giuridica(self, text: str) -> Optional[str]:
        """
        Extract Forma Giuridica (legal form).

        Args:
            text: Normalized text from PDF

        Returns:
            Forma Giuridica string or None
        """
        forma_patterns = [
            r'SOCIETA\' PER AZIONI|S\.P\.A\.|SPA(?=\s|$|,)',
            r'SOCIETA\' A RESPONSABILITA\' LIMITATA|S\.R\.L\.|SRL(?=\s|$|,)',
            r'SOCIETA\' IN ACCOMANDITA SEMPLICE|S\.A\.S\.|SAS(?=\s|$|,)',
            r'SOCIETA\' IN NOME COLLETTIVO|S\.N\.C\.|SNC(?=\s|$|,)',
            r'DITTA INDIVIDUALE|IMPRESA INDIVIDUALE',
        ]

        forma_map = {
            'S.P.A.': 'SOCIETA\' PER AZIONI',
            'SPA': 'SOCIETA\' PER AZIONI',
            'S.R.L.': 'SOCIETA\' A RESPONSABILITA\' LIMITATA',
            'SRL': 'SOCIETA\' A RESPONSABILITA\' LIMITATA',
            'S.A.S.': 'SOCIETA\' IN ACCOMANDITA SEMPLICE',
            'SAS': 'SOCIETA\' IN ACCOMANDITA SEMPLICE',
            'S.N.C.': 'SOCIETA\' IN NOME COLLETTIVO',
            'SNC': 'SOCIETA\' IN NOME COLLETTIVO',
        }

        for pattern in forma_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                forma_raw = match.group(0).upper()
                forma_giuridica = forma_map.get(forma_raw, forma_raw)
                logger.info(f"✅ Forma giuridica found: {forma_giuridica}")
                return forma_giuridica
        return None

    def _calculate_confidence(
        self,
        partita_iva: Optional[str],
        codice_ateco: Optional[str],
        oggetto_sociale: Optional[str],
        sede_legale: Optional[Dict[str, str]],
        denominazione: Optional[str],
        forma_giuridica: Optional[str]
    ) -> Tuple[int, Dict[str, str]]:
        """
        Calculate confidence score based on extracted fields.

        Scoring:
        - P.IVA: 25 points
        - ATECO: 25 points
        - Oggetto Sociale: 15 points
        - Sede Legale: 15 points (important for seismic zone!)
        - Denominazione: 10 points
        - Forma Giuridica: 10 points
        Max: 100 points

        Args:
            partita_iva: Extracted P.IVA
            codice_ateco: Extracted ATECO code
            oggetto_sociale: Extracted Oggetto Sociale
            sede_legale: Extracted Sede Legale
            denominazione: Extracted Denominazione
            forma_giuridica: Extracted Forma Giuridica

        Returns:
            Tuple (score, details_dict)
        """
        score = 0
        details = {}

        if partita_iva:
            score += 25
            details['partita_iva'] = 'valid'
        if codice_ateco:
            score += 25
            details['ateco'] = 'valid'
        if oggetto_sociale:
            score += 15
            details['oggetto_sociale'] = 'valid'
        if sede_legale:
            score += 15  # Very important for seismic zone!
            details['sede_legale'] = 'valid'
        else:
            details['sede_legale'] = 'not_found'
        if denominazione:
            score += 10
            details['denominazione'] = 'valid'
        if forma_giuridica:
            score += 10
            details['forma_giuridica'] = 'valid'

        return min(score, 100), details  # Cap at 100%
