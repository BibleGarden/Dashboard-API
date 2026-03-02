# Testing

## Test Database

Tests work with a separate database `cep_test` to avoid affecting production data.

### Initial Setup

```bash
# Create test database (once, or after changing migrations/seed data)
docker exec bible-api python tests/setup_test_db.py
```

The `setup_test_db.py` script:
1. Recreates the `cep_test` database (DROP + CREATE)
2. Applies all migrations from `migrations/`
3. Loads seed data from `tests/seed_test_data.sql`

### Running Tests

```bash
# Unit tests (use mocks, fast)
docker exec bible-api pytest tests/ -k "not integration" -v

# All tests (unit + integration)
docker exec bible-api pytest tests/ -v

# Single file
docker exec bible-api pytest tests/test_excerpt.py -v

# Single test
docker exec bible-api pytest tests/test_excerpt.py::test_function_name -v
```

Tests run inside the `bible-api` container — they need environment variables (`API_KEY`, `JWT_SECRET_KEY`, etc.).

## How It Works

`tests/conftest.py` sets `os.environ["DB_NAME"] = "cep_test"` **before** importing app modules. Therefore, `app/config.py` reads `DB_NAME=cep_test` on load and all connections go to the test database.

JWT tokens for admin endpoints are obtained via `TestClient` (no running server required).

## Test Types

### Unit Tests (safe)
- Use mocks (`@patch`)
- Do NOT make real DB queries
- Examples: `test_anomaly_correction.py`, `test_voice_manual_fixes.py`

### Integration Tests
- Use `TestClient` + real test database `cep_test`
- Examples: `test_*_integration.py`

## Seed Data

The file `tests/seed_test_data.sql` contains a minimal data set:
- `bible_books` — all 66 books
- `languages` — ru, en, uk
- `translations` — SYNO (code=1), BSB (code=16)
- `translation_books` — books for these translations
- `translation_verses` — gen 1:1, jhn 3:16-17
- `voices` — Bondarenko voice (code=1)
- `voice_alignments` — timecodes for seed verses
- `voice_anomalies` — 2 anomalies for tests
- `bible_stat` — data for gen 1, jhn 3

When adding new tests that require data — add records to `seed_test_data.sql` and rerun `setup_test_db.py`.

## Statistics

- **Unit tests:** 64
- **Integration tests:** 37
- **Total:** 101
