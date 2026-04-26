# Government Scheme Eligibility API

## What This Is

A FastAPI-based backend API that takes user profile inputs (age, income, caste, state, gender, occupation, disability status) and returns all government schemes they qualify for — with application links, deadlines, and benefit details. It serves as developer-friendly infrastructure that any app (rural banking, NGO portal, government chatbot) can call to check scheme eligibility programmatically.

## Core Value

Given a user profile, instantly return every government scheme they're eligible for with actionable application details — because most Indians never claim schemes they're entitled to due to lack of a clean, queryable system.

## Requirements

### Validated

(None yet — ship to validate)

### Active

- [ ] Project skeleton with FastAPI + PostgreSQL + Redis via Docker Compose
- [ ] Database models for Users, Schemes, EligibilityCriteria, States
- [ ] Real scheme data collection (500+ schemes from MyScheme.gov.in, data.gov.in)
- [ ] JWT authentication system (register, login, refresh, protected routes)
- [ ] Data-driven rule engine that evaluates eligibility criteria against user profiles
- [ ] REST API endpoints for eligibility checking, scheme listing, search
- [ ] Redis caching layer for eligibility query results
- [ ] User profile saving and eligibility check history
- [ ] Admin panel routes for scheme CRUD management
- [ ] Comprehensive test suite (75%+ coverage)
- [ ] Production readiness (rate limiting, logging, error handling, CORS, API versioning)
- [ ] Documentation and deployment setup

### Out of Scope

- Multilingual support (Tamil, Hindi) — deferred to stretch goals
- WhatsApp Bot integration — deferred to stretch goals
- Webhook notifications for new matching schemes — deferred to stretch goals
- Chrome extension for auto-filling government forms — deferred to stretch goals
- Frontend/UI — this is a pure API project

## Context

- India has 500+ central and state government schemes worth lakhs of crores in benefits
- No developer-friendly API exists today for programmatic eligibility checking
- MyScheme.gov.in has 3000+ schemes but no public API
- data.gov.in provides some scheme data as downloadable CSV/JSON
- The rule engine must be data-driven (criteria in DB, not hardcoded in Python)
- Target data sources: MyScheme.gov.in (scraping), data.gov.in (CSV download), AI-assisted structuring
- Priority schemes include PM Kisan, Ayushman Bharat, PM Awas Yojana, Sukanya Samriddhi, and Tamil Nadu state schemes

## Constraints

- **Tech Stack**: FastAPI, PostgreSQL, SQLAlchemy 2.0 + Alembic, Pydantic v2, Redis, JWT (python-jose), Playwright + BeautifulSoup, Pytest — as specified in source document
- **Data Quality**: Must use real, verified government scheme data — no fake/placeholder data
- **Architecture**: Rule engine must be generic and data-driven via EligibilityCriteria table
- **Deployment**: Must work with single `docker compose up` command
- **Testing**: Minimum 75% test coverage

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Data-driven rule engine over hardcoded rules | Adding new schemes requires zero code changes — just DB insert | — Pending |
| EligibilityCriteria table with field/operator/value | Generic pattern supports all scheme types without schema changes | — Pending |
| PostgreSQL full-text search over Elasticsearch | Simpler stack, tsvector/tsquery sufficient for scheme name/description search | — Pending |
| Async throughout (AsyncSession, aioredis) | Consistent async patterns, better performance under load | — Pending |

## Evolution

This document evolves at phase transitions and milestone boundaries.

**After each phase transition** (via `/gsd-transition`):
1. Requirements invalidated? → Move to Out of Scope with reason
2. Requirements validated? → Move to Validated with phase reference
3. New requirements emerged? → Add to Active
4. Decisions to log? → Add to Key Decisions
5. "What This Is" still accurate? → Update if drifted

**After each milestone** (via `/gsd-complete-milestone`):
1. Full review of all sections
2. Core Value check — still the right priority?
3. Audit Out of Scope — reasons still valid?
4. Update Context with current state

---
*Last updated: 2026-04-26 after initialization*
