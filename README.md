# Peblo TV Mini

A full-stack television catalogue platform built with FastAPI, PostgreSQL, React, and TypeScript. It provides an internal CMS for editorial content management and a public Viewer app for browsing published catalogues.

## What is implemented

- **Backend**: FastAPI + SQLAlchemy 2.0 + Alembic + Pydantic v2
- **Database**: PostgreSQL with 6 models (User, Show, Season, Episode, Artwork, PublishRun)
- **Authentication**: JWT bearer tokens with editor/admin roles
- **CMS**: React 18 + TypeScript + Vite + TanStack Query for editorial workflow
- **Viewer**: React 18 + TypeScript + Vite for public catalogue consumption
- **Artwork**: Upload with Pillow-based validation (aspect ratio, size, format)
- **Validation**: Human-readable validation report blocking invalid publishes
- **Publishing**: Deterministic immutable catalogue versions with atomic activation
- **Storage**: `StorageService` protocol with `LocalStorage` implementation
- **Search**: Backend search/filter API with category, language, and section filters
- **Testing**: 51/51 backend tests passing with pytest
- **CI**: GitHub Actions workflow for backend tests and frontend builds

## Project structure

- `backend/` — FastAPI API, database models, validation, publishing, seeding
- `cms/` — Internal CMS frontend (port 5173 in development)
- `viewer/` — Public viewer frontend (port 4173 in development)
- `challenge/` — Assignment seed data and asset samples
- `storage/` — Local storage for generated catalogues and uploaded art
- `.github/workflows/` — CI definition

## Local setup

### Prerequisites

- Python 3.12
- Node.js 20
- PostgreSQL 16+
- npm

### Backend setup

```bash
cd peblo-tv-mini/backend
python -m venv .venv
.venv\Scripts\activate  # Windows
source .venv/bin/activate  # Unix
pip install -r requirements.txt
cp ../.env.example ../.env
# Edit .env with your local PostgreSQL credentials
alembic upgrade head
python -m app.seeding.seed_dev
uvicorn app.main:app --reload --port 8000
```

### CMS setup

```bash
cd peblo-tv-mini/cms
npm install
npm run dev
```

### Viewer setup

```bash
cd peblo-tv-mini/viewer
npm install
npm run dev
```

### Docker Compose setup

```bash
cp .env.example .env
# Edit .env if needed for local ports/credentials
docker compose up --build
```

The container entrypoint runs `alembic upgrade head` and `python -m app.seeding.seed_dev` automatically.

Stop with `Ctrl+C`, or `docker compose down`. Remove persisted data with `docker compose down -v`.

## URLs

| Service | Development URL | Notes |
|---------|-----------------|-------|
| API | http://localhost:8000 | Backend server |
| API Health | http://localhost:8000/health | Health check with PostgreSQL probe |
| CMS | http://localhost:5173 | Internal editorial interface |
| Viewer | http://localhost:4173 | Public catalogue viewer |

## Environment variables

| Variable | Purpose | Default |
|----------|---------|---------|
| `APP_ENV` | Application environment | `development` |
| `APP_HOST` | Bind host | `0.0.0.0` |
| `APP_PORT` | Bind port | `8000` |
| `LOG_LEVEL` | Logging level | `info` |
| `POSTGRES_DB` | Database name | `peblo` |
| `POSTGRES_USER` | Database user | `peblo` |
| `POSTGRES_PASSWORD` | Database password | `change_me_dev` |
| `POSTGRES_HOST` | Database host | `db` (Docker) / `localhost` (local) |
| `POSTGRES_PORT` | Database port | `5432` |
| `DATABASE_URL` | SQLAlchemy database URL | derived from above |
| `JWT_SECRET` | JWT signing secret | `change-me-in-dev` |
| `JWT_ALGORITHM` | JWT algorithm | `HS256` |
| `JWT_ACCESS_TOKEN_EXPIRE_MINUTES` | Token expiry | `60` |
| `STORAGE_BACKEND` | Storage provider | `local` |
| `LOCAL_STORAGE_PATH` | Local storage root | `./storage` |
| `LOCAL_STORAGE_URL` | Public storage base URL | `http://localhost:8000/storage` |
| `CORS_ALLOW_ORIGINS` | Allowed CORS origins | `http://localhost:5173,http://localhost:4173` |
| `CMS_API_URL` | CMS API base URL | `http://localhost:8000` |
| `VIEWER_API_URL` | Viewer API base URL | `http://localhost:8000` |
| `DEV_EDITOR_EMAIL` | Editor dev account email | `editor@example.com` |
| `DEV_EDITOR_PASSWORD` | Editor dev account password | `change_me_dev` |
| `DEV_ADMIN_EMAIL` | Admin dev account email | `admin@example.com` |
| `DEV_ADMIN_PASSWORD` | Admin dev account password | `change_me_dev` |

## Authentication

The API uses JWT bearer tokens. Development accounts are created by the seed script:

- **Editor**: `editor@example.com` / `change_me_dev`
- **Admin**: `admin@example.com` / `change_me_dev`

The CMS login uses these credentials. The backend rejects invalid emails and passwords with HTTP 401/422 responses.

## Atomic publish design

Publishing creates an immutable catalogue version and atomically activates it for viewers:

1. `build_catalogue()` validates all published shows/episodes and builds a deterministic JSON document
2. The catalogue is written to `storage/catalogue/versions/sha256-{digest}.json` using a temp file + `os.replace()` to avoid partial writes
3. The live pointer file `storage/catalogue/live.json` is atomically updated with the new version key
4. If the activation fails, the previous live catalogue remains unchanged
5. All publish attempts are recorded in `publish_runs` with status, outcome, and counts

This ensures viewers never see a half-written catalogue and failed publishes do not corrupt the live pointer.

## Storage abstraction

The project defines a `StorageService` protocol with methods: `save`, `read`, `delete`, `exists`, `public_url`, `internal_url`.

`LocalStorage` implements this protocol using the local filesystem. It stores uploaded artwork and immutable catalogue versions under a configurable root directory.

To support Cloudflare R2 or another object store later:
1. Implement the same `StorageService` protocol
2. Replace the `LocalStorage` instance in `app/api/v1/catalog.py` and the seed script
3. No changes to models, schemas, or business logic are required

## Search scalability

The current Viewer search loads the full published catalogue and filters it client-side. The backend `/catalog/search` endpoint also filters the entire catalogue in memory.

For larger catalogues, this approach does not scale. Recommended improvements:

1. **PostgreSQL full-text search**: Add `GIN` indexes on `shows.title`, `shows.synopsis`, `episodes.title` and use `to_tsvector()` / `to_tsquery()` for server-side search
2. **Dedicated search service**: Index catalogue content into Elasticsearch, Meilisearch, or Typesense for fast full-text search with faceting
3. **Incremental catalogue loading**: Add pagination to `/catalog/search` and limit result sets
4. **Pre-computed search indexes**: Build search indexes at publish time and store them alongside catalogue versions

## Published catalogue file rationale

The published catalogue is a standalone JSON file served to the Viewer. It contains only public-facing data: shows, seasons, episodes, artwork URLs, sections, and categories. It excludes database records, admin status fields, timestamps, storage keys, upload metadata, and internal validation details.

The file is immutable once written. A separate `live.json` pointer file tracks the current active version. This design:

- Decouples the Viewer from the database
- Enables CDN caching of catalogue content
- Allows instant rollback by changing the pointer
- Makes publish operations idempotent (same content = same file hash)

## Tradeoffs

- **Immutable files**: Every publish writes a new file. Over time, storage grows unless old versions are pruned. The current implementation does not implement version expiry.
- **No catalogue version expiry**: Old catalogue files accumulate. A production deployment should add a cleanup policy.
- **LocalStorage only**: Currently supports only local filesystem storage. Object storage (R2/S3) requires a new implementation.
- **Client-side search**: Works for small catalogues but will not scale to thousands of shows/episodes without backend search.
- **Single PostgreSQL instance**: No read replicas or connection pooling configured.

## Skipped / deferred work

- Cloudflare R2 or S3 storage backend
- PostgreSQL full-text search or dedicated search service
- Catalogue version expiry / cleanup policy
- CDN integration for catalogue and artwork delivery
- Multi-region or replicated PostgreSQL setup
- Advanced artwork editing (crop, rotate, metadata)
- User management beyond development accounts
- Audit logging for admin actions
- Rate limiting and request throttling
- OpenAPI schema documentation polish

## Testing

```bash
cd peblo-tv-mini/backend
python -m pytest tests/ -v
```

Current status: **51/51 tests passing**

Key test coverage:
- Show, season, episode, and artwork CRUD
- Validation rules and reference checks
- Publish determinism and idempotency
- Catalogue schema and season 0 exclusion
- Search filters and viewer endpoints
- Authorization and artwork upload validation
- Health checks and database models

## CI

GitHub Actions runs on push and pull requests:
- Backend: Python 3.12 + uv + pytest
- CMS: Node.js 20 + npm ci + build
- Viewer: Node.js 20 + npm ci + build

## AI disclosure

AI coding assistants were used during the development of this project to assist with code generation, debugging, and documentation. All AI-generated code was reviewed, tested, and validated by the developer. The project's tests, architecture decisions, and implementation details were verified by the development team before inclusion.
