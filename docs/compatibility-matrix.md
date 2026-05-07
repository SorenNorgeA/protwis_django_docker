# Compatibility Matrix

_Last run: 2026-05-07 13:45 UTC_ · [workflow run](https://github.com/iskoldt-X/protwis_django_docker/actions/runs/25499696491)

**Summary:** 0 / 36 green · 10 red (lock) · 26 red (build).

Each green cell links to the ghcr package page; the tag in the cell is what you `docker pull`.

---

## Python 3.8

| Django \ RDKit | 2023.09 | 2024.09 | 2025.09 | 2026.03 |
|---|---|---|---|---|
| **3.2** | ❌ build | ❌ lock | ❌ lock | ❌ lock |
| **4.2** | ❌ build | ❌ lock | ❌ lock | ❌ lock |
| **5.2** | ❌ lock | ❌ lock | ❌ lock | ❌ lock |

## Python 3.11

| Django \ RDKit | 2023.09 | 2024.09 | 2025.09 | 2026.03 |
|---|---|---|---|---|
| **3.2** | ❌ build | ❌ build | ❌ build | ❌ build |
| **4.2** | ❌ build | ❌ build | ❌ build | ❌ build |
| **5.2** | ❌ build | ❌ build | ❌ build | ❌ build |

## Python 3.12

| Django \ RDKit | 2023.09 | 2024.09 | 2025.09 | 2026.03 |
|---|---|---|---|---|
| **3.2** | ❌ build | ❌ build | ❌ build | ❌ build |
| **4.2** | ❌ build | ❌ build | ❌ build | ❌ build |
| **5.2** | ❌ build | ❌ build | ❌ build | ❌ build |

---

## Failure legend

- **❌ lock** — `uv lock` did not resolve.
- **❌ build** — lock resolved but `docker build` failed (typically a missing system library or native-extension break).
- **—** — no result (cell skipped or workflow interrupted).

## Reproduce a cell locally

```bash
# Example: py3.11 / dj4.2 / rdk2024.09
PY_MIN=3.11 PY_MAX=3.12 \
DJANGO_MAJOR=4.2 DJANGO_NEXT=5.0 \
RDKIT_MAJOR=2024.09 RDKIT_NEXT=2024.10 \
envsubst < pyproject.matrix.toml.tmpl > pyproject.toml
uv lock                                                 # gate 1
docker build --build-arg PYTHON_VERSION=3.11 -t probe . # gate 2
```

