# Codebase Concerns

**Analysis Date:** 2026-06-14

---

## Critical Issues

### Private FiftyOne API Usage in VLM Adapter

- **Issue:** `FiftyOneZooAdapter.generate_text` calls `self._model._generate_detections([image])` — a private, underscore-prefixed method.
- **File:** `src/fiftyone_pose_importer/verification/vlm_client.py:34`
- **Impact:** Any fiftyone release may rename or remove `_generate_detections` without notice, silently breaking all VLM inference with a cryptic `AttributeError`. The entire VLM pipeline collapses.
- **Fix approach:** Either pin fiftyone to a specific minor version and track API changes, or open-source-search for a stable public API surface (`model.predict`, `model.embed_images`, etc.).

### Thread Cancellation Does Not Stop Running VLM Inference

- **Issue:** `_call_with_timeout` in `vlm_engine.py` calls `future.cancel()` after a `TimeoutError`, but `cancel()` on an already-running `Future` is a no-op in Python's `concurrent.futures`. The underlying thread continues executing indefinitely in the background.
- **File:** `src/fiftyone_pose_importer/verification/vlm_engine.py:90–97`
- **Impact:** GPU memory and CPU remain tied up on slow/hung VLM calls long after the timeout fires. Under load this accumulates, potentially causing OOM or stalling subsequent inference.
- **Fix approach:** Accept that Python threads cannot be killed; document that the thread runs to completion despite the timeout. Consider using subprocess isolation or a multiprocessing approach for true cancellation. At minimum, replace `future.cancel()` with a comment explaining it is ineffective.

### Bare `assert` Statements in Production Control Flow

- **Issue:** Two bare `assert` statements are used as flow-control guards in `run_import.py`. Running Python with the `-O` flag silently strips all `assert` statements, causing `NoneType` errors on the next line instead.
- **Files:**
  - `src/fiftyone_pose_importer/run_import.py:101` — `assert bundle.default is not None`
  - `src/fiftyone_pose_importer/run_import.py:232` — `assert contract_bundle is not None`
- **Impact:** In optimised Python deployments (`python -O`), these guards vanish and the subsequent attribute access raises `AttributeError` with no explanatory message.
- **Fix approach:** Replace with explicit `if contract_bundle is None: raise SchemaContractError(...)` guards.

---

## Tech Debt

### `Pillow` Used But Not Declared as a Dependency

- **Issue:** `PIL` (Pillow) is imported directly in `cropper.py`, `vlm_engine.py`, and `vlm_client.py`, but `Pillow` is absent from `pyproject.toml` `[project.dependencies]`. It is only available as a transitive dependency of `fiftyone`.
- **Files:** `src/fiftyone_pose_importer/verification/cropper.py:7`, `vlm_engine.py:8`, `vlm_client.py:5`; `pyproject.toml:11–14`
- **Impact:** If `fiftyone` ever drops or changes its Pillow dependency, imports silently fail at runtime — no install-time warning given to users.
- **Fix approach:** Add `"Pillow>=9.0.0"` to `pyproject.toml` dependencies.

### Duplicate Keypoint/Visibility Extraction Logic

- **Issue:** Two independent implementations of keypoint + visibility parsing exist:
  - `_extract_points_and_visibility` in `src/fiftyone_pose_importer/run_import.py:23–48`
  - `_keypoints_visibility` in `src/fiftyone_pose_importer/run_verify.py:60–83`
  Both decode the Datumaro `skeleton`/`points` format but with subtle differences (e.g., only `run_import.py` validates visibility values; `run_verify.py` silently defaults to `[2, ...]`).
- **Impact:** Bug fixes or format changes must be applied in two places. The divergence in validation strictness may cause different failure modes between import and verify pipelines.
- **Fix approach:** Extract a shared `parse_keypoints_and_visibility` utility into `datumaro_reader.py` or a new `src/fiftyone_pose_importer/annotation_utils.py` and use it in both entry points.

### Inconsistent Configuration Validation Approach

- **Issue:** `pydantic` is declared as a dependency and used for `ImportConfig`/`ResolvedConfig` in `config_model.py`. The entire verification config (`VerificationConfig`, `VlmConfig`) uses hand-rolled `dataclass` + manual dict parsing instead.
- **Files:** `src/fiftyone_pose_importer/config_model.py`, `src/fiftyone_pose_importer/verification/config.py`, `src/fiftyone_pose_importer/verification/vlm_config.py`
- **Impact:** The manual parsing in `config.py` and `vlm_config.py` is verbose (~200+ lines combined) and must be kept consistent manually. Error messages from hand-rolled validation are less structured than pydantic's.
- **Fix approach:** Migrate `VerificationConfig` and `VlmConfig` to pydantic models, or remove pydantic from `pyproject.toml` and standardise on the manual dataclass approach.

### New `ThreadPoolExecutor` Created Per VLM Rule Call

- **Issue:** `_call_with_timeout` in `vlm_engine.py` instantiates a new `ThreadPoolExecutor(max_workers=1)` for every single VLM rule evaluation. For an object with 5 rules, 5 executors are created and torn down.
- **File:** `src/fiftyone_pose_importer/verification/vlm_engine.py:90–97`
- **Impact:** Thread-pool creation overhead accumulates on large datasets; executor teardown blocks until the thread finishes (negating some timeout benefits).
- **Fix approach:** Reuse a single executor across calls (e.g., pass it as a parameter or use a module-level singleton), or accept the overhead since VLM inference latency dominates.

---

## TODO / FIXME Items

No `TODO`, `FIXME`, `HACK`, or `XXX` comments were found in the source tree.

| File | Line | Comment |
|------|------|---------|
| — | — | None detected |

---

## Risk Areas

### Fragile `is_skeleton` Heuristic

- **Files:** `src/fiftyone_pose_importer/run_verify.py:277`
- **Code:** `is_skeleton = ann_type in {"points", "skeleton"} or (bool(keypoints) and ann_type != "polygon")`
- **Why fragile:** Annotation type detection falls through to a presence-of-keypoints fallback when `ann_type` is absent or unexpected. An annotation with `ann_type="bbox"` that also carries a `keypoints` field (valid in Datumaro mixed annotations) will incorrectly be treated as skeleton, changing the crop policy and canvas dimensions.
- **Safe modification:** Add explicit handling for unknown `ann_type` values; log a warning and default to `is_skeleton=False`.

### All Results Buffered in Memory Before Writing Reports

- **Files:** `src/fiftyone_pose_importer/run_verify.py:227–356`
- **Why fragile:** `results: list[ObjectVerificationResult]` and `annotation_payloads: dict` accumulate every annotation result in RAM before `write_run_reports` is called. On datasets with tens of thousands of annotations, this is unbounded memory growth.
- **Safe modification:** Stream results to the NDJSON report incrementally, or add a configurable batch-size flush.

### Hardcoded VLM Model Allowlist

- **File:** `src/fiftyone_pose_importer/verification/vlm_config.py:13–19`
- **Why fragile:** `VALID_ZOO_MODEL_NAMES` contains exactly three `qwen3-vl-*` model names. An unknown model name only emits a warning — the pipeline continues. When fiftyone adds new models or renames existing ones, operators may misconfigure the model name and not notice.
- **Safe modification:** Either make the allowlist configurable via config or promote the unknown-model warning to a soft error that requires explicit `allow_unknown_model: true` opt-in.

### Missing `__init__.py` in Most Test Subdirectories

- **Issue:** Only `tests/phase7/__init__.py` exists. All other test phase directories (`phase2/`, `phase4/`, `phase5/`, `phase6/`) have no `__init__.py`.
- **Impact:** pytest typically handles this fine in `rootdir` mode, but test runners configured with `--import-mode=importlib` or build tools that expect package-style test trees may fail to discover tests. Cross-phase test fixture sharing is not possible.
- **Fix approach:** Add empty `__init__.py` to all `tests/phase*/` directories for consistency, or document that `phase7/__init__.py` is intentional and the others are not.

---

## Missing Functionality

### No Retry Logic for VLM Adapter Failures

- **File:** `src/fiftyone_pose_importer/verification/vlm_engine.py:119–150`
- **Problem:** Transient adapter errors (network issues, GPU OOM spikes) immediately set `vlm_status=REVIEW` and skip remaining rules for the object. There is no retry or back-off mechanism.
- **Blocks:** Reliable unattended batch processing — a single transient GPU hiccup marks an object for manual review.

### No Batched VLM Inference

- **File:** `src/fiftyone_pose_importer/run_verify.py:383–416`
- **Problem:** Objects are sent to `evaluate_vlm_object` one at a time in a sequential `for result in results` loop. The VLM model is never invoked on a batch of images simultaneously.
- **Blocks:** Efficient GPU utilisation; throughput scales linearly with annotation count.

### No CLI Progress Reporting or Streaming Output

- **File:** `src/fiftyone_pose_importer/run_verify.py:457–471`
- **Problem:** The CLI `main()` runs the full verification pipeline silently and only prints a final JSON summary. For large datasets, operators have no indication of progress or estimated time remaining.

### VLM Pipeline Has No Dry-Run Mode

- **Problem:** There is no way to validate VLM config (model name, label/rule mappings, prompt templates) without actually loading the model and running inference.

---

## Performance Concerns

### Sequential Per-Object VLM Inference Is a Bottleneck

- **File:** `src/fiftyone_pose_importer/run_verify.py:383–416`
- **Problem:** Every deterministic-PASS object is sent to `evaluate_vlm_object` in sequence. Each call blocks on `_call_with_timeout` which synchronously waits (up to `timeout_seconds`) for the GPU. For 1,000 objects × 2 rules × 8-second timeout, worst-case wall time is 16,000 seconds.
- **Improvement path:** Batch images for rules that share the same prompt template; or introduce a `max_workers` parameter to run objects concurrently.

### New ThreadPoolExecutor Per Rule Invocation

- **File:** `src/fiftyone_pose_importer/verification/vlm_engine.py:90–97`
- **Problem:** A new thread pool is created and destroyed for every rule evaluation, including thread creation/teardown overhead. Inexpensive at small scale; adds up for thousands of objects × multiple rules.
- **Improvement path:** Reuse a single `ThreadPoolExecutor` scoped to the duration of `run_verify`.

---

## Dependency Risks

### `fiftyone>=1.0.0` — No Upper Bound, Private API Dependency

- **File:** `pyproject.toml:12`
- **Risk:** The `fiftyone>=1.0.0` constraint has no upper bound. The `_generate_detections` private method relied upon in `vlm_client.py:34` may change in any minor or patch release.
- **Impact:** Silent breakage of all VLM inference with no install-time warning.
- **Migration plan:** Pin `fiftyone>=1.0.0,<2.0.0`, add a CI test against the pinned version, and file a tracking issue to migrate off the private API.

### `Pillow` Not Declared — Transitive Dependency Only

- **File:** `pyproject.toml` (absent)
- **Risk:** Pillow is depended upon directly but only arrives transitively via fiftyone. A fiftyone packaging change could silently drop it.
- **Migration plan:** Add `"Pillow>=9.0.0"` to `[project.dependencies]`.

### `pydantic>=2.0.0` — No Upper Bound, Only Partially Used

- **File:** `pyproject.toml:13`
- **Risk:** pydantic v3 (if released) may introduce breaking changes to `BaseModel`/`field_validator`. The package is also used only for the import path, not the verification path, suggesting possible removal.
- **Migration plan:** Either remove pydantic and migrate `ImportConfig` to a plain dataclass + manual validation (consistent with verification config approach), or add `pydantic>=2.0.0,<3.0.0` upper bound.

### Model Allowlist Requires Code Changes for New VLMs

- **File:** `src/fiftyone_pose_importer/verification/vlm_config.py:13–19`
- **Risk:** `VALID_ZOO_MODEL_NAMES` is a frozenset literal. Adding support for new FiftyOne zoo models (e.g., `qwen3-vl-14b-instruct-torch`) requires a code change and a new release. Unknown models only emit a warning, not an error.
- **Migration plan:** Expose the allowlist as a config option or make validation opt-in via `strict_model_validation: true` flag.

---

*Concerns audit: 2026-06-14*
