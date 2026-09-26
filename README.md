# Dashboard API

Admin REST API for [Bible Garden](https://github.com/Bible-Garden) — data management, quality control, and export.

Built with FastAPI and MySQL.

## Setup

```bash
cp .env.example .env
# fill in DB credentials, API_KEY, JWT_SECRET_KEY in .env

docker compose up -d --build
```

The API will be available at `http://localhost:8084/api` (Swagger UI at `/docs`).

## Authorization

Two-level auth system:

1. **API Key** (`X-API-Key` header) — public GET endpoints
2. **JWT Token** (`Authorization: Bearer`) — administrative operations (24h TTL)

See [docs/SECURITY.md](docs/SECURITY.md) for details.

## Running Tests

```bash
# One-time setup
docker exec admin-api python tests/setup_test_db.py

# Unit tests only (safe, uses mocks)
docker exec admin-api pytest tests/ -k "not integration" -v

# All tests (uses test DB cep_test)
docker exec admin-api pytest tests/ -v
```

See [docs/TESTING.md](docs/TESTING.md) for details.

## Migrations

```bash
docker compose exec dashboard-api python3 migrate.py migrate          # run pending
docker compose exec dashboard-api python3 migrate.py create "name"    # create new
docker compose exec dashboard-api python3 migrate.py status            # show status
```

See [migrations/README.md](migrations/README.md) for details.

## Bible-API request statistics

This repository owns the `cep_public` statistics schema and serves it through
JWT-protected `/api/stats/summary` and `/api/stats/recent`. The summary includes
request counts, errors and average latency by `bible-garden`, `lampada`, `ops`
and historical `unknown` application. Recent requests expose and filter the
same application identity. The `API_KEY` in this repository authenticates
Dashboard-API reads; it is distinct from Bible-API's per-application keys.
Apply the statistics migration before deploying the new Bible-API writer.

## Documentation

- [docs/DEVELOPMENT.md](docs/DEVELOPMENT.md) — project structure, Docker commands, DB tables
- [docs/SECURITY.md](docs/SECURITY.md) — endpoint protection, authorization examples
- [docs/TESTING.md](docs/TESTING.md) — test setup and execution
- [docs/API_ANOMALIES.md](docs/API_ANOMALIES.md) — voice anomalies API, manual fixes logic
- [docs/AUDIO.md](docs/AUDIO.md) — MP3 downloading and storage
- [docs/REVERSE_PROXY_SETUP.md](docs/REVERSE_PROXY_SETUP.md) — Nginx reverse proxy setup
- [docs/iOS_TEST_CASES.md](docs/iOS_TEST_CASES.md) — iOS API test cases

## License

[GPLv3](LICENSE)
