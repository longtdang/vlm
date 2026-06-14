<!-- refreshed: 2026-06-14 -->
# Codebase Structure

**Analysis Date:** 2026-06-14

## Top-Level Layout

```
vlm/
├── src/                          # All production Python source
│   └── fiftyone_pose_importer/   # Main package (installed as fiftyone-datumaro-importer)
│       ├── verification/         # Verification sub-package (deterministic + VLM)
│       └── *.py                  # Top-level pipeline modules
├── tests/                        # Pytest test suite, organised by phase
│   ├── phase2/                   # Import pipeline tests (contract + matching)
│   ├── phase4/                   # CLI launch/summary schema tests
│   ├── phase5/                   # Contracts & preflight integration tests
│   ├── phase6/                   # Deterministic verification tests
│   └── phase7/                   # VLM verification tests
├── data/                         # Local dev sample data
│   ├── images/                   # Sample PNG images for manual runs
│   └── default.json              # Sample Datumaro JSON
├── docs/                         # Design documents & specs
│   └── superpowers/
│       ├── plans/                # Implementation plans
│       └── specs/                # Design specs
├── .planning/                    # GSD planning artefacts (not source)
│   ├── codebase/                 # Codebase map documents (this dir)
│   ├── phases/                   # Per-phase plans & summaries
│   ├── research/                 # Research notes
│   └── milestones/               # Milestone requirements & roadmaps
├── pyproject.toml                # Package metadata, deps, entry points
├── config.example.yaml           # Import-only config example
├── config.import-only.example.yaml  # Import-only minimal config
├── config.import-vlm.example.yaml   # Full import + deterministic + VLM config with inline docs
├── local.verify.yaml             # Local dev config (gitignored pattern)
├── local.verify.summary.json     # Last local run summary (gitignored pattern)
└── README.md
```

## Module Breakdown

| Module/Package | Purpose |
|----------------|---------|
| `fiftyone_pose_importer` | Top-level package; `__init__.py` is minimal |
| `fiftyone_pose_importer.cli` | CLI entry point; subcommand dispatch (`import` / `verify`) and legacy fallback |
| `fiftyone_pose_importer.run_import` | Full import pipeline: config → image index → match → FiftyOne dataset write |
| `fiftyone_pose_importer.run_verify` | Full verify pipeline: config → Datumaro parse → crop → deterministic engine → optional VLM → reports |
| `fiftyone_pose_importer.config_loader` | YAML → pydantic model load + path resolution |
| `fiftyone_pose_importer.config_model` | Pydantic `ImportConfig` and `ResolvedConfig` models |
| `fiftyone_pose_importer.datumaro_reader` | JSON load + minimal structural validation |
| `fiftyone_pose_importer.image_index` | Directory walk → stem-normalised `dict[str, Path]`; duplicate detection |
| `fiftyone_pose_importer.matching` | Join image index and annotation items on normalised filename stem |
| `fiftyone_pose_importer.pose_contract` | Extract `SkeletonContract` / `SkeletonContractBundle` from Datumaro categories |
| `fiftyone_pose_importer.preflight` | `PreflightReport` dataclass; accumulates pre-import validation issues |
| `fiftyone_pose_importer.summary` | Write run summary JSON adjacent to config file |
| `fiftyone_pose_importer.verification` | Sub-package for all verification logic; exports public API via `__init__.py` |
| `fiftyone_pose_importer.verification.types` | Frozen dataclasses & enums for deterministic verification (`DeterministicVerdict`, `ObjectVerificationResult`, `RuleResult`, etc.) |
| `fiftyone_pose_importer.verification.vlm_types` | Frozen dataclasses & enums for VLM results (`VlmVerdict`, `VlmObjectResult`, `VlmRuleResult`) |
| `fiftyone_pose_importer.verification.config` | Parse `verification.deterministic` YAML into `VerificationConfig`; default + per-label override logic |
| `fiftyone_pose_importer.verification.vlm_config` | Parse `verification.vlm` YAML into `VlmConfig`; validate model names, thresholds, prompts |
| `fiftyone_pose_importer.verification.cropper` | Pure `plan_crop()` + I/O `materialize_crop()`; two crop policies |
| `fiftyone_pose_importer.verification.engine` | `evaluate_object()` — orchestrates rule categories against a single annotation |
| `fiftyone_pose_importer.verification.rules` | `RULE_REGISTRY` + stateless rule evaluator functions |
| `fiftyone_pose_importer.verification.vlm_client` | `VlmAdapter` protocol; `FiftyOneZooAdapter` (production); `MockVlmAdapter` (tests) |
| `fiftyone_pose_importer.verification.vlm_engine` | `evaluate_vlm_object()` — prompt building, adapter call with timeout, response parsing, risk aggregation |
| `fiftyone_pose_importer.verification.report_csv` | Write `deterministic_report.csv`; run-dir helpers (`_safe_run_dir`, `_safe_run_timestamp`) |
| `fiftyone_pose_importer.verification.report_json` | Write `deterministic_report.json`; `serialize_object_result()` |
| `fiftyone_pose_importer.verification.report_ndjson` | Write `deterministic_trace.ndjson` (one record per line) |
| `fiftyone_pose_importer.verification.report_vlm` | Write `vlm_report.{csv,json,ndjson}`; `serialize_vlm_object_result()`; review queue ordering |

## Key Files

| File | Purpose |
|------|---------|
| `pyproject.toml` | Package name `fiftyone-datumaro-importer`, entry points, deps (`fiftyone`, `pydantic`, `PyYAML`) |
| `src/fiftyone_pose_importer/cli.py` | `main()` — CLI entry point for `fiftyone-datumaro-import` |
| `src/fiftyone_pose_importer/run_verify.py` | `run_verify()` — orchestrates the full verification pipeline including VLM |
| `src/fiftyone_pose_importer/run_import.py` | `run_import()` — orchestrates full import pipeline |
| `src/fiftyone_pose_importer/verification/config.py` | `load_verification_config()`, `VerificationConfig`, `KNOWN_RULES`, `DEFAULT_RULES` |
| `src/fiftyone_pose_importer/verification/vlm_config.py` | `load_vlm_config()`, `VlmConfig`, `VALID_VLM_RULES`, `VALID_ZOO_MODEL_NAMES` |
| `src/fiftyone_pose_importer/verification/rules.py` | `RULE_REGISTRY` dict — add new deterministic rules here |
| `src/fiftyone_pose_importer/verification/vlm_engine.py` | `evaluate_vlm_object()`, `build_prompt()`, `parse_vlm_response()`, `RULE_ANNOTATION_FIELDS` |
| `src/fiftyone_pose_importer/verification/cropper.py` | `plan_crop()`, `materialize_crop()`, `CropPlan` |
| `src/fiftyone_pose_importer/verification/__init__.py` | Public API surface for the `verification` sub-package |
| `config.import-vlm.example.yaml` | Full annotated config reference including all VLM options and rule documentation |
| `tests/conftest.py` | Shared pytest fixtures |
| `tests/phase7/` | Phase 7 VLM tests — most recent phase |

## Naming Conventions

**Files:**
- Snake_case Python modules: `run_verify.py`, `vlm_config.py`, `report_ndjson.py`
- `report_<format>.py` naming for all report writers
- `vlm_` prefix for all VLM-specific modules: `vlm_client.py`, `vlm_config.py`, `vlm_engine.py`, `vlm_types.py`
- Test files: `test_<module_or_feature>.py` placed in `tests/phase<N>/`

**Directories:**
- Test directories match development phases: `phase2/`, `phase4/`, `phase5/`, `phase6/`, `phase7/`
- Runtime output: `<output_dir>/<YYYYMMDDTHHMMSSZ>/` (timestamped run dir)
- Crops sub-directory: `<run_dir>/crops/<sample_id>_<object_id>.png`

## Where to Add New Code

**New deterministic rule:**
1. Add evaluator function in `src/fiftyone_pose_importer/verification/rules.py`
2. Register in `RULE_REGISTRY` dict (same file)
3. Add rule name to appropriate category in `KNOWN_RULES` dict in `src/fiftyone_pose_importer/verification/config.py`
4. Add to `DEFAULT_RULES` if it should apply by default
5. Tests: `tests/phase6/test_rules_engine.py`

**New VLM rule:**
1. Add rule name to `VALID_VLM_RULES` in `src/fiftyone_pose_importer/verification/vlm_config.py`
2. Add annotation field mapping in `RULE_ANNOTATION_FIELDS` in `src/fiftyone_pose_importer/verification/vlm_engine.py`
3. Add to `VLM_RULE_NAMES` list in `src/fiftyone_pose_importer/verification/report_vlm.py` (controls CSV columns)
4. Tests: `tests/phase7/test_vlm_engine.py`

**New report format:**
- Implementation: `src/fiftyone_pose_importer/verification/report_<format>.py`
- Register in `write_run_reports()` in `src/fiftyone_pose_importer/verification/report_csv.py` (deterministic) or `write_vlm_reports()` in `report_vlm.py` (VLM)
- Tests: `tests/phase6/test_reporting.py` (deterministic) or `tests/phase7/test_report_vlm.py` (VLM)

**New CLI subcommand:**
- Add to `_main_with_subcommands()` in `src/fiftyone_pose_importer/cli.py`
- Register entry point in `pyproject.toml` if a standalone script is needed

**New top-level config field:**
- Add to `ImportConfig` pydantic model in `src/fiftyone_pose_importer/config_model.py`
- Update `run_import.py` or `run_verify.py` to consume it
- Update `config.import-vlm.example.yaml` with documentation

## Generated/Build Artifacts

- `src/fiftyone_datumaro_importer.egg-info/` — generated by `pip install -e .`; do not edit; not committed as source
- `src/fiftyone_pose_importer/__pycache__/` — Python bytecode cache; gitignored
- `src/fiftyone_pose_importer/verification/__pycache__/` — Python bytecode cache; gitignored
- `<output_dir>/<timestamp>/` — verification run artifacts (CSV, JSON, NDJSON, crop PNGs); generated at runtime; not in repo
- `local.verify.summary.json` — local run summary; present in repo root as dev convenience artefact

## Special Directories

**`data/images/`:**
- Purpose: Sample warehouse images for local manual testing
- Generated: No (manually added sample images)
- Committed: Yes (sample data for dev)

**`data/`:**
- Purpose: Dev sample Datumaro JSON (`default.json`) and images
- Committed: Yes

**`.planning/`:**
- Purpose: GSD project management artefacts — phases, milestones, research notes, codebase maps
- Generated: By GSD planning commands
- Committed: Yes

**`docs/superpowers/`:**
- Purpose: Design specifications and implementation plans authored during development
- Committed: Yes

---

*Structure analysis: 2026-06-14*
