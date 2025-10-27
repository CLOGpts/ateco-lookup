"""
Pytest configuration and shared fixtures for SYD Cyber Backend Tests

Questo file viene caricato automaticamente da pytest prima di eseguire i test.
Fornisce fixtures (oggetti riutilizzabili) per tutti i test.
"""
import json
import sys
from pathlib import Path
from typing import Generator

import pytest
from fastapi.testclient import TestClient

# Aggiungi la directory root al path per importare main.py
sys.path.insert(0, str(Path(__file__).parent.parent))

# NOTA: Import dell'app gestito in modo lazy per evitare problemi con il monolite
# Il monolite ha classi Pydantic definite dentro funzioni, che causano errori di import
# Soluzione: importiamo l'app solo quando serve (dentro la fixture)
def get_app():
    """
    Importa e restituisce l'app FastAPI.

    Questa funzione è necessaria perché il backend è un monolite con
    classi Pydantic definite dentro funzioni, che causano errori di import
    se caricate troppo presto.
    """
    from main import app
    return app


# ============================================================================
# FIXTURES - Oggetti riutilizzabili per i test
# ============================================================================

@pytest.fixture(scope="session")
def client() -> Generator[TestClient, None, None]:
    """
    Crea un client HTTP di test per chiamare l'API senza avviare il server.

    Spiegazione:
    - TestClient simula un browser/frontend che chiama il backend
    - Usa questo client nei test come: client.get("/endpoint")
    - NON serve avviare uvicorn, tutto in memoria!

    Scope "session" = crea 1 sola volta per tutti i test (performance)

    NOTA: Usa get_app() per import lazy (evita problemi con monolite)
    """
    app = get_app()  # Import lazy dell'app
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture(scope="session")
def fixtures_dir() -> Path:
    """
    Restituisce il path della cartella fixtures/ dove salvare i baseline.

    Uso nei test:
    def test_something(fixtures_dir):
        baseline_file = fixtures_dir / "my_baseline.json"
        with open(baseline_file, "w") as f:
            json.dump(result, f)
    """
    fixtures_path = Path(__file__).parent / "fixtures"
    fixtures_path.mkdir(exist_ok=True)
    return fixtures_path


@pytest.fixture
def sample_risk_data():
    """
    Dati di esempio per test risk calculation.

    Questo è un esempio di input valido per /calculate-risk-assessment
    """
    return {
        'economic_loss': 'G',        # Green (basso)
        'non_economic_loss': 'Y',    # Yellow (medio)
        'control_level': '++'         # Adeguato
    }


# ============================================================================
# HELPERS - Funzioni utility per i test
# ============================================================================

def save_baseline(data: dict, filename: str, fixtures_dir: Path):
    """
    Helper per salvare baseline JSON in modo consistente.

    Uso:
    save_baseline(response.json(), "risk_baseline.json", fixtures_dir)
    """
    filepath = fixtures_dir / filename
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    return filepath


def load_baseline(filename: str, fixtures_dir: Path) -> dict:
    """
    Helper per caricare baseline JSON salvati.

    Uso:
    expected = load_baseline("risk_baseline.json", fixtures_dir)
    """
    filepath = fixtures_dir / filename
    if not filepath.exists():
        raise FileNotFoundError(f"Baseline file not found: {filepath}")

    with open(filepath, "r", encoding="utf-8") as f:
        return json.load(f)


# Rendi gli helpers disponibili come fixtures
@pytest.fixture
def save_baseline_fixture(fixtures_dir):
    """Wrapper per usare save_baseline come fixture"""
    def _save(data, filename):
        return save_baseline(data, filename, fixtures_dir)
    return _save


@pytest.fixture
def load_baseline_fixture(fixtures_dir):
    """Wrapper per usare load_baseline come fixture"""
    def _load(filename):
        return load_baseline(filename, fixtures_dir)
    return _load
