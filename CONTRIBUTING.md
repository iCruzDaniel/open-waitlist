# Contributing to OpenWaitlist

Thanks for considering a contribution. OpenWaitlist is a FastAPI microservice for waitlists and leads, with an optional React + TypeScript admin panel. We welcome bug reports, feature ideas, documentation improvements, and test contributions.

## Prerequisites

- **Python 3.12+** and [uv](https://docs.astral.sh/uv/) (package manager)
- **Docker + Docker Compose** (for deployment and integration testing)
- **Node.js 20+** and npm (only if you touch the admin panel in `admin-panel/`)

## Development Setup

### Backend

```bash
# Clone the repo
git clone https://github.com/iCruzDaniel/open-waitlist.git
cd waitlistgo

# Install dependencies
uv sync

# Create your local environment file
cp .env.example .env

# Run database migrations
uv run alembic upgrade head

# Start the dev server
uv run uvicorn app.main:app --reload
```

The API runs at `http://localhost:8000`.

### Admin Panel (optional)

```bash
cd admin-panel
npm ci
npm run dev
```

Vite serves the panel at `http://localhost:5173`. You need `ENABLE_ADMIN_PANEL=true` in your `.env` for the panel to proxy to the backend.

## Day-to-Day Development

### Running tests

```bash
uv run pytest              # all tests
uv run pytest -v           # verbose
uv run pytest --cov=app    # with coverage
```

### Linting and formatting

```bash
uv run ruff check .        # lint
uv run ruff format .       # format
```

Ruff is the only formatter and linter for this project. Configuration lives in `pyproject.toml` (line-length 100, target Python 3.12). Do not use black, isort, flake8, or any other tool for formatting.

### After changing the admin panel

```bash
cd admin-panel
npm run build
```

Always rebuild before committing UI changes so the production bundle stays in sync.

## Coding Conventions

These rules keep the codebase consistent. Deviations will be asked to conform before merging.

### Python

- Type hints on everything. No exceptions.
- Use `async def` for every function that touches I/O (database, HTTP, SMTP, file system).
- Pydantic v2 for all request and response schemas.
- One service class per business responsibility in `app/services/`. Routers in `app/api/v1/` contain no business logic, only orchestration.
- `entry.data` is free-form JSON. Do not force fields like `email` at the Pydantic level beyond minimal size/type validation.
- Waitlists are soft-deleted (`is_active=false`, `deleted_at`), never physically deleted.
- Notifications (email + webhook) always run as background tasks. They must never add latency to `POST /entries` and their failure must never break the response to the client.

### TypeScript / React

- TypeScript strict mode. No `as any`, no `@ts-ignore`, no `@ts-expect-error`.
- Prefer explicit types over inference when the inferred type is not obvious.

### General

- All variable names, function names, and commit messages in English.
- User-facing messages (if any) may be in Spanish or English.

## Commit Conventions

We use [Conventional Commits](https://www.conventionalcommits.org/). Every commit message must follow this format:

```
<type>(<scope>): <short description>
```

Common types:

| Type | When to use |
|---|---|
| `feat` | New feature or capability |
| `fix` | Bug fix |
| `chore` | Tooling, CI, dependencies, scaffolding |
| `refactor` | Code restructuring with no behavior change |
| `docs` | Documentation only |
| `test` | Adding or updating tests |

Examples:

```
feat(entries): add CSV export endpoint
fix(auth): handle expired JWT gracefully
chore: update ruff to 0.8.5
docs: clarify notification setup in README
test(waitlists): cover soft-delete edge cases
```

Keep commits atomic. One logical change per commit.

## Pull Request Process

1. Branch off `main`. Use a descriptive branch name (`feat/csv-export`, `fix/jwt-expiry`).
2. Make your changes. Keep PRs focused on a single concern.
3. Before opening the PR, confirm:
   - `uv run pytest` passes
   - `uv run ruff check .` is clean
   - `uv run ruff format .` has no changes
   - If you touched the admin panel, `npm run build` in `admin-panel/` succeeds
4. Open the PR against `main`. Describe what changed and why. Link to any related issue.
5. A maintainer will review. Address feedback. Squash and merge when approved.

## Reporting Bugs

Open an issue on [GitHub](https://github.com/iCruzDaniel/open-waitlist/issues). Include:

- What you expected to happen
- What actually happened
- Steps to reproduce
- Python version, OS, and whether you are using Docker or running locally

## Security

Never commit secrets. That means API keys, passwords, JWT tokens, SMTP credentials, or any value from your `.env` file. The `.env` file is gitignored for a reason.

Do not log API keys, passwords, or full JWT tokens. If you need to debug authentication, log only the token's payload or a truncated prefix.

## Code of Conduct

This project follows the [Contributor Covenant Code of Conduct](CODE_OF_CONDUCT.md). By participating, you agree to its terms.
