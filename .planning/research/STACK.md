# Technology Stack

**Project:** FiftyOne Datumaro Importer (milestone v1.1)
**Researched:** 2026-06-12

## Recommended Stack Changes for v1.1

### Keep (already in project)
| Technology | Version/Compat | Purpose | Why |
|------------|----------------|---------|-----|
| Python | >=3.10 (recommend 3.11) | Runtime | Matches current package constraints and FiftyOne ecosystem stability |
| fiftyone | >=1.0,<2 | Dataset + visualization | Required for per-field skeleton rendering and dataset workflows |
| pydantic | >=2,<3 | Typed config | Reuse for strict verification config schema |
| PyYAML | >=6,<7 | Config loading | Existing config-first workflow already depends on it |

### Add (minimal)
| Technology | Version/Compat | Purpose | Integration Point |
|------------|----------------|---------|-------------------|
| Pillow | >=10,<12 | Deterministic annotation cropping from image plus bbox/polygon extents | New verification/cropper.py; called from verification pipeline after import/match |
| httpx | >=0.27,<1 | Provider-agnostic VLM API client (optional step) | New verification/vlm_client.py; invoked only when verification.vlm.enabled=true |
| tenacity | >=8,<10 | Retry/backoff for VLM network calls | Wrap httpx VLM requests to reduce transient failures |

## Architecture-Level Integration (code)

1. **Preserve skeleton field rendering pattern**
   - Update src/fiftyone_pose_importer/run_import.py to group keypoints by label-specific field (like src/main.py), and set dataset.skeletons mapping per field instead of relying only on default_skeleton.

2. **Configurable verification pipeline (reusable)**
   - Extend src/fiftyone_pose_importer/config_model.py with nested models:
     - verification.enabled
     - verification.labels[]
     - verification.rules (deterministic checks)
     - verification.vlm (enabled/provider/model/prompt_template/timeout)
     - verification.report (json/csv output path)
   - Keep validation in Pydantic (forbid extra keys, typed enums for rule names/outcomes).

3. **Execution flow additions**
   - Add modules under src/fiftyone_pose_importer/verification/:
     - pipeline.py (orchestrator)
     - cropper.py (Pillow crops)
     - rules.py (deterministic checks)
     - vlm_client.py (optional VLM)
     - reporting.py (JSON/CSV writer)
   - Trigger from CLI after import success (new flag like --verify or config-driven auto-run).

4. **Reporting format**
   - Write machine-readable JSON as canonical report and optional CSV flat export for triage.
   - Keep schema stable: sample id, annotation id, label, crop path/hash, deterministic rule results, vlm result, final status.

## Dependency Update (pyproject.toml)

dependencies = [
  "fiftyone>=1.0.0,<2.0.0",
  "pydantic>=2.0.0,<3.0.0",
  "PyYAML>=6.0.0,<7.0.0",
  "Pillow>=10.0.0,<12.0.0",
  "httpx>=0.27.0,<1.0.0",
  "tenacity>=8.2.0,<10.0.0",
]

## Explicitly NOT Add in v1.1 (scope control)

| Do NOT add | Why |
|------------|-----|
| FastAPI/Flask service layer | v1.1 is local batch utility, not a hosted API |
| Celery/RQ/Kafka job queue | Verification volume does not justify distributed async infra yet |
| Database (Postgres/SQLite ORM) for results | JSON/CSV report files are sufficient and simpler for milestone scope |
| LangChain/LlamaIndex agent frameworks | Adds abstraction and complexity without benefit for deterministic plus templated VLM checks |
| Full plugin framework for rules | Start with simple in-repo rule registry; plugin system can wait |
| Replacing FiftyOne rendering model | Requirement is to preserve existing per-field skeleton rendering behavior |

## Sources

- .planning/PROJECT.md (v1.1 goals and scope)
- src/main.py (known-good per-skeleton field rendering pattern)
- src/fiftyone_pose_importer/run_import.py (current import flow and skeleton handling)
- README.md (current operational model)
- pyproject.toml (current dependency baseline)
