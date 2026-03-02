# Development

## Quick Start

```bash
# Set up runtime variables
cp .env.example .env
nano .env

# Run in Docker
docker compose up -d --build

# Swagger UI
open http://localhost:8084/docs
```

## Docker Commands

```bash
# Start
docker compose up -d --build

# Logs
docker logs bible-api -f

# Restart
docker compose restart

# Stop
docker compose down
```

## Migrations

```bash
# Apply all migrations
python migrate.py migrate

# Create a new migration
python migrate.py create "migration_name"

# Status
python migrate.py status
```

See more: [../migrations/README.md](../migrations/README.md)

## OpenAPI Specification

```bash
# Export OpenAPI schema (executed in the container)
docker exec bible-api bash -c "cd /code && PYTHONPATH=app python3 extract-openapi.py app.main:app"
```

This will create an `openapi.yaml` file with the full API specification.

## Project Structure

```
app/
├── main.py           # Main FastAPI application
├── auth.py           # Authorization (API Key, JWT)
├── excerpt.py        # Endpoints for chapters and excerpts
├── audio.py          # Audio files (Range requests, fallback)
├── checks.py         # DB checks
├── models.py         # Pydantic models
├── database.py       # DB connection
└── config.py         # Configuration from environment variables
```

## DB Tables

### Translations and Texts

- **`languages`** - Bible languages
- **`translations`** - Bible translations
- **`translation_books`** - books in a translation
- **`translation_verses`** - verses with text
- **`bible_stat`** - reference verse counts (for validation)

### Voices and Audio

- **`voices`** - translation voice narrations
- **`voice_alignments`** - word timings in voice narration (begin/end for each word)
- **`voice_manual_fixes`** - manual timing corrections
  - Takes priority over `voice_alignments`
  - SQL: `COALESCE(vmf.begin, a.begin)`
- **`voice_anomalies`** - automatically detected issues
  - Types: `fast`, `slow`, `long`, `short`, `manual`
  - Statuses: `detected`, `confirmed`, `disproved`, `corrected`, `already_resolved`, `disproved_whisper`

### Service Tables

- **`migrations`** - DB migration history
