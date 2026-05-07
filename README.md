# protwis_django_docker

[![CI](https://github.com/iskoldt-x/protwis_django_docker/actions/workflows/ci.yml/badge.svg)](https://github.com/iskoldt-x/protwis_django_docker/actions/workflows/ci.yml)
[![Docker Publish](https://github.com/iskoldt-x/protwis_django_docker/actions/workflows/docker-publish.yml/badge.svg)](https://github.com/iskoldt-x/protwis_django_docker/actions/workflows/docker-publish.yml)
[![License: Apache-2.0](https://img.shields.io/badge/license-Apache%202.0-blue.svg)](LICENSE)

A reproducible Docker environment for the [protwis](https://github.com/protwis/protwis) Django application — the backbone of [GPCRdb](https://gpcrdb.org). One `docker compose up` brings the full stack online: Django app, PostgreSQL with the RDKit cartridge, and Adminer.

Designed as the runtime companion to [postgres_rdkit_docker](https://github.com/iskoldt-x/postgres_rdkit_docker), replacing the legacy conda-based local setup with a single uv-managed Python environment built on `python:3.8-slim-bookworm`.

---

## What you get

| Service | URL / Port | Notes |
|---|---|---|
| Django app | <http://localhost:8000> | source bind-mounted from the host; `runserver` auto-reloads on edit |
| PostgreSQL | `localhost:5432` | user `protwis`, password `protwis`, db `protwis`; RDKit cartridge enabled |
| Adminer    | <http://localhost:8888> | web SQL client; server name is `db` |

All three host-side ports are configurable via `.env`.

---

## Design principles

- **Code-free image.** The protwis source and the GPCRdb data tree are bind-mounted at runtime, never baked into the image. Upgrading Python or Django becomes a pure image rebuild — code remains untouched.
- **No conda, no host-side Python.** Dependencies are pure-pip via `uv`; the resulting image is significantly smaller than the legacy conda baseline and `uv sync --frozen` resolves in seconds.
- **No invasive changes to protwis.** Two additive `settings_*_docker.py` files register themselves under `protwis.settings_local` via `sys.modules`; existing settings files are not modified.
- **Single source of truth for shared config.** Site constants (`SITE_NAME`, `REFERENCE_POSITIONS`, `DOCUMENTATION_URL`, …) live in the upstream local-settings file; the docker variants inherit them, so future edits propagate automatically.
- **Multi-stage build.** Build tools (`build-essential`, `*-dev` headers) live in the builder stage only; the final image ships only runtime shared libraries.
- **Reproducible across hosts.** Same image, same dependency versions, same PostgreSQL extensions on every developer's machine. CI builds and smoke-tests every push.

---

## Prerequisites

- Docker Desktop running
- ~30 GB free disk space (for the postgres volume after the dump load)
- `git`, `curl`

Tested on macOS (Apple Silicon and Intel) and Linux. On Windows, run inside WSL2.

---

## Quickstart

1. **Clone the three repositories side by side**
   ```bash
   mkdir -p ~/GitHub && cd ~/GitHub
   git clone https://github.com/protwis/protwis
   git clone https://github.com/protwis/gpcrdb_data
   git clone https://github.com/iskoldt-x/protwis_django_docker
   ```

2. **Copy the example env file** (no edits required for the happy path)
   ```bash
   cd protwis_django_docker
   cp .env.example .env
   ```

3. **Bring up the stack**
   ```bash
   docker compose up -d
   ```
   The first start pulls the published images; subsequent starts take seconds.

4. **Load the GPCRdb dump and apply migrations** (~30–60 min)
   ```bash
   curl -L https://files.gpcrdb.org/protwis_sp.sql.gz -o ~/protwis.sql.gz
   gunzip -c ~/protwis.sql.gz | docker exec -i gpcrdb-db psql -U protwis -d protwis -q -1
   docker compose exec app python manage.py migrate
   ```
   The `migrate` step is required: the published dump may lags upstream code, so a small set of Django migrations brings the schema forward. See [docs/onboarding.md](docs/onboarding.md) §5 for the rationale.

5. **Open <http://localhost:8000>**

---

## Repository layout

```
.
├── Dockerfile                  # multi-stage, uv-driven, Python 3.8 on bookworm-slim
├── docker-compose.yml          # app + db + adminer; parameterised by .env
├── pyproject.toml              # single source of truth for Python deps
├── uv.lock                     # generated; committed for reproducibility
├── .env.example                # main-stack env template — copy to .env
├── .env.alt                    # alt-stack env template — for side-by-side runs
├── docs/
│   ├── onboarding.md              # long-form tutorial — start here as a new contributor
│   └── design-pipeline-1.md       # design rationale and verification log
├── LICENSE
├── README.md
└── .github/workflows/
    ├── ci.yml                     # build + smoke on every push/PR
    └── docker-publish.yml         # multi-arch publish to ghcr.io on v* tags
```



---

## Development workflow

The protwis source is bind-mounted into the app container, so host edits are live and Django's `runserver` auto-reloads. Common commands:

```bash
# Tail app logs (filter out deprecation noise)
docker compose logs -f app | grep -v "FutureWarning\|Deprecation"

# Drop into the app container
docker compose exec app bash

# Run any Django management command (see onboarding §8 for the pattern)
docker compose exec app python manage.py <command>

# Open a psql shell against the DB
docker exec -it gpcrdb-db psql -U protwis -d protwis

# Rebuild the app image after editing Dockerfile or pyproject.toml
docker compose build app
docker compose up -d app

# Stop the stack
docker compose down

# Reset the database (DESTRUCTIVE — drops the 26 GB postgres volume)
docker compose down -v
```

For long-running management commands, run detached and watch logs separately:
```bash
docker compose exec -T -d app python manage.py build_<something>
docker compose logs -f app
```

---

## Running a second stack

A second isolated stack (separate ports, separate volume, separate network) coexists with the main one via the bundled `.env.alt` template:

```bash
docker compose --env-file .env.alt up -d   # main on :8000, alt on :8001
```

Useful for code-vs-code, dump-vs-dump, or before-vs-after comparisons.

---

## Continuous integration

| Workflow | Trigger | What it does |
|---|---|---|
| [`ci.yml`](.github/workflows/ci.yml) | every push and PR to `main` | builds the image and runs smoke tests (critical imports, Django boot, `manage.py check`) |
| [`docker-publish.yml`](.github/workflows/docker-publish.yml) | tags matching `v*` | builds multi-arch (amd64 + arm64) and pushes to `ghcr.io/iskoldt-x/protwis_django_docker` |

The published image is anonymously pullable, so `docker compose up` works on a fresh machine with no `docker login` step.

---

## Upgrading dependencies

The whole point of moving off conda is making upgrades testable in CI rather than untestable on a laptop:

1. Edit `pyproject.toml` (typically a single pin bump).
2. Regenerate the lock locally: `uv lock`. Without `uv` on the host, run it via the same Python container:
   ```bash
   docker run --rm -v "$PWD":/work -w /work python:3.8-slim-bookworm bash -c \
     "apt-get update -qq && apt-get install -y -qq git && pip install -q uv && uv lock"
   ```
3. Push — GitHub Actions builds the image and runs the smoke suite. If green, merge; if red, the failure points at the exact breakage.

A future `docs/upgrading.md` will codify the Python 3.8 → 3.11 → 3.12 and Django 2.2 → 3.2 → 4.2 ladders.

---

## Going further

- **New contributor?** Start with [docs/onboarding.md](docs/onboarding.md) — the full hand-holding tutorial covering daily-use commands, management commands, troubleshooting, and dual-stack workflows.
- **Upstream code:** <https://github.com/protwis/protwis>
- **GPCRdb data:** <https://github.com/protwis/gpcrdb_data>

---

## License

[Apache-2.0](LICENSE)
