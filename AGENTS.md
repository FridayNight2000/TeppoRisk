# Repository Guidelines

## Project Structure

```
real-time-risk/
├── backend/              # FastAPI backend (Python 3.12)
│   ├── app/
│   │   ├── api/          # Route handlers
│   │   ├── core/         # Configuration (pydantic-settings)
│   │   ├── db/           # Data access layer
│   │   ├── dependencies/ # FastAPI dependency injection
│   │   ├── models/       # Domain / ML models
│   │   ├── schemas/      # Pydantic request/response schemas
│   │   ├── services/     # Business logic & model inference
│   │   └── main.py       # App factory & lifespan
│   ├── model_assets/     # Serialized model checkpoint & scalers
│   ├── tests/            # pytest test suite
│   └── pyproject.toml    # Build config, tool settings (ruff, mypy, pytest)
├── frontend/             # Next.js 16 app (React 19, TypeScript, Tailwind 4)
│   ├── app/
│   │   ├── components/   # React components (MapLibre GL map, charts)
│   │   ├── hooks/        # Custom React hooks
│   │   ├── lib/          # Utility functions
│   │   ├── types/        # TypeScript type definitions
│   │   └── data/         # Static data files
│   ├── public/           # Static assets
│   └── package.json      # pnpm managed
├── scripts/              # Data preparation scripts (Python)
├── Makefile              # Root dev commands
└── vercel.json           # Deployment config
```

## Build, Test & Development Commands

### Backend

```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"

# Run dev server
uvicorn app.main:app --host 127.0.0.1 --port 8000

# Lint & format
ruff check . && ruff format .

# Type check
mypy

# Tests
pytest
```

### Frontend

```bash
cd frontend
pnpm install

pnpm dev          # Start Next.js dev server (port 3000)
pnpm build        # Production build
pnpm lint         # ESLint (eslint-config-next with core-web-vitals & typescript)
```

### Full Stack (from repo root)

```bash
make dev              # Starts backend + frontend together
make dev-backend      # Backend only
make dev-frontend     # Frontend only
```

## Coding Style & Conventions

### Python (backend)

- **Formatter/linter**: Ruff (`line-length = 100`, rules: E, F, I, B, UP)
- **Type checking**: mypy in strict mode
- **Target**: Python 3.12
- **Naming**: snake_case for modules, functions, variables; PascalCase for classes and Pydantic models
- **Imports**: sorted by isort rules via Ruff

### TypeScript (frontend)

- **Framework**: Next.js 16 App Router with React 19 -- read `node_modules/next/dist/docs/` before writing code; APIs differ from older versions
- **Styling**: Tailwind CSS 4 via `@tailwindcss/postcss`
- **Linting**: ESLint with `eslint-config-next` (core-web-vitals + typescript)
- **Path alias**: `@/*` maps to the `frontend/` root
- **Strict mode**: enabled in `tsconfig.json`

## Testing Guidelines

### Backend

- **Framework**: pytest with pytest-asyncio
- **Test directory**: `backend/tests/`
- **Naming**: files prefixed `test_`, functions prefixed `test_`
- **Run**: `cd backend && .venv/bin/python -m pytest`

### Frontend

- No test framework is currently configured. Use ESLint and TypeScript compiler (`pnpm build`) for static verification.

## Environment Variables

Copy `.env.example` in both `backend/` and `frontend/` directories. Backend requires paths to model assets and station metadata; frontend requires `BACKEND_URL`.

## Commit & Pull Request Guidelines

- **Commit style**: Conventional Commits -- `type: short description` (e.g. `feat:`, `fix:`, `chore:`, `docs:`)
- Keep commits focused on a single logical change
- PR descriptions should summarize what changed and why
