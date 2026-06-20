# Contributing

## Reporting Security Issues

If you discover a potential security issue in this project, please notify AWS/Amazon
Security via our [vulnerability reporting page](https://aws.amazon.com/security/vulnerability-reporting/).
Do **not** create a public GitHub issue for security findings.

## Getting Started

1. Clone the repository
2. Set up the backend: `cd backend && pip install -r requirements.txt -r requirements-dev.txt`
3. Set up the frontend: `cd procurement-agent-ui && npm install`
4. Copy `backend/.env.example` to `backend/.env` and fill in your values

## Development Workflow

1. Create a feature branch: `git checkout -b feature/your-feature`
2. Write tests first (TDD)
3. Implement your changes
4. Run the full test suite: `cd backend && make test`
5. Run linting: `cd backend && make lint`
6. Format code: `cd backend && make format`
7. Commit with conventional commit messages: `feat: add supplier risk scoring`

## Code Standards

Enforced conventions. Key rules:

- No file over 500 lines
- No bare `except Exception` — use specific exception types
- No `sys.path.insert()` — use proper Python imports
- Every new feature needs tests
- Pin all dependency versions exactly
- Never copy code to lambda_tools/ — use Lambda Layers

## Commit Messages

Use [Conventional Commits](https://www.conventionalcommits.org/):

- `feat:` — new feature
- `fix:` — bug fix
- `refactor:` — code restructuring without behavior change
- `test:` — adding or updating tests
- `docs:` — documentation changes
- `chore:` — build, CI, dependency updates

## Testing

```bash
# Backend unit tests
cd backend && pytest tests/ -m unit

# Backend integration tests
cd backend && pytest tests/ -m integration

# Frontend tests
cd procurement-agent-ui && npx vitest

# Full suite with coverage
cd backend && make test
```

## Pull Requests

- Keep PRs focused on a single concern
- Include tests for new functionality
- Update CHANGELOG.md under [Unreleased]
- Ensure all checks pass before requesting review
