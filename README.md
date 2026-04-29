# Finance Reconciliation System

A Django-based finance automation system that ingests raw financial data (bank statements + internal ledgers), performs intelligent reconciliation using confidence scoring, auto-categorizes transactions, and visualizes insights through a dashboard and REST APIs.

Built for the Data & Automation Intern assignment at Pilgrim.

## What it does

1. **Ingests CSVs** — upload bank statements and internal ledger files via API or the dashboard UI. Duplicates are detected using SHA-256 hashing and skipped automatically.

2. **Reconciles transactions** — matches bank entries against internal records using a weighted scoring system:
   - Amount match (40 pts) — exact match = 40, within 1% tolerance = 20
   - Date proximity (30 pts) — same day = 30, ±1 day = 20, ±2 days = 10
   - Narration similarity (30 pts) — fuzzy string matching via SequenceMatcher

   Entries scoring ≥80 are auto-matched, 60-79 are flagged as probable, below 60 are unmatched.

3. **Auto-categorizes** — 15 built-in regex rules classify transactions into categories (Food, Transport, Utilities, etc.) based on narration text. Categories like "Swiggy" → Food & Dining, "Uber" → Transport. Rules are extensible via the admin panel.

4. **Flags anomalies** — transactions exceeding category-specific thresholds are flagged (e.g., a ₹5,000 food expense when the typical threshold is ₹2,000).

5. **Builds a unified ledger** — normalizes data from both sources into a single ledger table with reconciliation status, confidence scores, and anomaly flags.

## Tech Stack

- **Backend**: Django 5.x + Django REST Framework
- **Database**: PostgreSQL (SQLite for local dev)
- **Dashboard**: Django templates + Chart.js
- **Background tasks**: Celery + Redis
- **API docs**: Swagger/OpenAPI via drf-spectacular
- **Deployment**: Docker + Railway
- **Power BI**: CSV export endpoint for direct connection

## API Endpoints

| Endpoint | Method | Description |
|---|---|---|
| `/api/upload/bank/` | POST | Upload bank_statement.csv |
| `/api/upload/ledger/` | POST | Upload internal_ledger.csv |
| `/api/reconcile/` | POST | Run reconciliation engine |
| `/api/summary/` | GET | Financial KPIs (credits, debits, match rate) |
| `/api/reconciliation/` | GET | Matched/unmatched entries with confidence scores |
| `/api/category-breakdown/` | GET | Expenses grouped by category |
| `/api/anomalies/` | GET | Flagged unusual transactions |
| `/api/export/powerbi/` | GET | CSV download for Power BI |
| `/api/ledger/` | GET | Full normalized ledger |
| `/api/docs/` | GET | Swagger UI |

## Quick Start

### Local (SQLite)
```bash
python -m venv venv
source venv/bin/activate   # Windows: venv\Scripts\activate
pip install -r requirements.txt
python manage.py migrate
python manage.py generate_sample_data
python manage.py runserver
```

Then open http://localhost:8000, upload the sample CSVs from `sample_data/`, and hit "Run Reconciliation".

### Docker (PostgreSQL + Redis)
```bash
docker-compose up --build
```

Opens at http://localhost:8000. Includes PostgreSQL and Redis for Celery.

## Project Structure

```
pilgrim-finance/
├── config/                 # Django project settings, URLs, Celery
├── finance/                # Core app
│   ├── models.py           # BankTransaction, InternalLedgerEntry, Ledger, etc.
│   ├── reconciliation.py   # Matching engine with confidence scoring
│   ├── categorizer.py      # Regex-based auto-categorization
│   ├── views.py            # REST API endpoints
│   ├── serializers.py      # DRF serializers
│   ├── tasks.py            # Celery background tasks
│   └── management/commands/
│       └── generate_sample_data.py
├── dashboard/              # Web dashboard (Django templates + Chart.js)
├── sample_data/            # Pre-generated test CSVs
├── Dockerfile
├── docker-compose.yml
└── requirements.txt
```

## Sample Data

The included CSVs contain ~45 bank transactions and ~43 internal ledger entries with deliberate edge cases:

- Exact matches (same amount, same day)
- Date offsets (±1-2 days between bank and internal)
- Fuzzy narrations ("SWIGGY ORDER #4521" vs "Swiggy Order")
- Unmatched transactions on both sides
- One duplicate entry for dedup testing
- Indian vendors (Swiggy, Zomato, Jio, Airtel, etc.) for auto-categorization

## Reconciliation Results (sample data)

| Metric | Value |
|---|---|
| Bank transactions | 44 |
| Internal entries | 43 |
| Auto-matched (≥80) | 21 |
| Probable (60-79) | 15 |
| Unmatched | 15 |
| Match rate | 82.8% |
| Anomalies flagged | 8 |
| Categories detected | 16 |
