"""
Risk Service - Business logic for risk assessment and calculation.

Extracted from main.py for modular architecture.
Handles risk events, descriptions, scoring, and matrix calculations.
"""
import json
import logging
from pathlib import Path
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


class RiskService:
    """
    Service for risk assessment operations.

    Handles:
    - Risk event categorization and listing
    - Event descriptions with impact/probability/controls
    - Risk score calculation
    - Risk matrix position calculation
    """

    def __init__(self, data_path: Path = Path("MAPPATURE_EXCEL_PERFETTE.json")):
        """
        Initialize Risk service.

        Args:
            data_path: Path to risk mappings JSON file
        """
        self.data_path = data_path
        self.excel_categories: Dict[str, List[str]] = {}
        self.excel_descriptions: Dict[str, str] = {}
        self._load_risk_data()
        logger.info(f"RiskService initialized with data from: {data_path}")

    def _load_risk_data(self):
        """
        Load risk data from JSON file.

        Loads EXCEL_CATEGORIES and EXCEL_DESCRIPTIONS.
        Uses fallback if file not found.
        """
        try:
            with open(self.data_path, 'r', encoding='utf-8') as f:
                risk_data = json.load(f)
                self.excel_categories = risk_data.get('mappature_categoria_eventi', {})
                self.excel_descriptions = risk_data.get('vlookup_map', {})
            logger.info(f"Risk data loaded: {len(self.excel_categories)} categories")
        except FileNotFoundError:
            logger.warning(f"⚠️ {self.data_path} not found, using fallback")
            self.excel_categories = {
                "Damage_Danni": [],
                "Business_disruption": [],
                "Employment_practices_Dipendenti": [],
                "Execution_delivery_Problemi_di_produzione_o_consegna": [],
                "Clients_product_Clienti": [],
                "Internal_Fraud_Frodi_interne": [],
                "External_fraud_Frodi_esterne": []
            }
            self.excel_descriptions = {}
        except json.JSONDecodeError as e:
            logger.error(f"❌ {self.data_path} corrupt: {e}")
            raise
        except Exception as e:
            logger.error(f"❌ Unexpected error loading {self.data_path}: {e}")
            raise

    def get_category_mapping(self) -> Dict[str, str]:
        """
        Get category alias mapping.

        Maps common category names to Excel category names.

        Returns:
            Dictionary of alias -> real_category
        """
        return {
            "operational": "Execution_delivery_Problemi_di_produzione_o_consegna",
            "cyber": "Business_disruption",
            "compliance": "Clients_product_Clienti",
            "financial": "Internal_Fraud_Frodi_interne",
            "damage": "Damage_Danni",
            "employment": "Employment_practices_Dipendenti",
            "external_fraud": "External_fraud_Frodi_esterne"
        }

    def normalize_category_name(self, category: str) -> Optional[str]:
        """
        Normalize category name to Excel category.

        Args:
            category: User-provided category name

        Returns:
            Excel category name or None if not found
        """
        # Try exact match
        if category in self.excel_categories:
            return category

        # Try mapping
        category_mapping = self.get_category_mapping()
        if category.lower() in category_mapping:
            return category_mapping[category.lower()]

        # Try fuzzy match
        for cat in self.excel_categories:
            if category.lower() in cat.lower():
                return cat

        return None

    def get_events_for_category(self, category: str) -> Dict:
        """
        Get risk events for a category.

        Args:
            category: Category name (can be alias)

        Returns:
            Dict with category, events list, total OR error dict
        """
        real_category = self.normalize_category_name(category)

        if not real_category or real_category not in self.excel_categories:
            available = list(self.excel_categories.keys())
            category_mapping = self.get_category_mapping()
            return {
                "error": f"Category '{category}' not found",
                "available_categories": available,
                "category_mapping": category_mapping
            }

        # Parse events from Excel format
        events = []
        for event_str in self.excel_categories[real_category]:
            parts = event_str.split(' - ', 1)
            if len(parts) == 2:
                code = parts[0].strip()
                name = parts[1].strip()
                severity = self._calculate_severity(code)

                events.append({
                    "code": code,
                    "name": name,
                    "severity": severity
                })

        logger.info(f"Found {len(events)} events for category: {real_category}")

        return {
            "category": real_category,
            "original_request": category,
            "events": events,
            "total": len(events)
        }

    def _calculate_severity(self, event_code: str) -> str:
        """
        Calculate event severity based on code prefix.

        Args:
            event_code: Event code (e.g., "101", "201")

        Returns:
            Severity level: low, medium, high, critical
        """
        if event_code.startswith('1'):
            return 'medium'
        elif event_code.startswith('2'):
            return 'high'
        elif event_code.startswith('3'):
            return 'low'
        elif event_code.startswith('4'):
            return 'medium'
        elif event_code.startswith('5'):
            return 'high'
        elif event_code.startswith('6') or event_code.startswith('7'):
            return 'critical'
        else:
            return 'medium'

    def get_event_description(self, event_code: str) -> Dict:
        """
        Get detailed description for an event.

        Args:
            event_code: Event code (e.g., "101")

        Returns:
            Dict with code, name, description, impact, probability, controls OR error dict
        """
        import re

        # Clean event_code (handle [object Object] from frontend)
        if '[object' in event_code.lower() or '{' in event_code:
            numbers = re.findall(r'\d+', event_code)
            if numbers:
                event_code = numbers[0]
            else:
                return {
                    "error": "Invalid event code format",
                    "received": event_code,
                    "expected": "Event code like '101', '201', etc.",
                    "hint": "Frontend should pass event.code, not the entire event object"
                }

        event_code = event_code.strip()

        # Find event in categories
        event_name = None
        category_found = None

        for cat_name, cat_events in self.excel_categories.items():
            for event in cat_events:
                if event.startswith(event_code + ' - '):
                    event_name = event.split(' - ', 1)[1]
                    category_found = cat_name
                    break
            if event_name:
                break

        # Get VLOOKUP description if available
        vlookup_description = self.excel_descriptions.get(event_code)

        if event_name:
            final_description = vlookup_description if vlookup_description else event_name
            impact = self._get_impact_for_code(event_code)
            probability = self._get_probability_for_code(event_code)
            controls = self._get_controls_for_code(event_code)

            return {
                "code": event_code,
                "name": event_name,
                "description": final_description,
                "category": category_found,
                "impact": impact,
                "probability": probability,
                "controls": controls,
                "source": "Excel Risk Mapping",
                "has_vlookup": vlookup_description is not None
            }

        # Event not found
        return {
            "code": event_code,
            "name": "Evento non mappato",
            "description": f"Evento {event_code} non presente nel mapping Excel",
            "impact": "Da valutare",
            "probability": "unknown",
            "controls": ["Da definire in base all'analisi specifica"],
            "source": "Generic"
        }

    def _get_impact_for_code(self, event_code: str) -> str:
        """Get impact description based on event code prefix."""
        if event_code.startswith('1'):
            return "Danni fisici e materiali"
        elif event_code.startswith('2'):
            return "Interruzione operativa e perdita dati"
        elif event_code.startswith('3'):
            return "Problemi con dipendenti e clima aziendale"
        elif event_code.startswith('4'):
            return "Errori di processo e consegna"
        elif event_code.startswith('5'):
            return "Perdita clienti e sanzioni"
        elif event_code.startswith('6'):
            return "Frodi interne e perdite finanziarie"
        elif event_code.startswith('7'):
            return "Frodi esterne e attacchi cyber"
        else:
            return "Da valutare caso per caso"

    def _get_probability_for_code(self, event_code: str) -> str:
        """Get probability based on event code prefix."""
        if event_code.startswith('1'):
            return "low"
        elif event_code.startswith('2'):
            return "medium"
        elif event_code.startswith('3'):
            return "medium"
        elif event_code.startswith('4'):
            return "high"
        elif event_code.startswith('5'):
            return "medium"
        elif event_code.startswith('6'):
            return "low"
        elif event_code.startswith('7'):
            return "medium"
        else:
            return "unknown"

    def _get_controls_for_code(self, event_code: str) -> List[str]:
        """Get recommended controls based on event code prefix."""
        if event_code.startswith('1'):
            return ["Assicurazione danni", "Manutenzione preventiva", "Procedure di emergenza"]
        elif event_code.startswith('2'):
            return ["Backup e recovery", "Ridondanza sistemi", "Monitoring continuo"]
        elif event_code.startswith('3'):
            return ["HR policies", "Formazione continua", "Welfare aziendale"]
        elif event_code.startswith('4'):
            return ["Quality control", "Process automation", "KPI monitoring"]
        elif event_code.startswith('5'):
            return ["Customer satisfaction", "Compliance monitoring", "Legal review"]
        elif event_code.startswith('6'):
            return ["Audit interni", "Segregation of duties", "Whistleblowing"]
        elif event_code.startswith('7'):
            return ["Cybersecurity", "Fraud detection", "Identity verification"]
        else:
            return ["Controlli standard da definire"]

    def calculate_risk_matrix(self, data: dict) -> Dict:
        """
        Calculate risk matrix position and level.

        Implements Excel-based risk matrix calculation:
        - Inherent risk = min(economic_loss, non_economic_loss)
        - Matrix position = f"{column}{row}"
        - Risk level based on position

        Args:
            data: Dict with economic_loss, non_economic_loss, control_level

        Returns:
            Dict with matrix_position, risk_level, recommendations, etc.
        """
        # Convert colors to values (Excel system)
        color_to_value = {'G': 4, 'Y': 3, 'O': 2, 'R': 1}

        economic_value = color_to_value.get(data.get('economic_loss', 'G'), 4)
        non_economic_value = color_to_value.get(data.get('non_economic_loss', 'G'), 4)

        # Calculate inherent risk (MIN of two values, as per Excel)
        inherent_risk = min(economic_value, non_economic_value)

        # Map control to matrix row
        control_to_row = {
            '--': 1,  # Not adequate
            '-': 2,   # Partially adequate
            '+': 3,   # Substantially adequate
            '++': 4   # Adequate
        }

        control_level = data.get('control_level', '+')
        row = control_to_row.get(control_level, 3)

        # Calculate column based on inherent risk
        # Risk 4 (low) -> column A, Risk 1 (high) -> column D
        column_map = {4: 'A', 3: 'B', 2: 'C', 1: 'D'}
        column = column_map.get(inherent_risk, 'B')

        # Matrix position (e.g., "A1", "B2", "C3", "D4")
        matrix_position = f"{column}{row}"

        # Determine risk level based on position
        risk_levels = {
            'A4': {'level': 'Low', 'color': 'green', 'value': 0},
            'A3': {'level': 'Low', 'color': 'green', 'value': 0},
            'B4': {'level': 'Low', 'color': 'green', 'value': 0},
            'A2': {'level': 'Medium', 'color': 'yellow', 'value': 0},
            'B3': {'level': 'Medium', 'color': 'yellow', 'value': 0},
            'C4': {'level': 'Medium', 'color': 'yellow', 'value': 0},
            'A1': {'level': 'High', 'color': 'orange', 'value': 0},
            'B2': {'level': 'High', 'color': 'orange', 'value': 0},
            'C3': {'level': 'High', 'color': 'orange', 'value': 0},
            'D4': {'level': 'High', 'color': 'orange', 'value': 0},
            'B1': {'level': 'Critical', 'color': 'red', 'value': 1},
            'C2': {'level': 'Critical', 'color': 'red', 'value': 1},
            'D3': {'level': 'Critical', 'color': 'red', 'value': 1},
            'C1': {'level': 'Critical', 'color': 'red', 'value': 1},
            'D2': {'level': 'Critical', 'color': 'red', 'value': 1},
            'D1': {'level': 'Critical', 'color': 'red', 'value': 1}
        }

        risk_info = risk_levels.get(
            matrix_position,
            {'level': 'Medium', 'color': 'yellow', 'value': 0}
        )

        # Generate recommendations
        recommendations = self._get_recommendations(risk_info['level'])

        logger.info(
            f"Risk calculation: {matrix_position} = {risk_info['level']} "
            f"(Inherent: {inherent_risk}, Control: {row})"
        )

        return {
            'status': 'success',
            'matrix_position': matrix_position,
            'risk_level': risk_info['level'],
            'risk_color': risk_info['color'],
            'risk_value': risk_info['value'],
            'inherent_risk': {
                'value': inherent_risk,
                'label': {4: 'Low', 3: 'Medium', 2: 'High', 1: 'Critical'}[inherent_risk]
            },
            'control_effectiveness': {
                'value': row,
                'label': control_level,
                'description': {
                    '++': 'Adeguato',
                    '+': 'Sostanzialmente adeguato',
                    '-': 'Parzialmente Adeguato',
                    '--': 'Non adeguato / assente'
                }.get(control_level, 'Unknown')
            },
            'calculation_details': {
                'economic_loss': data.get('economic_loss'),
                'economic_value': economic_value,
                'non_economic_loss': data.get('non_economic_loss'),
                'non_economic_value': non_economic_value,
                'min_value': inherent_risk,
                'control_level': control_level,
                'control_row': row,
                'matrix_column': column
            },
            'recommendations': recommendations
        }

    def _get_recommendations(self, risk_level: str) -> List[str]:
        """Get recommendations based on risk level."""
        if risk_level == 'Critical':
            return [
                'Azione immediata richiesta',
                'Implementare controlli aggiuntivi urgentemente',
                'Escalation al management richiesta'
            ]
        elif risk_level == 'High':
            return [
                'Priorità alta per mitigazione',
                'Rafforzare i controlli esistenti',
                'Monitoraggio frequente richiesto'
            ]
        elif risk_level == 'Medium':
            return [
                'Monitorare regolarmente',
                'Valutare opportunità di miglioramento controlli',
                'Documentare piani di contingenza'
            ]
        else:  # Low
            return [
                'Rischio accettabile',
                'Mantenere controlli attuali',
                'Revisione periodica standard'
            ]

    def calculate_risk_score(self, data: dict) -> Dict:
        """
        Calculate risk score from assessment data.

        Scoring system:
        - Financial impact: 0-40 points
        - Economic loss: 0-30 points
        - Boolean impacts (image, regulatory, criminal): 10 points each
        - Non-economic loss: 0-10 points
        - Control multiplier: 0.5x to 1.5x

        Args:
            data: Dict with assessment values

        Returns:
            Dict with status, risk_score, analysis
        """
        score = 0

        # Financial impact (max 40 points)
        impatto_map = {
            'N/A': 0, '0 - 1K€': 5, '1 - 10K€': 10, '10 - 50K€': 15,
            '50 - 100K€': 20, '100 - 500K€': 25, '500K€ - 1M€': 30,
            '1 - 3M€': 35, '3 - 5M€': 40
        }
        score += impatto_map.get(data.get('impatto_finanziario', 'N/A'), 0)

        # Economic loss (max 30 points)
        perdita_map = {'G': 5, 'Y': 15, 'O': 25, 'R': 30}
        score += perdita_map.get(data.get('perdita_economica', 'G'), 0)

        # Boolean impacts (10 points each)
        if data.get('impatto_immagine') == 'Si':
            score += 10
        if data.get('impatto_regolamentare') == 'Si':
            score += 10
        if data.get('impatto_criminale') == 'Si':
            score += 10

        # Non-economic loss (max 10 points)
        perdita_non_eco_map = {'G': 0, 'Y': 3, 'O': 6, 'R': 10}
        score += perdita_non_eco_map.get(data.get('perdita_non_economica', 'G'), 0)

        # Control multiplier
        controllo_multiplier = {
            '++': 0.5,   # Reduces risk by 50%
            '+': 0.75,   # Reduces risk by 25%
            '-': 1.25,   # Increases risk by 25%
            '--': 1.5    # Increases risk by 50%
        }
        controllo = data.get('controllo', '+')
        if controllo in controllo_multiplier:
            score = int(score * controllo_multiplier[controllo])

        # Generate analysis
        if score >= 70:
            level = "CRITICO"
            action = "Richiede azione immediata"
        elif score >= 50:
            level = "ALTO"
            action = "Priorità alta, pianificare mitigazione"
        elif score >= 30:
            level = "MEDIO"
            action = "Monitorare e valutare opzioni"
        else:
            level = "BASSO"
            action = "Rischio accettabile, monitoraggio standard"

        analysis = f"Livello di rischio: {level} (Score: {score}/100). {action}"

        logger.info(f"Risk score calculated: {score} - {level}")

        return {
            "status": "success",
            "message": "Risk assessment salvato",
            "risk_score": score,
            "analysis": analysis
        }
