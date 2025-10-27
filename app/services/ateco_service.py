"""
ATECO Service - Business logic for ATECO code lookup and enrichment.

Extracted from ateco_lookup.py for modular architecture.
Handles ATECO 2022/2025 code normalization, search, and sector enrichment.
"""
from __future__ import annotations

import logging
from difflib import get_close_matches
from functools import lru_cache
from pathlib import Path
from typing import Dict, List, Optional, Union

import pandas as pd
import yaml

logger = logging.getLogger(__name__)

# ----------------------- Header Aliases (Column Name Tolerance) -----------------------
ALIASES = {
    "ORDINE_CODICE_ATECO_2022": ["ORDINE_CODICE_ATECO_2022", "ORDINE_CODICE"],
    "CODICE_ATECO_2022": ["CODICE_ATECO_2022", "CODICE ATECO 2022", "CODICE_ATECO"],
    "TITOLO_ATECO_2022": ["TITOLO_ATECO_2022", "TITOLO ATECO 2022", "TITOLO_2022", "TITOLO_ATECO"],
    "GERARCHIA_ATECO_2022": ["GERARCHIA_ATECO_2022", "GERARCHIA_ATEC", "GERARCHIA"],
    "NUMERO_CORR_ATECO_2022": ["NUMERO_CORR_ATECO_2022", "NUMERO_CORR_A", "N_CORR_2022"],
    "SOTTOTIPOLOGIA": ["SOTTOTIPOLOGIA"],
    "TIPO_RICODIFICA": ["TIPO_RICODIFICA"],
    "CODICE_ATECO_2025_RAPPRESENTATIVO": ["CODICE_ATECO_2025_RAPPRESENTATIVO", "CODICE ATECO 2025 RAPPRESENTATIVO"],
    "TITOLO_ATECO_2025_RAPPRESENTATIVO": ["TITOLO_ATECO_2025_RAPPRESENTATIVO", "TITOLO ATECO 2025 RAPPRESENTATIVO"],
    "CODICE_ATECO_2025_RAPPRESENTATIVO_SISTEMA_CAMERALE": [
        "CODICE_ATECO_2025_RAPPRESENTATIVO_SISTEMA_CAMERALE",
        "CODICE 2025 SISTEMA CAMERALE",
    ],
    "TITOLO_ATECO_2025_RAPPRESENTATIVO_SISTEMA_CAMERALE": [
        "TITOLO_ATECO_2025_RAPPRESENTATIVO_SISTEMA_CAMERALE",
        "TITOLO 2025 SISTEMA CAMERALE",
    ],
}
HEADER_RESOLVE: Dict[str, str] = {
    opt.lower(): std for std, lst in ALIASES.items() for opt in lst
}

# ----------------------- Excel Sheet Names -----------------------
POSSIBLE_SHEETS = ["Tabella operativa", "tabella operativa", "Foglio1", "Sheet1"]

# ----------------------- Search Order for ATECO Versions -----------------------
SEARCH_ORDER = [
    ("2022", "CODICE_ATECO_2022"),
    ("2025", "CODICE_ATECO_2025_RAPPRESENTATIVO"),
    ("2025-camerale", "CODICE_ATECO_2025_RAPPRESENTATIVO_SISTEMA_CAMERALE"),
]


# ----------------------- Utility Functions -----------------------


def normalize_code(raw: Union[str, float]) -> str:
    """
    Normalize ATECO code: strip spaces, replace commas with dots, uppercase.

    Args:
        raw: Raw ATECO code (string or float)

    Returns:
        Normalized code string (empty string if None/NaN)

    Examples:
        >>> normalize_code("62.01")
        "62.01"
        >>> normalize_code("62,01")
        "62.01"
        >>> normalize_code(" 62.01 ")
        "62.01"
        >>> normalize_code(62.01)
        "62.01"
    """
    if pd.isna(raw):
        return ""
    return str(raw).strip().replace(",", ".").replace(" ", "").upper()


def strip_code(raw: Union[str, float]) -> str:
    """
    Strip non-alphanumeric characters from ATECO code.

    Used for fuzzy matching and search.

    Args:
        raw: Raw ATECO code

    Returns:
        Code with only alphanumeric characters

    Examples:
        >>> strip_code("62.01")
        "6201"
        >>> strip_code("62-01-A")
        "6201A"
    """
    if pd.isna(raw):
        return ""
    return "".join(ch for ch in str(raw) if ch.isalnum())


def code_variants(code: str) -> List[str]:
    """
    Generate ATECO code variants for flexible matching.

    Variants include:
    - Original code
    - Code without dots
    - Zero-padded variants (e.g., 62.01 → 62.010, 62.0100)

    Args:
        code: Normalized ATECO code

    Returns:
        List of code variants (sorted, unique)

    Examples:
        >>> code_variants("62.01")
        ["6201", "62.01", "62.010", "62.0100"]
        >>> code_variants("62")
        ["62", "62.0", "62.00"]
    """
    c = normalize_code(code)
    if not c:
        return []

    parts = c.split(".")
    variants = {c, "".join(parts)}  # with dots and without

    if c.endswith("."):
        variants.add(c[:-1])

    # Add zero-padded variants for last numeric part
    if parts and parts[-1].isdigit():
        last = parts[-1]
        if len(last) == 1:
            variants.add(".".join(parts[:-1] + [last + "0"]))
            variants.add(".".join(parts[:-1] + [last + "00"]))
        elif len(last) == 2:
            variants.add(".".join(parts[:-1] + [last + "0"]))

    return sorted(variants)


def normalize_headers(df: pd.DataFrame) -> pd.DataFrame:
    """
    Normalize Excel column headers using ALIASES mapping.

    Maps various column name variations to standard names.

    Args:
        df: DataFrame with raw Excel columns

    Returns:
        DataFrame with normalized column names
    """
    mapping: Dict[str, str] = {}
    for col in df.columns:
        mapping[col] = HEADER_RESOLVE.get(str(col).strip().lower(), col)
    return df.rename(columns=mapping)


def load_mapping(path: Path = Path("mapping.yaml")) -> dict:
    """
    Load sector mapping YAML file.

    Contains sector → normative/certificazioni mappings.

    Args:
        path: Path to mapping.yaml

    Returns:
        Mapping dictionary (empty dict if file not found)
    """
    if not path.exists():
        logger.warning(f"Mapping file not found: {path}")
        return {}
    try:
        with open(path, "r", encoding="utf-8") as f:
            return yaml.safe_load(f) or {}
    except Exception as e:
        logger.error(f"Error loading mapping file: {e}")
        return {}


# ----------------------- ATECO Service Class -----------------------


class ATECOService:
    """
    Service for ATECO code lookup, search, and enrichment.

    Handles:
    - Dataset loading with caching
    - ATECO 2022/2025 code conversion
    - Smart search (exact, prefix, fuzzy)
    - Sector enrichment with normative/certificazioni
    """

    def __init__(self, dataset_path: Path, mapping_path: Path = Path("mapping.yaml")):
        """
        Initialize ATECO service.

        Args:
            dataset_path: Path to ATECO Excel dataset (tabella_ATECO.xlsx)
            mapping_path: Path to sector mapping YAML
        """
        self.dataset_path = dataset_path
        self.mapping = load_mapping(mapping_path)
        self._df_cache = None
        logger.info(f"ATECOService initialized with dataset: {dataset_path}")

    @lru_cache(maxsize=1)
    def load_dataset(self, debug: bool = False) -> pd.DataFrame:
        """
        Load and normalize ATECO dataset from Excel.

        Creates normalized columns (__NORM, __STRIP) for efficient search.
        Uses LRU cache to avoid reloading on every request.

        Args:
            debug: If True, print debug info about sheets

        Returns:
            Normalized DataFrame with ATECO data

        Raises:
            FileNotFoundError: If dataset file not found
        """
        if not self.dataset_path.exists():
            raise FileNotFoundError(f"Dataset file not found: {self.dataset_path}")

        xls = pd.ExcelFile(self.dataset_path)
        sheet_to_use = xls.sheet_names[0]

        # Find correct sheet name
        for sheet in POSSIBLE_SHEETS:
            if sheet in xls.sheet_names:
                sheet_to_use = sheet
                break

        if debug:
            logger.info(f"Excel sheets: {xls.sheet_names}, using: {sheet_to_use}")

        df = pd.read_excel(xls, sheet_name=sheet_to_use, dtype=str)
        df = normalize_headers(df)

        # Create normalized columns for search
        for key in [
            "CODICE_ATECO_2022",
            "CODICE_ATECO_2025_RAPPRESENTATIVO",
            "CODICE_ATECO_2025_RAPPRESENTATIVO_SISTEMA_CAMERALE",
        ]:
            if key in df.columns:
                df[key + "__NORM"] = df[key].apply(normalize_code)
                df[key + "__STRIP"] = df[key].apply(strip_code)

        logger.info(f"Dataset loaded: {len(df)} rows")
        return df

    def search_smart(
        self,
        code: str,
        prefer: Optional[str] = None,
        prefix: bool = False,
    ) -> pd.DataFrame:
        """
        Smart search for ATECO codes with 2022/2025 fallback.

        Search strategy:
        1. Generate code variants (with/without dots, zero-padded)
        2. Search in order: 2022 → 2025 → 2025-camerale (or reordered by prefer)
        3. Try exact match first
        4. If prefix=True, try prefix match
        5. If still no results, fallback to prefix search in 2022 codes

        Args:
            code: ATECO code to search
            prefer: Preferred version ("2022", "2025", "2025-camerale")
            prefix: If True, enable prefix matching

        Returns:
            DataFrame with matching rows (empty if no match)
        """
        df = self.load_dataset()
        variants = code_variants(code)
        order = SEARCH_ORDER.copy()

        # Reorder search if preference specified
        if prefer:
            order.sort(key=lambda x: 0 if x[0] == prefer else 1)

        # Phase 1: Exact match
        for _, base in order:
            cols = [
                c for c in (base + "__NORM", base + "__STRIP", base) if c in df.columns
            ]
            if not cols:
                continue

            mask = False
            for col in cols:
                ser = df[col].astype(str)
                mask = mask | ser.isin(variants)

            exact = df[mask]
            if not exact.empty:
                logger.info(f"Found exact match in {base}: {len(exact)} rows")
                return exact

        # Phase 2: Prefix match (if enabled)
        if prefix:
            for _, base in order:
                cols = [
                    c
                    for c in (base + "__NORM", base + "__STRIP", base)
                    if c in df.columns
                ]
                if not cols:
                    continue

                mask = False
                for col in cols:
                    ser = df[col].astype(str)
                    m = False
                    for v in variants:
                        m = m | ser.str.startswith(v)
                    mask = mask | m

                pref = df[mask]
                if not pref.empty:
                    logger.info(f"Found prefix match in {base}: {len(pref)} rows")
                    return pref

        # Phase 3: Fallback prefix search in 2022 codes
        base = (
            "CODICE_ATECO_2022__NORM"
            if "CODICE_ATECO_2022__NORM" in df.columns
            else "CODICE_ATECO_2022"
        )
        ser = df[base].astype(str)
        m = False
        for v in variants:
            m = m | ser.str.startswith(v)

        result = df[m]
        logger.info(f"Fallback search returned {len(result)} rows")
        return result

    def find_similar_codes(self, code: str, limit: int = 5) -> List[Dict[str, str]]:
        """
        Find similar ATECO codes using fuzzy matching.

        Useful for typo correction and suggestions.

        Args:
            code: ATECO code (possibly misspelled)
            limit: Maximum number of suggestions

        Returns:
            List of similar codes with titles

        Examples:
            >>> service.find_similar_codes("62.10", limit=3)
            [{"code": "62.01", "title": "Produzione software"}, ...]
        """
        df = self.load_dataset()
        code_norm = normalize_code(code)
        all_codes = df["CODICE_ATECO_2022"].dropna().unique()
        all_codes_norm = [normalize_code(c) for c in all_codes]

        # Find close matches with 60% similarity threshold
        matches = get_close_matches(code_norm, all_codes_norm, n=limit, cutoff=0.6)

        suggestions = []
        for match in matches:
            idx = all_codes_norm.index(match)
            original_code = all_codes[idx]
            row = df[df["CODICE_ATECO_2022"] == original_code].iloc[0]
            suggestions.append(
                {"code": original_code, "title": row.get("TITOLO_ATECO_2022", "")}
            )

        logger.info(f"Found {len(suggestions)} similar codes for '{code}'")
        return suggestions

    def flatten(self, row: pd.Series) -> Dict[str, Optional[str]]:
        """
        Convert DataFrame row to JSON-serializable dict.

        Excludes internal columns (__NORM, __STRIP).
        Converts NaN values to None.

        Args:
            row: DataFrame row (pandas Series)

        Returns:
            Dictionary with column_name → value mapping
        """
        data: Dict[str, Optional[str]] = {}
        for k, v in row.items():
            if k.endswith("__NORM") or k.endswith("__STRIP"):
                continue
            data[k] = None if pd.isna(v) else v
        return data

    def enrich(self, item: dict) -> dict:
        """
        Enrich ATECO item with sector, normative, and certificazioni.

        Uses CODICE_ATECO_2022 prefix to determine sector:
        - 20: chimico
        - 10-11: alimentare
        - 21, 86: sanitario
        - 29, 45: automotive
        - 25, 28: industriale
        - 62: ict
        - 64, 66: finance

        Then looks up normative/certificazioni from mapping.yaml.

        Args:
            item: ATECO item dict (from flatten())

        Returns:
            Enriched item with settore, normative, certificazioni fields
        """
        code = item.get("CODICE_ATECO_2022", "") or ""
        settore = None

        # Determine sector from code prefix
        if code.startswith("20"):
            settore = "chimico"
        elif code.startswith("10") or code.startswith("11"):
            settore = "alimentare"
        elif code.startswith("21") or code.startswith("86"):
            settore = "sanitario"
        elif code.startswith("29") or code.startswith("45"):
            settore = "automotive"
        elif code.startswith("25") or code.startswith("28"):
            settore = "industriale"
        elif code.startswith("62"):
            settore = "ict"
        elif code.startswith("64") or code.startswith("66"):
            settore = "finance"

        # Lookup normative/certificazioni from mapping
        if settore and settore in self.mapping.get("settori", {}):
            item["settore"] = settore
            item["normative"] = self.mapping["settori"][settore].get("normative", [])
            item["certificazioni"] = self.mapping["settori"][settore].get(
                "certificazioni", []
            )
        else:
            item["settore"] = settore or "non mappato"
            item["normative"] = []
            item["certificazioni"] = []

        return item
