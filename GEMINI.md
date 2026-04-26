<!-- GSD:project-start source:PROJECT.md -->
## Project

**Government Scheme Eligibility API**

A FastAPI-based backend API that takes user profile inputs (age, income, caste, state, gender, occupation, disability status) and returns all government schemes they qualify for — with application links, deadlines, and benefit details. It serves as developer-friendly infrastructure that any app (rural banking, NGO portal, government chatbot) can call to check scheme eligibility programmatically.

**Core Value:** Given a user profile, instantly return every government scheme they're eligible for with actionable application details — because most Indians never claim schemes they're entitled to due to lack of a clean, queryable system.

### Constraints

- **Tech Stack**: FastAPI, PostgreSQL, SQLAlchemy 2.0 + Alembic, Pydantic v2, Redis, JWT (python-jose), Playwright + BeautifulSoup, Pytest — as specified in source document
- **Data Quality**: Must use real, verified government scheme data — no fake/placeholder data
- **Architecture**: Rule engine must be generic and data-driven via EligibilityCriteria table
- **Deployment**: Must work with single `docker compose up` command
- **Testing**: Minimum 75% test coverage
<!-- GSD:project-end -->

<!-- GSD:stack-start source:STACK.md -->
## Technology Stack

Technology stack not yet documented. Will populate after codebase mapping or first phase.
<!-- GSD:stack-end -->

<!-- GSD:conventions-start source:CONVENTIONS.md -->
## Conventions

Conventions not yet established. Will populate as patterns emerge during development.
<!-- GSD:conventions-end -->

<!-- GSD:architecture-start source:ARCHITECTURE.md -->
## Architecture

Architecture not yet mapped. Follow existing patterns found in the codebase.
<!-- GSD:architecture-end -->

<!-- GSD:workflow-start source:GSD defaults -->
## GSD Workflow Enforcement

Before using Edit, Write, or other file-changing tools, start work through a GSD command so planning artifacts and execution context stay in sync.

Use these entry points:
- `/gsd-quick` for small fixes, doc updates, and ad-hoc tasks
- `/gsd-debug` for investigation and bug fixing
- `/gsd-execute-phase` for planned phase work

Do not make direct repo edits outside a GSD workflow unless the user explicitly asks to bypass it.
<!-- GSD:workflow-end -->



<!-- GSD:profile-start -->
## Developer Profile

> Profile not yet configured. Run `/gsd-profile-user` to generate your developer profile.
> This section is managed by `generate-claude-profile` -- do not edit manually.
<!-- GSD:profile-end -->
