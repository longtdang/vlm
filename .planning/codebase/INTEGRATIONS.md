# Integrations

**Analysis Date:** 2026-06-14

## External Services

### FiftyOne Model Zoo (Qwen3-VL)
- **What:** Hosts and downloads vision-language models locally
- **SDK:** `fiftyone.zoo` (`import fiftyone.zoo as foz`)
- **Usage:** `foz.load_zoo_model(model_name, max_new_tokens=...)` in `src/fiftyone_pose_importer/verification/vlm_client.py`
- **Auth:** None — models are downloaded from public FiftyOne zoo registry on first use
- **Models used:** `qwen3-vl-2b-instruct-torch`, `qwen3-vl-4b-instruct-torch`, `qwen3-vl-8b-instruct-torch`
- **Network requirement:** Internet access on first model download; subsequent runs use local cache

### FiftyOne Dataset Management
- **What:** Dataset storage, querying, and visualization app
- **SDK:** `fiftyone` (`import fiftyone as fo`)
- **Usage:** `run_import.py` imports Datumaro annotations into FiftyOne datasets
- **Storage:** FiftyOne uses a local MongoDB instance (managed by fiftyone itself) for dataset metadata
- **App:** `--launch` flag starts the FiftyOne app UI for dataset browsing

## Databases & Storage

### Local Filesystem (primary storage)
- **Input:** Datumaro JSON annotation files (`datumaro_json` config key)
- **Input:** Source image files (`image_dir` config key)
- **Output:** Verification run artifacts under `./verification-runs/<timestamp>/`:
  - `deterministic_report.csv` — per-object deterministic results
  - `deterministic_report.json` — same data as JSON
  - `deterministic_report.ndjson` — newline-delimited JSON
  - `vlm_report.csv` — VLM verification results (when VLM enabled)
  - `vlm_report.json` — same data as JSON
  - `crops/` — PNG image crops per annotation (written by `src/fiftyone_pose_importer/verification/cropper.py`)
- **Summary:** `local.verify.summary.json` — last run summary output

### FiftyOne Local MongoDB
- **What:** FiftyOne internally manages a local MongoDB instance for dataset persistence
- **Connection:** Managed entirely by the `fiftyone` library; no direct connection string in this codebase
- **Accessed via:** `import fiftyone as fo` → `fo.load_dataset()`, `fo.Dataset()` etc. in `src/fiftyone_pose_importer/run_import.py`

## Internal Integrations

### Datumaro JSON Format (CVAT export)
- **What:** Annotation data format from CVAT / Datumaro pipeline
- **Parser:** `src/fiftyone_pose_importer/datumaro_reader.py` — reads JSON, extracts `items`, `categories`, `annotations`
- **Annotation types handled:** `skeleton`, `polygon`, `points`, `bbox`
- **Label mapping:** Integer `label_id` → string label name via `categories.label.labels[]` array

### Verification Pipeline (internal two-stage)
- **Stage 1 — Deterministic:** Rules engine in `src/fiftyone_pose_importer/verification/engine.py` evaluates bbox, attribute, skeleton-count, visibility-format rules
- **Stage 2 — VLM:** `src/fiftyone_pose_importer/verification/vlm_engine.py` sends image crops + prompts to the VLM adapter; only runs on deterministic-PASS objects
- **Orchestrated by:** `src/fiftyone_pose_importer/run_verify.py`

## Auth & Identity

- **None** — this is a local CLI tool with no authentication, no user accounts, no OAuth, no API keys
- All paths are local filesystem only; `config_model.py` explicitly rejects URLs (`"://" in value` check)

## CI/CD & Deployment

- **None detected** — no `.github/workflows/`, no CI configuration files
- **No Docker** — no `Dockerfile` or `docker-compose.yml`
- **No cloud provider SDKs** — no AWS, GCP, or Azure imports detected

## Environment Configuration

- Config is file-based YAML only — no environment variables required for operation
- Example configs: `config.example.yaml`, `config.import-only.example.yaml`, `config.import-vlm.example.yaml`
- Local config convention: `local.verify.yaml` (gitignored)
- No `.env` file mechanism

---

*Integration audit: 2026-06-14*
