# Tech Stack

**Analysis Date:** 2026-06-14

## Languages

- **Python 3.12** (runtime: `python3.12`, venv: `.venv/`) — entire codebase
- `pyproject.toml` declares `requires-python = ">=3.10"`

## Runtimes & Package Managers

- **Python 3.12.3** — local `.venv` created with `python3 -m venv .venv`
- **pip** — package manager (no lockfile; `pyproject.toml` only)
- **setuptools >= 68 + wheel** — build backend (`[build-system]` in `pyproject.toml`)
- No `requirements.txt`, no `conda`, no `poetry.lock`

## Core Frameworks & Libraries

| Package | Version (installed) | Purpose |
|---------|---------------------|---------|
| `fiftyone` | `>=1.0.0` (declared) | Dataset management, model zoo access, FiftyOne app integration |
| `fiftyone.zoo` | (part of fiftyone) | Loads Qwen3-VL models via `foz.load_zoo_model()` — see `src/fiftyone_pose_importer/verification/vlm_client.py` |
| `pydantic` | `2.13.2` | Config validation (`ImportConfig`, `ResolvedConfig` in `src/fiftyone_pose_importer/config_model.py`) |
| `PyYAML` | `6.0.3` | YAML config parsing (`yaml.safe_load`) throughout `run_verify.py`, `config_loader.py` |
| `Pillow` | `12.2.0` | Image crop/open/save operations — `src/fiftyone_pose_importer/verification/cropper.py`, `vlm_engine.py` |
| `numpy` | `2.4.4` | Transitive dependency (via fiftyone/skimage) |

## Dev Tools

| Tool | Version | Purpose |
|------|---------|---------|
| `pytest` | `9.0.3` | Test runner — all tests in `tests/phase2/` through `tests/phase7/` |
| `setuptools` | `82.0.1` | Build/packaging |
| `wheel` | `0.46.3` | Build wheel distribution |

**No linter or formatter configuration detected** — no `.eslintrc`, no `pyproject.toml [tool.ruff]`/`[tool.black]`/`[tool.isort]` sections, no `.flake8`, no `mypy.ini`.

**Test layout:** Tests are organized in phase subdirectories (`tests/phase2/`, `tests/phase4/`, `tests/phase5/`, `tests/phase6/`, `tests/phase7/`) with a shared `tests/conftest.py`. Tests add `src/` to `sys.path` manually.

## Infrastructure & Deployment

- **No Docker** — no `Dockerfile` or `docker-compose.yml` found
- **No CI/CD pipeline** — no `.github/`, no `.agents/`, no GitHub Actions workflows
- **Install target:** `pip install -e .` (editable install from source)
- **CLI entry points** (declared in `pyproject.toml`):
  - `fiftyone-datumaro-import` → `fiftyone_pose_importer.cli:main`
  - `fiftyone-datumaro-verify` → `fiftyone_pose_importer.run_verify:main`
- **Output:** Verification runs written to local filesystem under `./verification-runs/<timestamp>/`
- **Package name:** `fiftyone-datumaro-importer` v`0.1.0`
- **Source layout:** `src/` layout — `[tool.setuptools] package-dir = {"" = "src"}`

## VLM Model Support

Supported FiftyOne zoo model names (validated in `src/fiftyone_pose_importer/verification/vlm_config.py`):
- `qwen3-vl-2b-instruct-torch`
- `qwen3-vl-4b-instruct-torch`
- `qwen3-vl-8b-instruct-torch`

Models are loaded lazily on first call via `fiftyone.zoo.load_zoo_model()` inside `FiftyOneZooAdapter` (`src/fiftyone_pose_importer/verification/vlm_client.py`).

---

*Stack analysis: 2026-06-14*
