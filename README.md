# Customer Data Pipeline

A data pipeline built with Flask, FastAPI, and PostgreSQL — fully containerised with Docker Compose.

```
Flask Mock API  ──►  FastAPI Pipeline  ──►  PostgreSQL (Neon)
  (port 5000)           (port 8000)
```

---

## Tech Stack

| Layer    | Technology              |
|----------|-------------------------|
| Mock API | Flask 3 + Gunicorn      |
| Pipeline | FastAPI + Uvicorn       |
| Database | PostgreSQL via Neon     |
| ORM      | SQLAlchemy 2            |
| HTTP     | httpx (async)           |
| Infra    | Docker + Docker Compose |

---

## Services

| Service            | Port | Description                                  |
|--------------------|------|----------------------------------------------|
| `mock-server`      | 5000 | Flask — serves 25 customer records from JSON |
| `pipeline-service` | 8000 | FastAPI — ingests data into PostgreSQL        |

---

## Project Structure

```
customer-pipeline/
├── docker-compose.yml
├── .env.example
├── README.md
├── mock-server/
│   ├── app.py
│   ├── Dockerfile
│   ├── requirements.txt
│   └── data/
│       └── customers.json
└── pipeline-service/
    ├── main.py
    ├── database.py
    ├── Dockerfile
    ├── requirements.txt
    ├── models/
    │   └── customer.py
    └── services/
        └── ingestion.py
```

---

## Setup

### Prerequisites
- Docker Desktop (running)
- Python 3.10+
- Git

### 1. Clone the repo
```bash
git clone <repo-url>
cd customer-pipeline
```

### 2. Create your `.env`
```bash
cp .env.example .env
```
Open `.env` and fill in your Neon database URL:
```env
DATABASE_URL=postgresql://<user>:<password>@<host>/neondb?sslmode=require
```

### 3. Start all services
```bash
docker-compose up -d --build
```

### 4. Wait for services to be healthy
```bash
docker-compose ps
```
All services should show `running (healthy)` before proceeding.

---

## API Reference

### Flask Mock Server — port 5000

#### `GET /api/health`
Returns service liveness and metadata.
```bash
curl http://localhost:5000/api/health
```
```json
{
  "status": "healthy",
  "service": "customer-mock-server",
  "version": "1.0.0",
  "uptime_seconds": 12.4,
  "record_count": 25
}
```

---

#### `GET /api/customers`
Returns paginated customer list. Supports optional search filter.

| Param    | Type   | Default | Description                          |
|----------|--------|---------|--------------------------------------|
| `page`   | int    | 1       | Page number (1-indexed)              |
| `limit`  | int    | 10      | Records per page (max 100)           |
| `search` | string | —       | Filter by name or email (optional)   |

```bash
curl "http://localhost:5000/api/customers?page=1&limit=5"
curl "http://localhost:5000/api/customers?search=bengaluru"
```
```json
{
  "data": [ "..." ],
  "total": 25,
  "page": 1,
  "limit": 5,
  "pages": 5
}
```

---

#### `GET /api/customers/{id}`
Returns a single customer by ID.
```bash
curl http://localhost:5000/api/customers/CUST-0001
```
Returns `404` if not found:
```json
{
  "error": "Customer 'CUST-0001' not found.",
  "status_code": 404
}
```

---

### FastAPI Pipeline Service — port 8000

#### `POST /api/ingest`
Fetches all customers from Flask (auto-handles pagination) and upserts into PostgreSQL. Safe to call multiple times — no duplicates created.

```bash
curl -X POST http://localhost:8000/api/ingest
```
```json
{
  "status": "success",
  "records_processed": 25
}
```

---

#### `GET /api/customers`
Returns paginated customer list from PostgreSQL.

| Param   | Type | Default | Description             |
|---------|------|---------|-------------------------|
| `page`  | int  | 1       | Page number (1-indexed) |
| `limit` | int  | 10      | Records per page        |

```bash
curl "http://localhost:8000/api/customers?page=1&limit=5"
```

---

#### `GET /api/customers/{id}`
Returns a single customer from PostgreSQL.
```bash
curl http://localhost:8000/api/customers/CUST-0001
```
Returns `404` if not found.

---

## Full Test Flow

```bash
# 1. health check Flask
curl http://localhost:5000/api/health

# 2. verify Flask serves data
curl "http://localhost:5000/api/customers?page=1&limit=5"

# 3. ingest into PostgreSQL
curl -X POST http://localhost:8000/api/ingest

# 4. query from PostgreSQL
curl "http://localhost:8000/api/customers?page=1&limit=5"

# 5. single record
curl http://localhost:8000/api/customers/CUST-0001

# 6. 404 test
curl http://localhost:8000/api/customers/CUST-9999
```

---

## Swagger UI

FastAPI auto-generates interactive API docs at:
```
http://localhost:8000/docs
```

---

## Database Schema

```sql
CREATE TABLE customers (
    customer_id     VARCHAR(50)    PRIMARY KEY,
    first_name      VARCHAR(100)   NOT NULL,
    last_name       VARCHAR(100)   NOT NULL,
    email           VARCHAR(255)   NOT NULL,
    phone           VARCHAR(20),
    address         TEXT,
    date_of_birth   DATE,
    account_balance DECIMAL(15,2),
    created_at      TIMESTAMP
);
```

---

## Upsert Logic

Running `POST /api/ingest` multiple times is safe. It uses PostgreSQL's `INSERT ... ON CONFLICT DO UPDATE` — existing records are updated, no duplicates are created.

---

## Logs

```bash
# all services
docker-compose logs -f

# individual service
docker-compose logs -f mock-server
docker-compose logs -f pipeline-service
```

---

## Shutdown

```bash
docker-compose down
```