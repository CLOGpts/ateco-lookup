"""
Seismic Zones Service

Handles seismic zone lookups for Italian municipalities (comuni).
Data source: OPCM 3519/2006 - Protezione Civile

Story 2.6: Extract Seismic Zones Service
"""

import json
import logging
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from difflib import get_close_matches, SequenceMatcher
from decimal import Decimal

logger = logging.getLogger(__name__)


class SeismicService:
    """Service for seismic zone lookups and analysis."""

    def __init__(self, db_path: Optional[Path] = None):
        """
        Initialize SeismicService.

        Args:
            db_path: Path to zone_sismiche_comuni.json (defaults to project root)
        """
        self.db_path = db_path or Path(__file__).parent.parent.parent / "zone_sismiche_comuni.json"
        self.db_data: Optional[Dict] = None
        self.zone_descriptions = {
            1: "Zona 1 - Sismicità alta: È la zona più pericolosa, dove possono verificarsi fortissimi terremoti",
            2: "Zona 2 - Sismicità media: Zona dove possono verificarsi forti terremoti",
            3: "Zona 3 - Sismicità bassa: Zona che può essere soggetta a scuotimenti modesti",
            4: "Zona 4 - Sismicità molto bassa: È la zona meno pericolosa"
        }

    def load_seismic_database(self) -> Dict:
        """
        Load seismic zones database from JSON file.

        Returns:
            Dict with 'comuni' and 'metadata' keys

        Raises:
            FileNotFoundError: If database file doesn't exist
            json.JSONDecodeError: If file is not valid JSON
        """
        if self.db_data is not None:
            return self.db_data

        if not self.db_path.exists():
            logger.error(f"Seismic database not found at {self.db_path}")
            raise FileNotFoundError(f"Database zone sismiche non trovato: {self.db_path}")

        try:
            with open(self.db_path, 'r', encoding='utf-8') as f:
                self.db_data = json.load(f)

            logger.info(
                f"Loaded seismic database: {self.db_data.get('metadata', {}).get('total_comuni', 0)} comuni"
            )
            return self.db_data

        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON in seismic database: {e}")
            raise

    def normalize_comune(self, comune: str) -> str:
        """
        Normalize comune name for matching.

        Args:
            comune: Raw comune name

        Returns:
            Normalized comune name (uppercase, accents removed)
        """
        comune_upper = comune.upper().strip()
        # Remove common accent variations
        replacements = {
            "'": "'",
            "À": "A", "Á": "A",
            "È": "E", "É": "E",
            "Ì": "I", "Í": "I",
            "Ò": "O", "Ó": "O",
            "Ù": "U", "Ú": "U"
        }

        for old, new in replacements.items():
            comune_upper = comune_upper.replace(old, new)

        return comune_upper

    def get_zone_description(self, zona: int) -> str:
        """Get human-readable description for seismic zone."""
        return self.zone_descriptions.get(zona, "N/D")

    def calculate_fuzzy_confidence(self, input_str: str, match_str: str) -> float:
        """Calculate similarity confidence between two strings."""
        return round(SequenceMatcher(None, input_str, match_str).ratio(), 2)

    def get_zone_by_comune(
        self,
        comune: str,
        provincia: Optional[str] = None
    ) -> Dict:
        """
        Get seismic zone data for a comune from JSON database.

        Uses multiple search strategies:
        1. Exact match
        2. Fuzzy match (with optional provincia filter)
        3. Provincia-based estimation

        Args:
            comune: Comune name
            provincia: Optional provincia code (2 letters) for disambiguation

        Returns:
            Dict with seismic zone data and metadata:
            {
                "comune": str,
                "provincia": str,
                "regione": str,
                "zona_sismica": int (1-4),
                "accelerazione_ag": float,
                "risk_level": str,
                "description": str,
                "normativa": str,
                "source": str ("database_match" | "fuzzy_match" | "provincia_estimation"),
                "confidence": float (0.0-1.0),
                "note": str (optional)
            }

        Raises:
            FileNotFoundError: If database not found
            ValueError: If comune not found and no fuzzy matches
        """
        db = self.load_seismic_database()
        comuni = db.get('comuni', {})

        # Normalize input
        comune_upper = self.normalize_comune(comune)

        # STRATEGY 1: EXACT MATCH
        if comune_upper in comuni:
            zona_data = comuni[comune_upper]

            # If provincia specified, verify match
            if provincia and zona_data['provincia'] != provincia.upper():
                raise ValueError(
                    f"comune_provincia_mismatch: {comune} non trovato in provincia {provincia}. "
                    f"Trovato in provincia {zona_data['provincia']}"
                )

            return {
                "comune": comune_upper,
                "provincia": zona_data['provincia'],
                "regione": zona_data.get('regione', 'N/D'),
                "zona_sismica": zona_data['zona_sismica'],
                "accelerazione_ag": zona_data['accelerazione_ag'],
                "risk_level": zona_data['risk_level'],
                "description": self.get_zone_description(zona_data['zona_sismica']),
                "normativa": "OPCM 3519/2006",
                "source": "database_match",
                "confidence": 1.0
            }

        # STRATEGY 2: FUZZY MATCH
        all_comuni = list(comuni.keys())
        matches = get_close_matches(comune_upper, all_comuni, n=5, cutoff=0.6)

        if matches:
            # Filter by provincia if specified
            if provincia:
                provincia_matches = [
                    m for m in matches
                    if comuni[m]['provincia'] == provincia.upper()
                ]

                if provincia_matches:
                    best_match = provincia_matches[0]
                else:
                    # No matches in specified provincia
                    suggestions = [
                        {"comune": m, "provincia": comuni[m]['provincia']}
                        for m in matches[:3]
                    ]
                    raise ValueError(
                        f"no_match_in_provincia: Nessun comune simile a '{comune}' "
                        f"trovato in provincia {provincia}. Suggerimenti: {suggestions}"
                    )
            else:
                best_match = matches[0]

            zona_data = comuni[best_match]
            confidence = self.calculate_fuzzy_confidence(comune_upper, best_match)

            return {
                "comune": best_match,
                "input_comune": comune_upper,
                "provincia": zona_data['provincia'],
                "regione": zona_data.get('regione', 'N/D'),
                "zona_sismica": zona_data['zona_sismica'],
                "accelerazione_ag": zona_data['accelerazione_ag'],
                "risk_level": zona_data['risk_level'],
                "description": self.get_zone_description(zona_data['zona_sismica']),
                "normativa": "OPCM 3519/2006",
                "source": "fuzzy_match",
                "confidence": confidence,
                "note": f"Match approssimato: '{comune}' -> '{best_match}'"
            }

        # STRATEGY 3: PROVINCIA ESTIMATION
        if provincia:
            provincia_upper = provincia.upper()
            comuni_provincia = {
                k: v for k, v in comuni.items()
                if v['provincia'] == provincia_upper
            }

            if comuni_provincia:
                # Find most common zone in provincia
                zone_counts = {}
                for data in comuni_provincia.values():
                    z = data['zona_sismica']
                    zone_counts[z] = zone_counts.get(z, 0) + 1

                zona_stimata = max(zone_counts, key=zone_counts.get)
                ag_reference = db.get('metadata', {}).get('ag_reference', {})

                return {
                    "comune": comune_upper,
                    "provincia": provincia_upper,
                    "zona_sismica": zona_stimata,
                    "accelerazione_ag": ag_reference.get(f'zona_{zona_stimata}', 0.0),
                    "risk_level": ["Molto Alta", "Alta", "Media", "Bassa"][zona_stimata - 1],
                    "description": self.get_zone_description(zona_stimata),
                    "normativa": "OPCM 3519/2006",
                    "source": "provincia_estimation",
                    "confidence": 0.5,
                    "note": f"Stima basata sulla zona prevalente della provincia {provincia_upper}"
                }

        # NO MATCHES FOUND
        suggestions = []
        if matches:
            suggestions = [
                {
                    "comune": m,
                    "provincia": comuni[m]['provincia'],
                    "zona_sismica": comuni[m]['zona_sismica']
                }
                for m in matches[:5]
            ]

        raise ValueError(
            f"comune_not_found: Comune '{comune}' non trovato. "
            f"Suggerimenti: {suggestions if suggestions else 'Nessuno'}"
        )

    def get_zone_from_db(
        self,
        comune: str,
        provincia: Optional[str] = None,
        db_session = None
    ) -> Dict:
        """
        Get seismic zone data from PostgreSQL database.

        Args:
            comune: Comune name
            provincia: Optional provincia code for disambiguation
            db_session: SQLAlchemy session (must be provided)

        Returns:
            Dict with seismic zone data (same format as get_zone_by_comune)

        Raises:
            ValueError: If db_session not provided or comune not found
        """
        if db_session is None:
            raise ValueError("db_session is required for database queries")

        from database.models import SeismicZone

        # Normalize comune
        comune_upper = comune.upper()

        # Build query
        query = db_session.query(SeismicZone).filter(
            SeismicZone.comune == comune_upper
        )

        if provincia:
            query = query.filter(SeismicZone.provincia == provincia.upper())

        result = query.first()

        if not result:
            raise ValueError(
                f"comune_not_found: Comune '{comune}' non trovato nel database zone sismiche"
            )

        return {
            "comune": result.comune,
            "provincia": result.provincia,
            "regione": result.regione,
            "zona_sismica": result.zona_sismica,
            "accelerazione_ag": float(result.accelerazione_ag),
            "risk_level": result.risk_level,
            "description": self.get_zone_description(result.zona_sismica),
            "normativa": "OPCM 3519/2006",
            "source": "database_match",
            "confidence": 1.0
        }

    def get_suggestions(self, comune: str, limit: int = 5) -> List[Dict]:
        """
        Get similar comune suggestions for a given input.

        Args:
            comune: Comune name to find suggestions for
            limit: Maximum number of suggestions

        Returns:
            List of suggestion dicts with comune, provincia, zona_sismica
        """
        try:
            db = self.load_seismic_database()
            comuni = db.get('comuni', {})

            comune_upper = self.normalize_comune(comune)
            all_comuni = list(comuni.keys())
            matches = get_close_matches(comune_upper, all_comuni, n=limit, cutoff=0.4)

            suggestions = []
            for match in matches:
                data = comuni[match]
                suggestions.append({
                    "comune": match,
                    "provincia": data['provincia'],
                    "zona_sismica": data['zona_sismica']
                })

            return suggestions

        except Exception as e:
            logger.error(f"Error getting suggestions: {e}")
            return []
