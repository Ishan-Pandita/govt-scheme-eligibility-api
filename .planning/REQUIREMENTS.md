# Requirements: Government Scheme Eligibility API

**Defined:** 2026-04-26
**Core Value:** Given a user profile, instantly return every government scheme they're eligible for with actionable application details.

## v1 Requirements

Requirements for initial release. Each maps to roadmap phases.

### Setup & Infrastructure

- [ ] **INFRA-01**: Project follows defined folder structure (app/, scraper/, alembic/, tests/)
- [ ] **INFRA-02**: Virtual environment with all dependencies in requirements.txt
- [ ] **INFRA-03**: Docker Compose runs FastAPI + PostgreSQL + Redis with single command
- [ ] **INFRA-04**: Dockerfile builds Python app correctly
- [ ] **INFRA-05**: Environment variables configured via .env file
- [ ] **INFRA-06**: Alembic initialized for database migrations
- [ ] **INFRA-07**: Health endpoint returns `{"status": "ok"}` at `/health`

### Database Models

- [ ] **DB-01**: User model with id, email, hashed_password, created_at
- [ ] **DB-02**: Scheme model with id, name, description, ministry, type, benefit_amount, apply_link, is_active
- [ ] **DB-03**: EligibilityCriteria model with id, scheme_id, field, operator, value
- [ ] **DB-04**: State model and SchemeState junction table for state-specific schemes
- [ ] **DB-05**: Alembic migration runs successfully and creates all tables
- [ ] **DB-06**: Tables verified in PostgreSQL

### Data Collection

- [ ] **DATA-01**: Playwright scraper extracts scheme data from MyScheme.gov.in
- [ ] **DATA-02**: data.gov.in downloader parses CSV datasets
- [ ] **DATA-03**: Raw scheme data structured into EligibilityCriteria format
- [ ] **DATA-04**: 20-30 schemes manually verified against official ministry pages
- [ ] **DATA-05**: Clean schemes_seed.json created with verified data
- [ ] **DATA-06**: Seed script inserts data into PostgreSQL
- [ ] **DATA-07**: Database contains 500+ real schemes after seeding

### Authentication

- [ ] **AUTH-01**: User can register with email and password via POST /auth/register
- [ ] **AUTH-02**: User can login and receive access + refresh JWT tokens via POST /auth/login
- [ ] **AUTH-03**: User can view their profile via GET /auth/me (requires valid token)
- [ ] **AUTH-04**: get_current_user dependency validates tokens via OAuth2PasswordBearer
- [ ] **AUTH-05**: User can refresh expired access token via POST /auth/refresh
- [ ] **AUTH-06**: Passwords are hashed with passlib + bcrypt

### Eligibility Engine

- [ ] **ENGINE-01**: EligibilityEngine class supports operators: eq, neq, gte, lte, gt, lt, in, not_in, contains
- [ ] **ENGINE-02**: evaluate_criterion function correctly matches user profile against single criterion
- [ ] **ENGINE-03**: get_eligible_schemes function returns all matching schemes for a user profile
- [ ] **ENGINE-04**: Engine handles null/optional criteria (missing fields skip that check)
- [ ] **ENGINE-05**: Unit tests pass for engine with mock profiles

### API Endpoints

- [ ] **API-01**: POST /eligibility/check takes user profile and returns matched schemes with reasons
- [ ] **API-02**: GET /eligibility/schemes/{scheme_id} returns full scheme details
- [ ] **API-03**: GET /schemes/ lists all schemes with filters (state, category, gender)
- [ ] **API-04**: GET /schemes/search?q=keyword performs full-text search using PostgreSQL tsvector
- [ ] **API-05**: List endpoints support pagination (skip, limit)
- [ ] **API-06**: All endpoints have Pydantic response models

### Caching

- [ ] **CACHE-01**: aioredis async client connects to Redis
- [ ] **CACHE-02**: CacheService class with get, set, delete methods
- [ ] **CACHE-03**: Cache key generated from MD5/SHA256 hash of sorted user profile
- [ ] **CACHE-04**: Eligibility endpoint checks cache first, computes on miss, stores with 1-hour TTL
- [ ] **CACHE-05**: X-Cache: HIT/MISS header appears in response
- [ ] **CACHE-06**: Admin endpoint DELETE /admin/cache/clear flushes Redis

### User Profiles & History

- [ ] **PROF-01**: UserProfile model linked to User with all eligibility fields
- [ ] **PROF-02**: EligibilityHistory model stores profile snapshot, results snapshot, checked_at
- [ ] **PROF-03**: POST /profile saves/updates user profile
- [ ] **PROF-04**: GET /profile returns saved profile
- [ ] **PROF-05**: Eligibility checks auto-save to history for authenticated users
- [ ] **PROF-06**: GET /eligibility/history returns paginated past checks

### Admin Panel

- [ ] **ADMIN-01**: User model has role field (user/admin)
- [ ] **ADMIN-02**: is_admin dependency checks role
- [ ] **ADMIN-03**: POST /admin/schemes adds new scheme with criteria
- [ ] **ADMIN-04**: PUT /admin/schemes/{id} updates scheme details
- [ ] **ADMIN-05**: DELETE /admin/schemes/{id} soft deletes (is_active = False)
- [ ] **ADMIN-06**: POST /admin/schemes/{id}/criteria adds criterion to scheme
- [ ] **ADMIN-07**: DELETE /admin/criteria/{id} removes criterion
- [ ] **ADMIN-08**: Regular user gets 403 on all admin routes

### Testing

- [ ] **TEST-01**: Pytest configured with AsyncClient from httpx
- [ ] **TEST-02**: Test fixtures for test DB, test user, test admin, seeded schemes
- [ ] **TEST-03**: Auth tests: register, login, bad password, expired token
- [ ] **TEST-04**: Eligibility tests: matching profiles, zero-match profiles, missing fields
- [ ] **TEST-05**: Cache tests: verify cache hit on second request
- [ ] **TEST-06**: Admin tests: add/update/delete scheme, non-admin gets 403
- [ ] **TEST-07**: Coverage report shows 75%+ with pytest --cov=app

### Production Readiness

- [ ] **PROD-01**: Rate limiting with slowapi (10 req/min per IP on eligibility endpoint)
- [ ] **PROD-02**: Structured logging with loguru
- [ ] **PROD-03**: Request ID middleware (UUID per request)
- [ ] **PROD-04**: Custom HTTPException error handlers
- [ ] **PROD-05**: CORS middleware configured
- [ ] **PROD-06**: GET /health checks DB + Redis connectivity
- [ ] **PROD-07**: API versioning prefix /api/v1/
- [ ] **PROD-08**: Swagger UI metadata (title, description, version, contact)

### Documentation & Deployment

- [ ] **DOCS-01**: README.md with setup instructions, example requests, architecture diagram
- [ ] **DOCS-02**: Docstrings on all major functions
- [ ] **DOCS-03**: All endpoints tagged with Swagger tags and descriptions
- [ ] **DOCS-04**: Example request/response in Swagger using openapi_examples
- [ ] **DOCS-05**: .env.example file with all required variables
- [ ] **DOCS-06**: Deployed to Railway/Render/Fly.io with live URL

## v2 Requirements

Deferred to future release. Tracked but not in current roadmap.

### Multilingual

- **LANG-01**: Scheme descriptions available in Tamil
- **LANG-02**: Scheme descriptions available in Hindi

### Integrations

- **INTG-01**: WhatsApp Bot integration via Twilio for eligibility checks
- **INTG-02**: Webhook notifications when new matching schemes are added
- **INTG-03**: Chrome extension for auto-filling government forms

## Out of Scope

| Feature | Reason |
|---------|--------|
| Frontend/UI | Pure API project — no web interface |
| Mobile app | API-first, clients build their own |
| Real-time notifications | Webhooks deferred to v2 |
| Payment processing | Not applicable to scheme checking |
| Multi-language API responses | Deferred — English only for v1 |

## Traceability

Which phases cover which requirements. Updated during roadmap creation.

| Requirement | Phase | Status |
|-------------|-------|--------|
| INFRA-01 to INFRA-07 | Phase 1 | Pending |
| DB-01 to DB-06 | Phase 2 | Pending |
| DATA-01 to DATA-07 | Phase 3 | Pending |
| AUTH-01 to AUTH-06 | Phase 4 | Pending |
| ENGINE-01 to ENGINE-05 | Phase 5 | Pending |
| API-01 to API-06 | Phase 6 | Pending |
| CACHE-01 to CACHE-06 | Phase 7 | Pending |
| PROF-01 to PROF-06 | Phase 8 | Pending |
| ADMIN-01 to ADMIN-08 | Phase 9 | Pending |
| TEST-01 to TEST-07 | Phase 10 | Pending |
| PROD-01 to PROD-08 | Phase 11 | Pending |
| DOCS-01 to DOCS-06 | Phase 12 | Pending |

**Coverage:**
- v1 requirements: 67 total
- Mapped to phases: 67
- Unmapped: 0 ✓

---
*Requirements defined: 2026-04-26*
*Last updated: 2026-04-26 after initial definition*
