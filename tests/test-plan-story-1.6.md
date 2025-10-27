# Test Plan - Story 1.6: Expand Coverage to 60%

**Generated:** 2025-10-27
**Target:** 60% coverage on main.py (currently 20%)
**Gap:** Need to cover 683 additional statements

## Current Coverage Baseline

**Tested Endpoints (Story 1.5 - 30 tests):**
- ✅ ATECO Lookup: `/lookup`, `/batch`, `/autocomplete` (8 tests)
- ✅ Risk Calculation: `/calculate-risk-assessment` (11 tests)
- ✅ Seismic Zones: `/seismic-zone/{comune}` (11 tests)

**Coverage:** 329/1686 statements (20%)

---

## Endpoint Inventory (33 total endpoints)

### **Priority 1: Critical Business Logic (HIGH PRIORITY)**

| Endpoint | Method | Line | Category | Estimated Tests | Status |
|----------|--------|------|----------|----------------|--------|
| `/risk-assessment-fields` | GET | 841 | Risk | 2 | ❌ TODO |
| `/save-risk-assessment` | POST | 960 | Risk | 3 | ❌ TODO |
| `/calculate-risk-assessment` | POST | 1033 | Risk | 1 | ✅ DONE |
| `/description` | POST | 1162 | Risk | 2 | ❌ TODO |
| `/events/{category}` | GET | 655 | Risk Events | 4 | ❌ TODO |
| `/description/{event_code}` | GET | 726 | Risk Events | 3 | ❌ TODO |

**Subtotal P1:** ~14 tests needed

---

### **Priority 2: Data Lookup & Core Features (MEDIUM PRIORITY)**

| Endpoint | Method | Line | Category | Estimated Tests | Status |
|----------|--------|------|----------|----------------|--------|
| `/lookup` | GET | 513 | ATECO | 1 | ✅ DONE |
| `/batch` | POST | 550 | ATECO | 1 | ✅ DONE |
| `/autocomplete` | GET | 586 | ATECO | 1 | ✅ DONE |
| `/seismic-zone/{comune}` | GET | 1671 | Seismic | 1 | ✅ DONE |
| `/db/events/{category}` | GET | 2729 | DB Lookup | 3 | ❌ TODO |
| `/db/lookup` | GET | 2833 | DB Lookup | 2 | ❌ TODO |
| `/db/seismic-zone/{comune}` | GET | 2888 | DB Lookup | 2 | ❌ TODO |
| `/api/test-visura` | GET | 1263 | Visura | 2 | ❌ TODO |
| `/api/extract-visura` | POST | 1284 | Visura | 3 | ❌ TODO |

**Subtotal P2:** ~12 tests needed

---

### **Priority 3: System Health & Monitoring (MEDIUM PRIORITY)**

| Endpoint | Method | Line | Category | Estimated Tests | Status |
|----------|--------|------|----------|----------------|--------|
| `/health` | GET | 452 | Health | 1 | ❌ TODO |
| `/health/database` | GET | 457 | Health | 2 | ❌ TODO |
| `/team/hello` | GET | 496 | Health | 1 | ❌ TODO |

**Subtotal P3:** ~4 tests needed

---

### **Priority 4: Session & Reporting (MEDIUM PRIORITY)**

| Endpoint | Method | Line | Category | Estimated Tests | Status |
|----------|--------|------|----------|----------------|--------|
| `/api/events` | POST | 2955 | Sessions | 3 | ❌ TODO |
| `/api/sessions/{user_id}` | GET | 3053 | Sessions | 2 | ❌ TODO |
| `/api/sessions/{user_id}/summary` | GET | 3141 | Sessions | 2 | ❌ TODO |
| `/api/send-prereport-pdf` | POST | 3259 | PDF | 2 | ❌ TODO |
| `/api/send-risk-report-pdf` | POST | 3405 | PDF | 2 | ❌ TODO |
| `/api/feedback` | POST | 3696 | Feedback | 2 | ❌ TODO |

**Subtotal P4:** ~13 tests needed

---

### **Priority 5: Admin & Migration (LOW PRIORITY - Optional)**

| Endpoint | Method | Line | Category | Estimated Tests | Status |
|----------|--------|------|----------|----------------|--------|
| `/admin/setup-database` | GET | 1853 | Admin | 1 | ⚠️ SKIP |
| `/admin/check-tables` | GET | 1945 | Admin | 1 | ⚠️ SKIP |
| `/admin/create-tables` | POST | 2017 | Admin | 1 | ⚠️ SKIP |
| `/admin/migrate-risk-events` | POST | 2122 | Admin | 1 | ⚠️ SKIP |
| `/admin/migrate-ateco` | POST | 2322 | Admin | 1 | ⚠️ SKIP |
| `/admin/migrate-seismic-zones` | POST | 2531 | Admin | 1 | ⚠️ SKIP |
| `/admin/create-feedback-table` | POST | 3583 | Admin | 1 | ⚠️ SKIP |

**Subtotal P5:** ~7 tests (SKIP for now - low ROI for coverage)

---

## Test Execution Strategy

### **Phase 1: Quick Wins (Priority 3 - Health)**
- Target: `/health`, `/health/database`, `/team/hello`
- Expected coverage gain: +3-5%
- Tests: 4 tests
- Files: `tests/integration/test_health.py`

### **Phase 2: Core Business Logic (Priority 1 - Risk)**
- Target: Risk assessment fields, save, description, events
- Expected coverage gain: +15-20%
- Tests: ~14 tests
- Files: `tests/integration/test_risk_events.py`, `tests/integration/test_risk_fields.py`

### **Phase 3: Data Lookup (Priority 2 - DB & Visura)**
- Target: Database endpoints, Visura extraction
- Expected coverage gain: +10-15%
- Tests: ~12 tests
- Files: `tests/integration/test_db_endpoints.py`, `tests/integration/test_visura.py`

### **Phase 4: Sessions & Reporting (Priority 4)**
- Target: Sessions, PDF generation, feedback
- Expected coverage gain: +10-15%
- Tests: ~13 tests
- Files: `tests/integration/test_sessions.py`, `tests/integration/test_pdf_reports.py`, `tests/integration/test_feedback.py`

### **Phase 5: Coverage Verification**
- Run full test suite
- Verify ≥60% coverage
- Add targeted tests for any remaining gaps

---

## Estimated Test Count

| Priority | Tests Needed | Cumulative |
|----------|--------------|------------|
| P3 (Health) | 4 | 34 (30+4) |
| P1 (Risk) | 14 | 48 |
| P2 (Data) | 12 | 60 |
| P4 (Sessions) | 13 | 73 |
| **Total New Tests** | **43** | **73 total** |

**Estimated Final Coverage:** 60-65% (target: ≥60%)

---

## Golden Master Strategy

Each test will generate a golden master JSON:
- **Location:** `tests/fixtures/baseline_<endpoint>_<scenario>.json`
- **Content:** Full HTTP response (status, headers, body)
- **Purpose:** Regression detection during refactoring

**Estimated Golden Masters:** 43 new files

---

## Test Files to Create

1. `tests/integration/test_health.py` - Health & system endpoints (4 tests)
2. `tests/integration/test_risk_events.py` - Risk events endpoints (7 tests)
3. `tests/integration/test_risk_fields.py` - Risk assessment fields (7 tests)
4. `tests/integration/test_db_endpoints.py` - Database lookup endpoints (7 tests)
5. `tests/integration/test_visura.py` - Visura extraction (5 tests)
6. `tests/integration/test_sessions.py` - Session management (7 tests)
7. `tests/integration/test_pdf_reports.py` - PDF generation (4 tests)
8. `tests/integration/test_feedback.py` - Feedback collection (2 tests)

**Total:** 8 new test files, 43 new tests

---

## Success Criteria

- ✅ Coverage reaches ≥60% on main.py
- ✅ All tests pass (100% pass rate)
- ✅ Test suite runs in <30 seconds
- ✅ All tests are deterministic (no flaky tests)
- ✅ Golden masters created for all new tests

---

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| Some endpoints require database setup | Use mocks or skip database-dependent tests initially |
| PDF generation may be slow | Mock PDF generation logic, focus on endpoint structure |
| Visura may require external API | Mock external API calls |
| Session tests may need auth | Use test fixtures for auth tokens |

---

## Implementation Order

1. **Start:** Health endpoints (easiest, quick win)
2. **Core:** Risk events & fields (highest business value)
3. **Data:** DB lookups & Visura (medium complexity)
4. **Advanced:** Sessions, PDFs, Feedback (more complex)
5. **Verify:** Run coverage, fill gaps if needed
