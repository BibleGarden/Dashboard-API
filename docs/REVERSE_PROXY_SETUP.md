# Reverse Proxy (optional)

By default, `bible-api` is available directly on port `8084` (host) -> `8000` (container).

If needed, you can place an Nginx reverse proxy in front of the API.

## Example Nginx Configuration

The `deploy/nginx/default.conf` file contains an example configuration with:
- Proxying `/api/*`, `/docs`, `/openapi.json`, `/redoc` to FastAPI
- Static site on the domain root
- Support for a separate API domain (`api.yourdomain.com`)

## Architecture with Reverse Proxy

```
Client -> Nginx (:80) -> bible-api (:8000)
```

- Nginx connects to the `bible-api` container by service name within the Docker network
- FastAPI is not directly accessible from outside (uses `expose` instead of `ports`)

## Architecture without Reverse Proxy (current)

```
Client -> bible-api (:8084 -> :8000)
```

The current `docker-compose.yml` uses direct port mapping without Nginx.
