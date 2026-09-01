# Production Deployment Security Baseline

Before starting the backend in production, inject these environment variables through the secret manager or deployment platform:

- `ENVIRONMENT=production`
- `SECRET_KEY` with at least 32 random characters
- `AI_DB_PASSWORD` for a dedicated application database user
- `CORS_ORIGINS` as a comma-separated allowlist of trusted HTTPS origins
- `CREATE_TABLES_ON_STARTUP=false`

Production startup runs `backend/sql/migrations/*.sql` through the controlled migration runner. Each migration is recorded in `ai_schema_migration` with a SHA-256 checksum. A checksum change or SQL failure stops startup and must be resolved before deployment.

Use a TLS-terminating reverse proxy in front of the application. Redirect HTTP to HTTPS, enable HSTS, and keep certificates and renewal outside the application container. Do not commit database passwords, JWT keys, or AI API keys to compose files or source control.
