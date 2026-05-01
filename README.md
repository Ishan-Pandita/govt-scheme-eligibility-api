# Government Scheme Eligibility API

A private FastAPI backend that evaluates a citizen profile against structured Indian government scheme rules and returns the schemes the person may qualify for, including benefits, eligibility reasons, and application links.

This project turns scheme discovery into a developer-friendly API. A bank, NGO, student portal, CSC center, or chatbot can send a user profile and receive matching schemes instead of hardcoding eligibility logic in each application.

## Highlights

- FastAPI REST API with Swagger and ReDoc documentation
- PostgreSQL schema with SQLAlchemy 2.0 and Alembic migrations
- Data-driven eligibility rule engine, so new schemes can be added without code changes
- 4,500+ seeded scheme records from collected/structured public scheme data
- Private-by-default API using `X-API-Key`
- JWT authentication for user and admin flows
- Admin-only scheme and criteria management
- PostgreSQL full-text search with GIN index
- In-memory eligibility cache, no Redis required for local use
- Profile saving and authenticated eligibility history
- Scripted test suite with 52 passing tests

## Why This Project Matters

Government benefits are difficult to discover because eligibility depends on age, income, caste category, state, gender, occupation, disability status, student status, and other conditions. This API centralizes those rules and exposes them through one consistent interface.

The core design choice is the rule engine. Eligibility criteria are stored as database rows:

| field | operator | value |
|---|---|---|
| occupation | eq | farmer |
| annual_income | lte | 200000 |
| age | gte | 18 |

That makes the system extensible: adding or updating a scheme is a data operation, not a code deployment.

## Tech Stack

| Layer | Technology |
|---|---|
| API | FastAPI |
| Database | PostgreSQL |
| ORM and migrations | SQLAlchemy 2.0, Alembic |
| Validation | Pydantic v2 |
| Auth | API key, JWT, python-jose, passlib |
| Cache | In-memory async cache |
| Search | PostgreSQL full-text search |
| Tests | Pytest, pytest-asyncio, httpx |
| Deployment | Docker, Docker Compose |

## Security Model

The API is private by default.

Every `/api/v1/*` endpoint requires:

```text
X-API-Key: <PRIVATE_API_KEY>
```

Admin endpoints require both:

```text
X-API-Key: <PRIVATE_API_KEY>
Authorization: Bearer <admin_access_token>
```

Do not commit real secrets. Put them only in `.env`. The `.env` file is ignored by Git.

## Project Structure

```text
app/
  main.py                    FastAPI app, middleware, router registration
  config.py                  Environment-based settings
  database.py                Async SQLAlchemy engine and session
  core/
    api_key.py               Private API key dependency
    dependencies.py          JWT user/admin dependencies
    rate_limit.py            slowapi limiter
    security.py              Password hashing and JWT helpers
  models/                    SQLAlchemy models
  routers/                   Auth, eligibility, profile, admin routes
  schemas/                   Pydantic request/response schemas
  services/
    eligibility_engine.py    Data-driven rule engine
    cache_service.py         Cache abstraction
    memory_redis.py          In-memory cache backend
  data/
    schemes_seed.json        Seed data for schemes and criteria
alembic/                     Database migrations
scraper/                     Data collection and conversion scripts
tests/                       Automated API and service tests
scripts/                     Local run/test helper scripts
```

## Prerequisites

- Python 3.12
- PostgreSQL running locally
- A virtual environment with dependencies installed

Redis is not required. The API uses an in-memory cache by default because caching is a performance optimization, not a correctness requirement.

## Environment Setup

Create `.env` from `.env.example`:

```powershell
copy .env.example .env
```

Then set private local values:

```env
DATABASE_URL=postgresql+asyncpg://schemes_user:schemes_pass@localhost:5432/schemes_db
REDIS_URL=memory://local
SECRET_KEY=replace-with-a-long-random-secret
PRIVATE_API_KEY=replace-with-your-private-api-key
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
REFRESH_TOKEN_EXPIRE_DAYS=7
ENVIRONMENT=development
SQL_ECHO=false
ADMIN_EMAIL=your-admin-email@example.com
ADMIN_PASSWORD=your-private-admin-password
```

Use strong values for `SECRET_KEY`, `PRIVATE_API_KEY`, and `ADMIN_PASSWORD`.

## Run Locally

From the project root:

```powershell
.\venv\Scripts\Activate.ps1
python -m alembic upgrade head
python seed.py
python -m uvicorn app.main:app --reload
```

Open:

```text
http://localhost:8000/docs
```

Daily development run after the database has already been migrated and seeded:

```powershell
python -m uvicorn app.main:app --reload
```

Helper script:

```powershell
powershell -ExecutionPolicy Bypass -File scripts/run_api.ps1
```

Skip seeding with:

```powershell
powershell -ExecutionPolicy Bypass -File scripts/run_api.ps1 -SkipSeed
```

## Health Check

```powershell
Invoke-RestMethod http://localhost:8000/health
```

Expected shape:

```json
{
  "status": "ok",
  "database": "connected",
  "cache": "connected",
  "cache_backend": "memory"
}
```

## Use The API

All versioned endpoints require the private API key.

PowerShell example:

```powershell
$headers = @{
  "X-API-Key" = "<your-private-api-key>"
}

$body = @{
  age = 30
  gender = "male"
  annual_income = 150000
  state = "Tamil Nadu"
  caste_category = "obc"
  occupation = "farmer"
  is_disabled = $false
} | ConvertTo-Json

Invoke-RestMethod `
  -Uri "http://localhost:8000/api/v1/eligibility/check" `
  -Method Post `
  -Headers $headers `
  -ContentType "application/json" `
  -Body $body
```

Response shape:

```json
{
  "profile_summary": {
    "age": 30,
    "gender": "male",
    "annual_income": 150000,
    "state": "Tamil Nadu",
    "caste_category": "obc",
    "occupation": "farmer",
    "is_disabled": false
  },
  "total_matched": 3,
  "schemes": [
    {
      "id": 1,
      "name": "Example Scheme",
      "ministry": "Example Ministry",
      "benefit_amount": "Rs 6000/year",
      "apply_link": "https://example.gov.in",
      "category": "agriculture",
      "matched_because": [
        "occupation eq farmer: pass",
        "annual_income lte 200000: pass"
      ]
    }
  ]
}
```

## Swagger Testing

1. Start the API.
2. Open `http://localhost:8000/docs`.
3. Click **Authorize**.
4. Paste your `PRIVATE_API_KEY` into the API key field.
5. Test public-private endpoints such as `/api/v1/eligibility/check`.

For admin routes:

1. Use `/api/v1/auth/login` with `ADMIN_EMAIL` and `ADMIN_PASSWORD` from `.env`.
2. Copy the returned `access_token`.
3. Click **Authorize** again.
4. Paste the token into the bearer token field.
5. Call `/api/v1/admin/*` endpoints.

## Main Endpoints

| Method | Endpoint | Purpose | Auth |
|---|---|---|---|
| POST | `/api/v1/auth/register` | Create user | API key |
| POST | `/api/v1/auth/login` | Get access and refresh tokens | API key |
| POST | `/api/v1/auth/refresh` | Refresh tokens | API key |
| GET | `/api/v1/auth/me` | Current user | API key + JWT |
| POST | `/api/v1/eligibility/check` | Match a profile to schemes | API key |
| GET | `/api/v1/eligibility/history` | User eligibility history | API key + JWT |
| GET | `/api/v1/schemes` | List schemes with filters | API key |
| GET | `/api/v1/schemes/search?q=keyword` | Full-text scheme search | API key |
| GET | `/api/v1/schemes/{id}` | Scheme details | API key |
| POST | `/api/v1/profile` | Save user profile | API key + JWT |
| GET | `/api/v1/profile` | Get saved profile | API key + JWT |
| POST | `/api/v1/admin/schemes` | Create scheme | API key + admin JWT |
| PUT | `/api/v1/admin/schemes/{id}` | Update scheme | API key + admin JWT |
| DELETE | `/api/v1/admin/schemes/{id}` | Soft-delete scheme | API key + admin JWT |
| POST | `/api/v1/admin/schemes/{id}/criteria` | Add criterion | API key + admin JWT |
| DELETE | `/api/v1/admin/criteria/{id}` | Delete criterion | API key + admin JWT |
| DELETE | `/api/v1/admin/cache/clear` | Clear eligibility cache | API key + admin JWT |

## Run Tests

```powershell
python -m pytest
```

With coverage:

```powershell
powershell -ExecutionPolicy Bypass -File scripts/run_tests.ps1
```

Current verification status:

```text
52 passed
```

The test suite covers:

- Registration, login, refresh, and `/auth/me`
- Private API key enforcement
- Eligibility rule operators
- Eligibility matching and cache headers
- Scheme listing, filtering, search, and detail lookup
- Profile save/get
- Eligibility history
- Admin authorization and scheme management

## Data And Seeding

The seed script loads:

- Indian states and union territories
- Scheme metadata
- Scheme-to-state links
- Eligibility criteria
- Admin account from `.env`

Run seeding once after database setup:

```powershell
python seed.py
```

You do not need to seed every time. The script is idempotent: existing schemes are skipped and the admin account is updated from `.env`.

## Docker Option

Docker Compose runs the API and PostgreSQL:

```powershell
docker compose up -d --build
docker compose exec api alembic upgrade head
docker compose exec api python seed.py
```

The default Docker setup still uses the in-memory cache. Redis can be reintroduced later if the API is deployed with multiple workers or high traffic.

## Recruiter Notes

This project demonstrates backend engineering across:

- API design with protected public and admin surfaces
- Relational data modeling for real-world eligibility rules
- Async SQLAlchemy with migrations
- JWT authentication and role-based authorization
- API key based private access control
- Rule-engine design instead of hardcoded business logic
- PostgreSQL full-text search
- Automated test coverage across auth, admin, eligibility, and profiles
- Docker-ready local deployment
- Practical tradeoff decisions, such as removing Redis as a required dependency for a simpler local build

## Important Disclaimer

Government scheme eligibility can change. This project is a technical backend and portfolio-quality API. Before real-world public use, scheme data and eligibility rules should be reviewed and verified against official government sources.
