# Security and Authorization

## Architecture

The API uses a two-level authorization system:

1. **API Key** (`X-API-Key`) - for public GET endpoints
2. **JWT Token** (`Authorization: Bearer`) - for administrative operations

## Protected Endpoints

| Endpoint | Method | Protection | Purpose |
|----------|--------|------------|---------|
| `/auth/login` | POST | - | Obtain JWT token |
| `/languages` | GET | API Key | List of languages |
| `/translations` | GET | API Key | List of translations |
| `/translation_info` | GET | API Key | Translation information |
| `/translations/{code}/books` | GET | API Key | Translation books |
| `/chapter_with_alignment` | GET | API Key | Chapter with alignment |
| `/excerpt_with_alignment` | GET | API Key | Excerpt with alignment |
| `/audio/{translation}/{voice}/{book}/{chapter}.mp3` | GET | API Key* | Audio files |
| `/translations/{code}` | PUT | JWT | Update translation |
| `/voices/{code}` | PUT | JWT | Update voice |
| `/voices/{code}/anomalies` | GET | JWT | List of anomalies |
| `/voices/anomalies` | POST | JWT | Create anomaly |
| `/voices/anomalies/{code}/status` | PATCH | JWT | Update status |
| `/voices/manual-fixes` | POST | JWT | Manual correction |
| `/cache/clear` | POST | JWT | Clear cache |
| `/check_translation` | GET | JWT | Translation check |
| `/check_voice` | GET | JWT | Voice check |

**\*** The audio endpoint supports the API key both in the `X-API-Key` header and as a query parameter `?api_key=...` (for compatibility with HTML `<audio>` elements)

## Configuration

All parameters are set via environment variables (see `.env.example`):

```
API_KEY=your-api-key-here
JWT_SECRET_KEY=your-secret-key        # openssl rand -hex 32
JWT_ALGORITHM=HS256
JWT_EXPIRE_HOURS=24
ADMIN_USERNAME=admin
ADMIN_PASSWORD_HASH=$$2b$$12$$...     # bcrypt hash ($ is escaped as $$ for docker-compose)
```

### Generating a Password Hash

```bash
python -c "import bcrypt; print(bcrypt.hashpw(b'your_password', bcrypt.gensalt()).decode('utf-8'))"
```

## Usage

### API Key (public endpoints)

```bash
# Via header (recommended)
curl -H "X-API-Key: your-api-key" \
  http://localhost:8084/api/translations

# Audio via query parameter (for <audio> elements)
curl "http://localhost:8084/api/audio/syn/bondarenko/01/01.mp3?api_key=your-api-key"
```

### JWT Token (administrative endpoints)

```bash
# 1. Obtain token
TOKEN=$(curl -s -X POST http://localhost:8084/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"your_password"}' | jq -r .access_token)

# 2. Use token
curl -H "Authorization: Bearer $TOKEN" \
  http://localhost:8084/api/voices/1/anomalies
```

## Implementation

- **`app/auth.py`** - authorization functions and FastAPI dependencies
- **`app/config.py`** - security settings (loaded from environment variables)
