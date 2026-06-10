# ArthaOS

ArthaOS is a financial operating system MVP for Indian freelancers, creators, consultants, gig workers, and small business owners. Upload a bank statement and get categorized transactions, dashboard metrics, charts, a P&L PDF, tax estimates, and CFO-style answers.

## Stack

- Frontend: Next.js 15, TypeScript, TailwindCSS, ShadCN-style primitives, Recharts
- Backend: FastAPI, SQLAlchemy, JWT auth, local file storage
- Database: PostgreSQL in Docker, SQLite-compatible local defaults
- AI: OpenAI-compatible chat completions endpoint with deterministic fallbacks

## Quick Start

```bash
cp .env.example .env
docker compose up --build
```

Open:

- Frontend: http://localhost:3000
- Backend health: http://localhost:8000/health
- API docs: http://localhost:8000/docs

## Local Development

Backend:

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload
pytest
```

Frontend:

```bash
cd frontend
npm install
npm run dev
```

## Statement Format

CSV uploads support common bank-style headers such as:

```csv
Date,Narration,Debit,Credit
2026-01-05,STARBUCKS,400,
2026-01-06,UPWORK GLOBAL,,50000
```

Supported MVP banks: HDFC, SBI, ICICI, Axis. PDF support is best-effort for text-based PDFs with extractable tabular rows.

## API Overview

- `POST /api/v1/auth/register`
- `POST /api/v1/auth/login`
- `GET /api/v1/dashboard`
- `POST /api/v1/upload`
- `POST /api/v1/chat`
- `GET /api/v1/reports/latest.pdf`

## Security Notes

- Passwords are hashed with bcrypt through Passlib.
- JWT protects all finance endpoints.
- SQLAlchemy parameterization protects database access from SQL injection.
- Uploads are limited to CSV/PDF and 10MB.
- SlowAPI applies a default per-IP rate limit.
- Replace `JWT_SECRET` before deploying.

## MVP Tax Logic

Tax is estimated from annual profit:

- 0-3 lakh: 0%
- 3-7 lakh: 5%
- 7-10 lakh: 10%
- 10 lakh+: 20%

This is a simplified MVP estimate, not tax advice.
