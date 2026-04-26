# Roadmap: Government Scheme Eligibility API

**Created:** 2026-04-26
**Milestone:** v1.0

## Phases

### Phase 1: Project Setup & Architecture
**Goal:** Get the project skeleton ready with Docker, FastAPI, and infrastructure.
**Requirements:** INFRA-01, INFRA-02, INFRA-03, INFRA-04, INFRA-05, INFRA-06, INFRA-07
**UI hint**: no
**Success criteria:**
1. Folder structure matches specification (app/, scraper/, alembic/, tests/)
2. `docker compose up` starts FastAPI + PostgreSQL + Redis without errors
3. GET /health returns `{"status": "ok"}`
4. Alembic is initialized and configured

### Phase 2: Database Models & Migrations
**Goal:** Define all database tables and run migrations.
**Requirements:** DB-01, DB-02, DB-03, DB-04, DB-05, DB-06
**UI hint**: no
**Success criteria:**
1. User, Scheme, EligibilityCriteria, State, SchemeState models exist
2. `alembic upgrade head` creates all tables
3. Tables verified with sample queries
4. Relationships (ForeignKey, relationship) work correctly

### Phase 3: Real Scheme Data Collection
**Goal:** Populate database with 500+ real, verified government schemes.
**Requirements:** DATA-01, DATA-02, DATA-03, DATA-04, DATA-05, DATA-06, DATA-07
**UI hint**: no
**Success criteria:**
1. Playwright scraper can extract data from MyScheme.gov.in
2. data.gov.in CSV parser works
3. schemes_seed.json contains structured, verified scheme data
4. Seed script inserts all data into PostgreSQL
5. `SELECT count(*) FROM schemes;` returns 500+

### Phase 4: Authentication System
**Goal:** Complete JWT auth flow — register, login, token refresh, protected routes.
**Requirements:** AUTH-01, AUTH-02, AUTH-03, AUTH-04, AUTH-05, AUTH-06
**UI hint**: no
**Success criteria:**
1. User can register with email/password
2. User can login and receive access + refresh tokens
3. Protected routes reject invalid/expired tokens
4. Token refresh works correctly
5. Passwords are properly hashed

### Phase 5: Core Eligibility Engine
**Goal:** Build the rule engine that matches user profiles to schemes.
**Requirements:** ENGINE-01, ENGINE-02, ENGINE-03, ENGINE-04, ENGINE-05
**UI hint**: no
**Success criteria:**
1. All operators (eq, neq, gte, lte, gt, lt, in, not_in, contains) work correctly
2. Engine correctly matches test profiles to expected schemes
3. Engine correctly rejects non-matching profiles
4. Null/optional criteria handled gracefully
5. Unit tests pass for all edge cases

### Phase 6: Eligibility API Endpoints
**Goal:** Expose the engine through REST endpoints with search and filtering.
**Requirements:** API-01, API-02, API-03, API-04, API-05, API-06
**UI hint**: no
**Success criteria:**
1. POST /eligibility/check returns matched schemes with reasons
2. GET /schemes/ supports state, category, gender filters
3. Full-text search works via GET /schemes/search?q=keyword
4. Pagination works on list endpoints
5. All responses use proper Pydantic models

### Phase 7: Redis Caching
**Goal:** Cache eligibility results for instant repeated queries.
**Requirements:** CACHE-01, CACHE-02, CACHE-03, CACHE-04, CACHE-05, CACHE-06
**UI hint**: no
**Success criteria:**
1. Redis client connects and operates async
2. Second call for same profile hits cache
3. X-Cache header shows HIT/MISS
4. Cache expires after 1 hour TTL
5. Admin can flush cache

### Phase 8: User Profiles & History
**Goal:** Let users save profiles and view past eligibility checks.
**Requirements:** PROF-01, PROF-02, PROF-03, PROF-04, PROF-05, PROF-06
**UI hint**: no
**Success criteria:**
1. User can save/update their profile
2. User can retrieve saved profile
3. Eligibility checks auto-save to history for authenticated users
4. History endpoint returns paginated results
5. History includes profile snapshot and results snapshot

### Phase 9: Admin Panel Routes
**Goal:** CRUD management for schemes without touching DB directly.
**Requirements:** ADMIN-01, ADMIN-02, ADMIN-03, ADMIN-04, ADMIN-05, ADMIN-06, ADMIN-07, ADMIN-08
**UI hint**: no
**Success criteria:**
1. Admin can add new schemes with criteria via API
2. Admin can update and soft-delete schemes
3. Admin can manage individual criteria
4. Regular user gets 403 on all admin routes
5. Role-based access control works correctly

### Phase 10: Testing
**Goal:** Comprehensive test suite proving the API works.
**Requirements:** TEST-01, TEST-02, TEST-03, TEST-04, TEST-05, TEST-06, TEST-07
**UI hint**: no
**Success criteria:**
1. Pytest runs with AsyncClient and test fixtures
2. Auth, eligibility, cache, and admin tests all pass
3. Edge cases covered (bad passwords, expired tokens, missing fields)
4. `pytest --cov=app` shows 75%+ coverage
5. All tests can run in CI environment

### Phase 11: Production Readiness
**Goal:** Make the API production-worthy with rate limiting, logging, error handling.
**Requirements:** PROD-01, PROD-02, PROD-03, PROD-04, PROD-05, PROD-06, PROD-07, PROD-08
**UI hint**: no
**Success criteria:**
1. Rate limiting active on eligibility endpoint (10 req/min per IP)
2. Every request is logged with request ID
3. Errors return structured JSON responses
4. CORS configured for cross-origin access
5. All routes under /api/v1/ prefix
6. Swagger UI shows proper metadata

### Phase 12: Documentation & Deployment
**Goal:** Make the project shareable and deployable.
**Requirements:** DOCS-01, DOCS-02, DOCS-03, DOCS-04, DOCS-05, DOCS-06
**UI hint**: no
**Success criteria:**
1. README.md has setup instructions and example requests
2. All major functions have docstrings
3. Swagger UI shows tags, descriptions, and example payloads
4. Someone can clone and run `docker compose up` in 5 minutes
5. Live deployed URL accessible

---
*Roadmap created: 2026-04-26*
*Last updated: 2026-04-26 after initial creation*
