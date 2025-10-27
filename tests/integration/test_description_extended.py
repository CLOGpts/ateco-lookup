"""
Test Baseline Estesi per /description Endpoint
===============================================

SCOPO: Test approfonditi per /description/{event_code} con vari event codes.

---
DOCUMENTAZIONE PER NUOVE CHAT:
Questi test coprono molti event codes per massimizzare coverage.
"""

import json
import pytest
from pathlib import Path


# ============================================================================
# TEST DESCRIPTION WITH MANY EVENT CODES
# ============================================================================

@pytest.mark.baseline
@pytest.mark.parametrize("event_code", [
    "101", "102", "103", "104", "105",  # Damage events
    "201", "202", "203", "204", "205",  # Business disruption
    "301", "302", "303", "304", "305",  # Employment
    "401", "402", "403", "404", "405",  # Execution
    "501", "502", "503", "504", "505",  # Clients
    "601", "602", "603", "604", "605",  # Internal fraud
    "701", "702", "703", "704", "705",  # External fraud
])
def test_description_many_codes(client, fixtures_dir, event_code):
    """
    Test /description/{event_code} with many different codes.

    This maximizes coverage by testing different code prefixes
    which trigger different logic branches in the code.
    """
    response = client.get(f"/description/{event_code}")

    # All should work (200 or return generic response)
    assert response.status_code == 200, \
        f"Expected 200, got {response.status_code} for code {event_code}"

    data = response.json()

    # Save baseline (but don't check structure to keep test simple)
    baseline_file = fixtures_dir / f"baseline_desc_code_{event_code}.json"
    with open(baseline_file, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    print(f"✅ Description {event_code} - saved")
