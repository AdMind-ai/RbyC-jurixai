# Docker Compose Deployment

Services:

- `web`: Django + Gunicorn
- `worker`: Celery worker
- `beat`: Celery beat
- `redis`: Redis broker/backend

## Run locally

```bash
docker compose up --build
```

## Run in production

Set `DJANGO_SETTINGS_MODULE=backend.aws_production` in the host environment or `.env`.

```bash
docker compose up -d --build
```

## Useful commands

```bash
docker compose ps
docker compose logs -f web
docker compose logs -f worker
docker compose logs -f beat
docker compose down
```
