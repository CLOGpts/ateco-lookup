#!/usr/bin/env python3
"""
MAIN.PY - Wrapper per ateco_lookup.py
"""
import logging
from pathlib import Path

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

logger.info("main.py: Loading ateco_lookup...")

# Importa le funzioni necessarie da ateco_lookup
from ateco_lookup import load_dataset, build_api

# Carica il dataset e crea l'app
logger.info("main.py: Loading ATECO dataset...")
df = load_dataset(Path("ateco_2025_mapping.xlsx"))

logger.info("main.py: Building FastAPI app...")
app = build_api(df)

logger.info("main.py: App ready with all ATECO + Risk endpoints!")