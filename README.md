# Maillard Back Office

Internal invoice processing system for Maillard.
**Upload → OCR/Parse → Extract → Store → Compare** supplier invoices.

## Stack

- **Backend:** FastAPI + SQLAlchemy + Alembic (Python 3.11+)
- **Database:** PostgreSQL 15
- **OCR:** Tesseract via pytesseract
- **PDF parsing:** PyMuPDF (text PDFs), Tesseract (scanned)
- **Frontend:** Retool (quick start) or React/Next.js (later)
- **Storage:** Local filesystem (dev) / S3 (prod)

## Quick Start

```bash
# 1. Copy env file and fill in values
cp .env.example .env

# 2. Start Postgres + backend
docker compose up -d

# 3. Run migrations
docker compose exec backend alembic upgrade head

# 4. Seed vendor data (optional)
docker compose exec backend python scripts/seed_vendors.py

# 5. Open API docs
open http://localhost:8000/docs
```

## Project Structure

```
backend/app/
  main.py              # FastAPI entrypoint
  core/                # config, logging
  db/                  # models, session, migrations
  api/routes/          # REST endpoints
  services/            # business logic
    ingestion/         # upload pipeline orchestration
    ocr/               # Tesseract wrapper + preprocessing
    pdf/               # text & scanned PDF extraction
    extraction/        # field parsing, normalization
    pricing/           # vendor price comparison
    units.py           # unit conversion (g/oz/lb/kg, ml/L/gal, case-pack)
  schemas/             # Pydantic models
  utils/               # helpers
  tests/               # pytest
```

## Quantity & Unit Handling

Invoices use varied formats:

| Invoice text | Parsed as |
|---|---|
| `5/20 oz` | 5 cases × 20 oz = 100 oz → 2834.95 g |
| `3x24 gal` | 3 cases × 24 gal = 72 gal → 272,549 ml |
| `10 lb` | 10 lb → 4535.92 g |
| `3 cases` | 3 cases → 3 ea |

Each **Product** has a `compare_mode` (weight / volume / count / none) and an optional
`base_unit` so the system knows how to normalize prices for apples-to-apples comparison.

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/health` | Health check |
| POST | `/api/v1/upload` | Upload invoice file |
| GET | `/api/v1/invoices` | List/search invoices |
| GET | `/api/v1/invoices/{id}` | Invoice detail with line items |
| GET | `/api/v1/vendors` | List vendors |
| POST | `/api/v1/vendors` | Create vendor |
| GET | `/api/v1/pricing/compare` | Price comparison across vendors |
