# Government Scheme Eligibility API

A FastAPI-based backend API that takes user profile inputs (age, income, caste, state, gender, occupation, disability status) and returns all government schemes they qualify for — with application links, deadlines, and benefit details.

## Why This Exists

India has 4,500+ central and state government schemes worth lakhs of crores in benefits. The majority of eligible citizens never claim them because there's no clean, developer-friendly way to query eligibility programmatically. This API fills that gap.

**Input:** User profile (age, gender, state, income, caste, occupation, disability status)
**Output:** List of matching schemes with eligibility reasons, benefit details, and application links

## Tech Stack

| Layer | Technology |
|---|---|
| Framework | FastAPI (async) |
| Database | PostgreSQL 16 |
| ORM | SQLAlchemy 2.0 + Alembic |
| Validation | Pydantic v2 |
| Auth | JWT (python-jose + passlib/bcrypt) |
| Caching | Redis 7 |
| Testing | Pytest + httpx (AsyncClient) |
| Deployment | Docker + Docker Compose |

## Quick Start

### Prerequisites

- Docker and Docker Compose installed
- Git

### Setup

```bash
# Clone the repository
git clone <repo-url>
cd govt-scheme-eligibility-api

# Start all services (FastAPI + PostgreSQL + Redis)
docker compose up -d --build

# Run database migrations
docker compose exec api alembic upgrade head

# Seed the database with 4,500+ real schemes
docker compose exec api python seed.py
```

The API is now running at **http://localhost:8000**

- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc
- Health Check: http://localhost:8000/health

### Environment Variables

Copy `.env.example` to `.env` and configure:

```env
DATABASE_URL=postgresql+asyncpg://schemes_user:schemes_pass@db:5432/schemes_db
REDIS_URL=redis://redis:6379
SECRET_KEY=your-secret-key-here
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
REFRESH_TOKEN_EXPIRE_DAYS=7
ENVIRONMENT=development
```

## API Endpoints

All endpoints are prefixed with `/api/v1`.

### Authentication

| Method | Endpoint | Description | Auth |
|--------|----------|-------------|------|
| POST | `/api/v1/auth/register` | Register new user | No |
| POST | `/api/v1/auth/login` | Login, get JWT tokens | No |
| POST | `/api/v1/auth/refresh` | Refresh expired token | No |
| GET | `/api/v1/auth/me` | Get current user profile | Yes |

### Eligibility

| Method | Endpoint | Description | Auth |
|--------|----------|-------------|------|
| POST | `/api/v1/eligibility/check` | Check scheme eligibility | No |
| GET | `/api/v1/eligibility/history` | View past checks | Yes |

### Schemes

| Method | Endpoint | Description | Auth |
|--------|----------|-------------|------|
| GET | `/api/v1/schemes` | List schemes (with filters) | No |
| GET | `/api/v1/schemes/search?q=keyword` | Search schemes | No |
| GET | `/api/v1/schemes/{id}` | Get scheme details | No |

### User Profile

| Method | Endpoint | Description | Auth |
|--------|----------|-------------|------|
| POST | `/api/v1/profile` | Save/update profile | Yes |
| GET | `/api/v1/profile` | Get saved profile | Yes |

### Admin (requires admin role)

| Method | Endpoint | Description | Auth |
|--------|----------|-------------|------|
| POST | `/api/v1/admin/schemes` | Create scheme | Admin |
| PUT | `/api/v1/admin/schemes/{id}` | Update scheme | Admin |
| DELETE | `/api/v1/admin/schemes/{id}` | Soft-delete scheme | Admin |
| POST | `/api/v1/admin/schemes/{id}/criteria` | Add criterion | Admin |
| DELETE | `/api/v1/admin/criteria/{id}` | Remove criterion | Admin |
| DELETE | `/api/v1/admin/cache/clear` | Flush Redis cache | Admin |

## Example: Check Eligibility

```bash
curl -X POST http://localhost:8000/api/v1/eligibility/check \
  -H "Content-Type: application/json" \
  -d '{
    "age": 25,
    "gender": "female",
    "annual_income": 180000,
    "state": "Tamil Nadu",
    "caste_category": "obc",
    "occupation": "farmer",
    "is_disabled": false
  }'
```

Response:
```json
{
  "profile_summary": {
    "age": 25,
    "gender": "female",
    "annual_income": 180000,
    "state": "Tamil Nadu",
    "caste_category": "obc",
    "occupation": "farmer"
  },
  "total_matched": 8,
  "schemes": [
    {
      "id": 3,
      "name": "PM Kisan Samman Nidhi",
      "ministry": "Ministry of Agriculture & Farmers Welfare",
      "benefit_amount": "Rs 6,000/year",
      "apply_link": "https://pmkisan.gov.in/",
      "category": "agriculture",
      "matched_because": [
        "occupation eq farmer: pass",
        "annual_income lte 200000: pass"
      ]
    }
  ]
}
```

## Architecture

```
app/
├── main.py              # FastAPI app, middleware, router registration
├── config.py            # Pydantic settings from environment
├── database.py          # Async SQLAlchemy engine + session
├── core/
│   ├── security.py      # Password hashing, JWT creation/verification
│   └── dependencies.py  # Auth dependencies (get_current_user, require_admin)
├── models/
│   ├── user.py          # User model
│   ├── scheme.py        # Scheme, State, scheme_state junction
│   ├── eligibility.py   # EligibilityCriteria model
│   └── profile.py       # UserProfile, EligibilityHistory
├── schemas/
│   ├── user.py          # Auth request/response schemas
│   ├── scheme.py        # Scheme + eligibility schemas
│   └── profile.py       # Profile + history schemas
├── routers/
│   ├── auth.py          # Authentication endpoints
│   ├── eligibility.py   # Eligibility check + scheme listing
│   ├── profile.py       # User profile + history
│   └── admin.py         # Admin CRUD for schemes
├── services/
│   ├── eligibility_engine.py  # Data-driven rule engine
│   └── cache_service.py       # Redis caching layer
└── data/
    └── schemes_seed.json      # 4,500+ verified schemes
```

### Rule Engine Design

The eligibility engine is **data-driven** — no hardcoded rules in Python. Each scheme has multiple `EligibilityCriteria` rows in the database:

| scheme_id | field | operator | value |
|-----------|-------|----------|-------|
| 1 | occupation | eq | farmer |
| 1 | annual_income | lte | 200000 |
| 1 | age | gte | 18 |

Supported operators: `eq`, `neq`, `gte`, `lte`, `gt`, `lt`, `in`, `not_in`, `contains`

Adding a new scheme requires **zero code changes** — just insert rows into the database.

## Running Tests

```bash
# Create test database first
docker compose exec db psql -U schemes_user -c "CREATE DATABASE schemes_test_db;"

# Run tests with coverage
docker compose exec api pytest --cov=app --cov-report=term-missing

# Run specific test file
docker compose exec api pytest tests/test_auth.py -v
```

## Data Sources

The 4,500+ schemes were collected from:
1. **MyScheme.gov.in** — Playwright scraper extracting structured scheme data
2. **data.gov.in** — Official open government CSV datasets
3. **Kaggle datasets** — Supplementary enrichment for eligibility criteria

All priority schemes (PM Kisan, Ayushman Bharat, PM Awas Yojana, etc.) were manually verified against official ministry websites.

## Default Admin Account

After seeding: `admin@schemesapi.gov.in` / `admin123`

Change these credentials immediately in production.

---

*Built with FastAPI, PostgreSQL, Redis, Docker*
