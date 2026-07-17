# Project Overview

Full-stack AI-powered legal/compliance assistant web application.

## Stack

- **Frontend**: React 19 + TypeScript + Vite, Material UI, TailwindCSS — in `/frontend`
- **Backend**: Django 5 + Django REST Framework + Celery — in `/backend`
- **Original deployment**: Docker Compose (see `/infra`)

## Key Features

- AI chat (OpenAI integration)
- Document search and compliance checking
- Document translation (DeepL)
- Corporate secretary tools (Segreteria Societaria)
- Billing/usage tracking (Stripe)
- Perplexity AI integration

## Running Locally on Replit

### Frontend (dev server)
```bash
cd frontend && npm install && npm run dev
```

### Backend (Django)
```bash
cd backend && pip install -r requirements.txt && python manage.py runserver
```

The backend requires at minimum these environment variables:
- `OPENAI_KEY` — required
- `DEEPL_KEY` — required
- Many optional: AWS credentials, Stripe, Vera API, Perplexity, etc.

## Project Structure

```
frontend/   React + Vite app
backend/    Django project
  core/         main models (chat, documents, companies)
  billing/      usage & cost tracking
  infra/    Docker Compose deployment config
```

## User Preferences

- Language: Italian preferred for communication
