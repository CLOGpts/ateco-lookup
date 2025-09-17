#!/usr/bin/env python3
"""
MAIN.PY - Wrapper per ateco_lookup.py
Railway sembra cachare main.py, quindi usiamo questo come ponte
"""
import sys
import logging

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

logger.info("main.py: Importing ateco_lookup...")

# Importa tutto da ateco_lookup
from ateco_lookup import *

# L'app FastAPI viene da ateco_lookup
logger.info("main.py: App loaded from ateco_lookup")