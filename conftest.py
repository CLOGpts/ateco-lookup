"""
Pytest configuration file

This file is automatically loaded by pytest and sets up the Python path
to allow importing from the 'app' package in tests.
"""

import sys
from pathlib import Path

# Add the project root to Python path so 'app' package can be imported
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))
