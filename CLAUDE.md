# CLAUDE.md — SupplyChainOptimization-v2

## Project Overview

Predictive supply chain orchestrator: Flask 3.0 backend, React 19 + Vite frontend, AWS CDK infrastructure, Strands AI agents on Bedrock AgentCore. Multi-objective optimization (cost, risk, quality, lead-time) with Neptune graph DB, Chronos-2 demand forecasting, and Cognito auth.

## Architecture

```
backend/
  api/
    server.py      → Thin app factory (registers Blueprints, middleware, error handlers)
    state.py       → Shared state (data_reader, neptune_client, optimization_engine, etc.)
    routes/        → Flask Blueprints: health, data, optimization, purchase_orders,
                     defects, forecasting, graph, risk, chat, admin
  core/            → Business logic: models, optimization engine
  config/          → Environment-based settings
  data/            → Data readers (CSV, Neptune, S3, Chronos)
  agents/          → AgentCore entrypoint + procurement agent
  aws/cdk/         → 14 CDK stacks
  aws/lambda_tools/ → Lambda deployment (symlinks to core/, data/ — NOT copies)
  tests/           → Unit + integration tests
procurement-agent-ui/
  src/             → React components, TypeScript
demand-forecasting/
  agents/          → Chronos-2 forecasting agents
  frontend/        → Forecasting UI
```

## Enforced Conventions

### File Size & Structure
- **No file may exceed 500 lines.** If a file approaches this limit, refactor BEFORE adding more code.
- Flask routes MUST use Blueprints — one file per domain (suppliers, optimization, defects, agents, forecasting, health).
- React components must be single-responsibility. Extract sub-components when a file exceeds 300 lines.
- No god classes. Split large classes into focused modules.

### Python Standards
- **Python 3.11** target.
- Formatter: **Black** (line-length 88). Run before every commit.
- Linter: **flake8** (88 chars, ignore E203/W503).
- Type checker: **mypy** (strict mode — disallow_untyped_defs).
- All config is in `backend/pyproject.toml`. Do NOT create separate .flake8, .mypy.ini files.

### Exception Handling
- **NEVER use bare `except Exception`.** Always catch the most specific exception type.
- Acceptable: `except (ValueError, KeyError)`, `except ConnectionError`, `except boto3.exceptions.ClientError`.
- **NEVER silently swallow exceptions** (`except: pass`). Always log at minimum.
- Create custom exception classes in `backend/core/exceptions.py` when domain-specific errors are needed.

### Imports & Packaging
- **NEVER use `sys.path.insert()`.** The backend is a proper Python package.
- Run from the backend directory: `python -m api.server` or use pyproject.toml entry points.
- Lambda functions import shared code via Lambda Layers, NOT by copying files.
- Test files use `conftest.py` fixtures for path setup, not sys.path hacks.

### Code Duplication
- Shared business logic (models, optimization, data readers) lives in `backend/core/` and `backend/data/`.
- Lambda functions import from these via Lambda Layers — **never copy files to lambda_tools/**.
- If you find yourself copying code, create a shared module instead.

### Dependencies
- **Pin ALL versions exactly** in every requirements.txt file (e.g., `strands-agents==1.1.2`, not `strands-agents`).
- Production deps go in `requirements.txt`. Test/dev tools go in `requirements-dev.txt`.
- After adding a dependency, verify it doesn't conflict with existing pins.
- Frontend: use exact semver in package.json for critical deps.

### Testing
- **Every new endpoint or feature MUST have tests.** No exceptions.
- Backend: pytest with markers (@pytest.mark.unit, @pytest.mark.integration, @pytest.mark.slow).
- Frontend: Vitest + React Testing Library. Test user interactions, not implementation details.
- Coverage threshold: 70% minimum (enforced by pytest-cov).
- Test file naming: `test_<module>.py` for unit, `tests/integration/test_<feature>.py` for integration.

### Security
- All config from environment variables — NEVER hardcode secrets, keys, or ARNs.
- CORS origins: explicit allowlist only. NEVER set to `"*"` in production.
- Flask-Talisman for security headers (CSP, X-Frame-Options, HSTS).
- Flask-Limiter for rate limiting on all API endpoints.
- Validate all API request input with Pydantic models.
- CDK stacks: do NOT suppress security warnings with "hackathon" or "demo" justifications.

### Frontend (React/TypeScript)
- TypeScript strict mode. No `any` types except when interfacing with untyped libraries.
- ESLint with React hooks + React refresh plugins.
- Components: functional only, with explicit prop types.
- No inline styles for reusable patterns — extract to CSS modules or utility classes.
- State management: keep state as close to where it's used as possible.

### Git & Commits
- Branch naming: `feature/`, `fix/`, `refactor/`, `docs/`, `test/` prefixes.
- Commit messages: conventional commits format (`feat:`, `fix:`, `refactor:`, `test:`, `docs:`, `chore:`).
- One logical change per commit. Don't mix feature work with refactoring.

### Documentation
- Python: one-line docstrings for non-obvious functions. No multi-paragraph docstrings.
- API endpoints: Flasgger/Swagger annotations for all routes.
- README.md maintained at root. Per-module docs in docs/.

## SDLC Workflow (How to use Claude for this project)

### Before Writing Any Code
1. **Brainstorm first** — use the brainstorming skill to explore requirements and design before implementation.
2. **Write a plan** — for multi-step features, use the writing-plans skill to create an architecture blueprint.
3. **Check CLAUDE.md** — every convention above must be followed. If a convention is wrong, update CLAUDE.md first.

### During Implementation
4. **TDD** — write tests first, then implement to make them pass. Use the test-driven-development skill.
5. **Small files** — if you're about to add code to a file over 400 lines, stop and refactor first.
6. **Specific exceptions** — never use `except Exception`. Think about what can actually fail.
7. **No duplication** — if code exists in core/, import it. Never copy.

### Before Completing
8. **Verify** — use the verification-before-completion skill. Run tests, check types, lint.
9. **Review** — use the requesting-code-review skill on your changes.
10. **Commit** — one logical change per commit, conventional commit message format.

## Quick Reference: Commands

```bash
# Backend
cd backend && make test          # Run all tests with coverage
cd backend && make lint           # flake8 + mypy
cd backend && make format         # Black formatting
cd backend && python -m api.server  # Run dev server

# Frontend
cd procurement-agent-ui && npm run dev    # Dev server (port 5174)
cd procurement-agent-ui && npm run build  # Type check + build
cd procurement-agent-ui && npm run lint   # ESLint
cd procurement-agent-ui && npx vitest     # Run tests

# CDK
cd backend/aws/cdk && npx cdk synth      # Synthesize stacks
cd backend/aws/cdk && npx cdk deploy      # Deploy
```

## Environment Variables

See `backend/.env.example` for full list. Key vars:
- `FLASK_ENV` — development | production
- `FLASK_PORT` — default 5000
- `CORS_ORIGINS` — comma-separated allowlist (NEVER use *)
- `AWS_REGION` — default us-east-1
- `NEPTUNE_ENDPOINT` — Neptune cluster endpoint
- `DATA_PATH` — path to CSV data files
