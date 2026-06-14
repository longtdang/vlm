<!-- refreshed: 2026-06-14 -->
# Architecture

**Analysis Date:** 2026-06-14

## System Overview

A config-driven CLI pipeline that ingests CVAT/Datumaro pose annotations plus local images, imports them into FiftyOne as keypoint datasets, and runs a two-stage verification pass: a deterministic rule engine followed by an optional VLM (vision-language model) quality check via FiftyOne model-zoo.

## Components

| Component | Responsibility | Key Files |
|-----------|----------------|-----------|
| **CLI** | Entry-point dispatch; routes `import` / `verify` subcommands or legacy import invocation | `src/fiftyone_pose_importer/cli.py` |
| **Import Pipeline** | Load config → index images → match annotations → build FiftyOne samples → write dataset | `src/fiftyone_pose_importer/run_import.py` |
| **Verify Pipeline** | Load config → parse Datumaro → crop each object → run deterministic rules → optionally invoke VLM stage → write reports | `src/fiftyone_pose_importer/run_verify.py` |
| **Config Loader** | Parse & validate YAML config into typed `ImportConfig` / `ResolvedConfig` pydantic models | `src/fiftyone_pose_importer/config_loader.py`, `src/fiftyone_pose_importer/config_model.py` |
| **Datumaro Reader** | Thin JSON loader; validates `items` list presence | `src/fiftyone_pose_importer/datumaro_reader.py` |
| **Image Index** | Walk image directory; build stem→Path lookup; detect duplicates | `src/fiftyone_pose_importer/image_index.py` |
| **Matcher** | Join image index against annotation items on normalized filename stem | `src/fiftyone_pose_importer/matching.py` |
| **Pose Contract** | Extract skeleton label/edge contracts from Datumaro categories; support multi-label bundles | `src/fiftyone_pose_importer/pose_contract.py` |
| **Preflight Report** | Accumulate pre-import health signals (duplicates, unmatched keys, schema mismatches) | `src/fiftyone_pose_importer/preflight.py` |
| **Summary Writer** | Serialise run summary JSON next to config file | `src/fiftyone_pose_importer/summary.py` |
| **Verification Config** | Parse `verification.deterministic` YAML block into `VerificationConfig`; support global rules + per-label overrides | `src/fiftyone_pose_importer/verification/config.py` |
| **Cropper** | Plan and materialise per-annotation image crops with configurable padding; two policies: `skeleton_preserve_canvas` and `non_skeleton_clip`; marks out-of-frame keypoints occluded | `src/fiftyone_pose_importer/verification/cropper.py` |
| **Deterministic Engine** | Evaluate annotation against ordered rule categories (detection → attribute → skeleton-count → visibility-format); emit `ObjectVerificationResult` | `src/fiftyone_pose_importer/verification/engine.py` |
| **Rule Registry** | Stateless evaluators keyed by name: `bbox_format`, `bbox_non_empty`, `required_attributes`, `roll_count_positive`, `clamp_type_allowed`, `keypoint_count`, `visibility_codes` | `src/fiftyone_pose_importer/verification/rules.py` |
| **VLM Config** | Parse `verification.vlm` YAML block; validate model name, thresholds, per-label rules & prompt templates | `src/fiftyone_pose_importer/verification/vlm_config.py` |
| **VLM Client / Adapter** | Protocol `VlmAdapter` + `FiftyOneZooAdapter` (lazy model load via `fiftyone.zoo`) + `MockVlmAdapter` for tests | `src/fiftyone_pose_importer/verification/vlm_client.py` |
| **VLM Engine** | Build prompts from templates; call adapter with per-rule timeout (thread executor); parse JSON response (`error_probability` float); aggregate risk score; emit `VlmObjectResult` with PASS/REVIEW/FAIL verdict | `src/fiftyone_pose_importer/verification/vlm_engine.py` |
| **Reporting — Deterministic** | Write `deterministic_report.csv`, `deterministic_report.json`, `deterministic_trace.ndjson` into timestamped run dir | `src/fiftyone_pose_importer/verification/report_csv.py`, `report_json.py`, `report_ndjson.py` |
| **Reporting — VLM** | Write `vlm_report.csv`, `vlm_report.json` (with `review_queue`), `vlm_trace.ndjson` into same run dir | `src/fiftyone_pose_importer/verification/report_vlm.py` |
| **Shared Types** | Frozen dataclasses and enums: `DeterministicVerdict`, `VlmVerdict`, `ObjectVerificationResult`, `VlmObjectResult`, `RuleResult`, `VlmRuleResult`, etc. | `src/fiftyone_pose_importer/verification/types.py`, `vlm_types.py` |

## Data Flow

### Import command (`fiftyone-datumaro-import import --config …`)

```
YAML config
    │
    ▼
config_loader.load_config()  →  ResolvedConfig
    │
    ├─→ datumaro_reader.load_datumaro()       →  raw dict {items, categories}
    ├─→ image_index.build_image_index()        →  stem→Path index
    ├─→ matching.build_matches()               →  [(image_path, item), …]
    ├─→ pose_contract.extract_skeleton_contract_bundle()  →  SkeletonContractBundle
    ├─→ preflight.PreflightReport  (gates pipeline on errors)
    │
    ▼
For each matched (image_path, item):
    └─→ fo.Sample  ←  normalised keypoints, visibility, skeleton metadata
         written to fo.Dataset via dataset.add_samples()
    │
    ▼
summary.write_summary()  →  <config_stem>.summary.json
stdout  →  JSON summary
```

### Verify command (`fiftyone-datumaro-verify verify --config …` or `fiftyone-datumaro-verify --config …`)

```
YAML config
    │
    ├─→ load_verification_config()  →  VerificationConfig
    ├─→ datumaro_reader.load_datumaro()
    │
    ▼
For each item → annotation:
    ├─→ cropper.plan_crop()     →  CropPlan  (or FAIL with reason)
    ├─→ cropper.materialize_crop()  →  PNG file in run_dir/crops/
    └─→ engine.evaluate_object()    →  ObjectVerificationResult
              │
              └─→ rules.evaluate_rule()  ×N  →  RuleResult[]
    │
    ▼
report_csv.write_run_reports()  →  deterministic_report.{csv,json,ndjson}
    │
    ▼  (only if verification.vlm.enabled = true)
For each PASS result where label is VLM-enabled:
    ├─→ PIL.Image.open(crop_path)
    └─→ vlm_engine.evaluate_vlm_object()
              ├─→ vlm_engine.build_prompt()  (template substitution per rule)
              ├─→ VlmAdapter.generate_text()  (with timeout via ThreadPoolExecutor)
              └─→ vlm_engine.parse_vlm_response()  →  VlmRuleResult
              →  aggregate max risk  →  VlmObjectResult (PASS/REVIEW/FAIL)
    │
    ▼
report_vlm.write_vlm_reports()  →  vlm_report.{csv,json,ndjson}
    │
    ▼
stdout  →  JSON summary (counts, artifact paths, warnings)
```

## Key Patterns

- **Two-stage verification gate**: Only annotations that pass the deterministic engine proceed to the VLM stage. VLM is purely additive and does not rewrite deterministic results.
- **CropPlan / materialize separation**: `plan_crop()` is a pure function returning a `CropPlan` dataclass (no I/O). `materialize_crop()` performs the actual file write. This keeps crop logic unit-testable without disk access.
- **Rule registry pattern**: `RULE_REGISTRY` in `rules.py` maps string names to stateless callable evaluators. New rules are added by inserting into the registry and referencing the name in YAML config.
- **Label-overridable config**: `VerificationConfig.rules_for_label()` and `VlmConfig.rules_for_label()` both support global defaults with per-label overrides — enabling different keypoint counts, thresholds, and prompt templates per annotation class.
- **VlmAdapter Protocol**: `VlmAdapter` is a `typing.Protocol` — any object with `generate_text(image, prompt) -> str` is a valid adapter. `FiftyOneZooAdapter` is the production implementation; `MockVlmAdapter` is used in tests without model loading.
- **Frozen dataclasses throughout**: All result and config types (`ObjectVerificationResult`, `VlmObjectResult`, `CropPlan`, `VerificationConfig`, etc.) are `@dataclass(frozen=True)` — immutable after construction.
- **Preflight-as-gate**: `PreflightReport.has_errors()` blocks FiftyOne dataset writes; errors cause `run_import()` to return `(False, summary)` before any data is written.
- **Security-conscious path handling**: `_is_within()` checks in `run_verify.py` and `config_model.py` URL rejection guard against path traversal and remote URLs.
- **Timestamped run directories**: Each verify invocation writes artifacts into `<output_dir>/<YYYYMMDDTHHMMSSZ>/` — deterministic reports and VLM reports share the same run dir.
- **Single-threaded VLM model**: `FiftyOneZooAdapter` explicitly documents non-thread-safety; `_call_with_timeout` uses a single-worker thread executor only for timeout enforcement, not parallelism.

## Entry Points

| Entry Point | Invocation | Source |
|-------------|-----------|--------|
| `fiftyone-datumaro-import` | `fiftyone-datumaro-import import --config <yaml>` or legacy `fiftyone-datumaro-import --config <yaml>` | `src/fiftyone_pose_importer/cli.py:main()` |
| `fiftyone-datumaro-verify` | `fiftyone-datumaro-verify verify --config <yaml>` or `fiftyone-datumaro-verify --config <yaml>` | `src/fiftyone_pose_importer/run_verify.py:main()` |
| Direct Python module | `python -m fiftyone_pose_importer.cli` | `src/fiftyone_pose_importer/cli.py` |

## Architectural Constraints

- **Threading**: Single-threaded sequential pipeline. `ThreadPoolExecutor(max_workers=1)` in `vlm_engine._call_with_timeout` is used solely for timeout enforcement on blocking VLM calls — not for concurrency.
- **Global state**: `FiftyOneZooAdapter._model` is instance-level lazy state; FiftyOne dataset operations (`fo.Dataset`, `fo.launch_app`) are global-session singletons managed by the FiftyOne library.
- **No circular imports**: `verification/` sub-package imports only from within itself or from the parent package's `datumaro_reader`; top-level modules import from `verification/` but not vice versa.
- **VLM only on PASS objects**: The VLM loop in `run_verify.py` (line 384) explicitly filters `result.verdict is not DeterministicVerdict.PASS` — failed objects are never sent to the model.
- **PIL dependency for VLM**: `PIL` (Pillow) is imported lazily inside the `if vlm_enabled:` branch of `run_verify.py` — it is not required for deterministic-only runs.

## Anti-Patterns

### Importing FiftyOne in non-import path
**What happens:** `fiftyone as fo` is imported at module top-level in `run_import.py` (line 7).
**Why it's wrong:** This forces FiftyOne (a heavy dependency) to load whenever `run_import` is imported, even in verify-only or test scenarios.
**Do this instead:** Guard `import fiftyone as fo` inside `run_import()` body, mirroring how VLM imports are guarded inside `if vlm_enabled:`.

## Error Handling

**Strategy:** Pipeline functions return `(bool, dict)` tuples (`ok`, `summary`) rather than raising to the caller. Exceptions at the per-annotation level are caught and converted to `_failure_result()` entries; only config/IO errors at startup propagate as exceptions to the CLI layer, which catches them and prints a JSON error to stderr.

**Patterns:**
- Per-annotation failures → `ObjectVerificationResult(verdict=FAIL, failure_reasons=[reason])` — pipeline continues
- `UnevaluableRuleError` in rule evaluators → caught in `evaluate_rule()` → becomes `RuleResult(verdict=FAIL, reason="unevaluable:…")` — not a warning
- Unknown rule names → warning string appended; rule skipped (not a failure)
- VLM adapter errors (including timeout) → `VlmObjectResult(vlm_status=REVIEW, failure_reason=…)` — REVIEW is the safe default on uncertainty
- Config errors → `VerificationConfigError` / `VlmConfigError` (both extend `ValueError`) raised from loaders; caught at `run_verify()` boundary

## Cross-Cutting Concerns

**Logging:** No structured logging framework — status communicated entirely via the returned summary dict and JSON stdout/stderr output in CLI.
**Validation:** Config validation in `config_model.py` (pydantic), `config.py` (manual), `vlm_config.py` (manual). Annotation data validated inline in `run_verify.py` with fallback to `_failure_result()`.
**Authentication:** None — local filesystem only; `config_model.py` explicitly rejects `://` URLs.

---

*Architecture analysis: 2026-06-14*
