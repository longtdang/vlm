# Coding Conventions

**Analysis Date:** 2026-06-14

## Code Style

**Formatting:**
- No autoformatter config detected (no `.prettierrc`, `ruff.toml`, or `[tool.ruff]` / `[tool.black]` in `pyproject.toml`)
- Line lengths are kept reasonable — long lines avoided but no hard enforced limit observed
- Trailing commas used consistently in multi-line data structures

**Future imports:**
- Every source file begins with `from __future__ import annotations` — applied to all 17 source `.py` files and most test files
- Exception: `src/fiftyone_pose_importer/preflight.py` and `src/fiftyone_pose_importer/config_model.py` do not use it (older phase code)

**Imports:**
- Standard library first, then third-party, then internal relative imports
- `TYPE_CHECKING` guard used for heavy optional imports (e.g., `VlmAdapter` in `run_verify.py`)
- Heavy optional runtime imports (PIL, fiftyone.zoo) are deferred inside functions / lazy-loaded in `__init__`

## Naming Conventions

**Files:**
- `snake_case` throughout: `vlm_engine.py`, `vlm_config.py`, `report_vlm.py`, `run_verify.py`
- Module sub-package: `src/fiftyone_pose_importer/verification/` for verification subsystem

**Functions:**
- `snake_case` for all functions: `evaluate_vlm_object`, `build_prompt`, `parse_vlm_response`
- Private helper functions prefixed with `_`: `_make_det_result`, `_call_with_timeout`, `_bbox_values`, `_safe_token`
- Public loader functions follow `load_*` pattern: `load_vlm_config`, `load_verification_config`, `load_datumaro`

**Variables:**
- `snake_case` throughout
- Descriptive names preferred: `rule_results`, `annotation_payloads`, `vlm_artifact_paths`
- Loop variable shortening only when obvious: `result`, `rule`, `item`

**Classes:**
- `PascalCase` for all classes: `VlmConfig`, `VlmAdapter`, `FiftyOneZooAdapter`, `MockVlmAdapter`, `VerificationConfig`, `VlmObjectResult`
- Error classes use `Error` suffix and inherit from `ValueError`: `VlmConfigError`, `VerificationConfigError`, `UnevaluableRuleError`
- Enum classes use `PascalCase` with `str` mixin: `class VlmVerdict(str, Enum)`, `class DeterministicVerdict(str, Enum)`

**Constants:**
- `UPPER_SNAKE_CASE`: `VALID_ZOO_MODEL_NAMES`, `VALID_VLM_RULES`, `RULE_REGISTRY`, `DEFAULT_PROMPT_TEMPLATE`, `DEFAULT_PADDING_PX`
- Module-level constants typed explicitly: `VALID_ZOO_MODEL_NAMES: frozenset[str]`, `RULE_REGISTRY: dict[str, RuleEvaluator]`

**Type Aliases:**
- Defined at module level with explicit type: `RuleEvaluator = Callable[[dict[str, Any], RuleSpec], tuple[DeterministicVerdict, str | None]]`

## Patterns in Use

**Frozen dataclasses as value objects:**
- All result/config types are `@dataclass(frozen=True)`: `VlmConfig`, `VlmObjectResult`, `VlmRuleResult`, `RuleSpec`, `ObjectVerificationResult`
- Mutation via `dataclasses.replace()` when modification is needed (used in tests)

**Protocol + runtime_checkable for adapter interfaces:**
- `VlmAdapter` in `src/fiftyone_pose_importer/verification/vlm_client.py` is defined as `@runtime_checkable class VlmAdapter(Protocol)` with single method `generate_text`
- Concrete implementations: `FiftyOneZooAdapter` (production), `MockVlmAdapter` (testing/CI)

**Registry pattern for rule dispatch:**
- `RULE_REGISTRY: dict[str, RuleEvaluator]` in `src/fiftyone_pose_importer/verification/rules.py` maps rule name strings to evaluator callables
- Lookup returns `None` for unknown rules (treated as warning, not error)

**Load function + warnings tuple return:**
- Config loaders always return `tuple[Config, list[str]]` where warnings are non-fatal issues:
  - `load_verification_config(raw) -> tuple[VerificationConfig, list[str]]`
  - `load_vlm_config(raw) -> tuple[VlmConfig, list[str]]`
- Unknown rules and unknown model names produce warnings, not exceptions

**Keyword-only arguments for multi-param functions:**
- Functions with many parameters use `*` to force keyword-only: `evaluate_vlm_object(*, result, annotation, crop_image, adapter, vlm_config)`, `evaluate_object(*, sample_id, object_id, label, ...)`

**Fail-safe / REVIEW escalation for errors:**
- VLM errors (timeout, adapter exception, all-invalid output) escalate to `VlmVerdict.REVIEW` rather than crashing
- Deterministic pipeline exceptions use `# pragma: no cover` guards — never propagate exceptions upward

**Lazy imports for heavy optional dependencies:**
- `fiftyone.zoo` imported inside `FiftyOneZooAdapter.generate_text()` on first call
- PIL, fiftyone, yaml imported inside functions when only needed in VLM code paths

**Pydantic for external config models:**
- `ImportConfig` and `ResolvedConfig` in `src/fiftyone_pose_importer/config_model.py` use Pydantic `BaseModel` with `ConfigDict(extra="forbid")`
- VLM and verification configs use plain `dataclasses` + manual parsing (not Pydantic) for flexibility

**str Enum values:**
- Enum `.value` accessed explicitly when serializing: `result.vlm_status.value`, `row.vlm_status.value == "PASS"`
- Enum comparison uses identity: `result.verdict is DeterministicVerdict.PASS`

## Anti-Patterns Observed

**Inconsistent config parsing approach:**
- `ImportConfig` uses Pydantic (`src/fiftyone_pose_importer/config_model.py`) while `VerificationConfig` and `VlmConfig` use manual dict parsing with dataclasses. New config code should follow the manual parsing + `load_*` pattern used in `verification/` for consistency.

**Single `type: ignore` inline suppression:**
- `src/fiftyone_pose_importer/verification/rules.py:48` uses `# type: ignore[assignment]` for a `spec.params.get()` result. Prefer explicit casting or type narrowing over suppression.

**Mixed test isolation strategies across phases:**
- Phase 4/5 tests manually inject fake `fiftyone` modules via `sys.modules` (inline in each test file) — e.g., `test_run_summary_schema.py`, `test_contracts_preflight.py`
- Phase 6/7 tests avoid fiftyone entirely by testing at the verification/VLM layer
- New tests should follow phase 6/7 approach: test against concrete functions that don't require fiftyone

**No `__init__.py` in most test phase directories:**
- Only `tests/phase7/__init__.py` exists; other phase directories lack `__init__.py`. This is acceptable for pytest discovery but inconsistent.

## Documentation Style

**Docstrings:**
- Sparse — only a handful of functions have docstrings
- When present, single-line or short multi-line format without full parameter documentation:
  ```python
  class FiftyOneZooAdapter:
      """Thin wrapper around FiftyOne zoo Qwen3-VL model for raw text generation.

      Loads the model lazily on first call. Not thread-safe — single sequential
      pipeline use only. Per D-01: FiftyOne model-zoo only.
      """
  ```
- Internal helper functions (prefixed `_`) have no docstrings

**Inline comments:**
- Used for non-obvious logic: `# skeleton: [x0, y0, v0, x1, y1, v1, ...]`, `# Locked ordering: adapter failures first, then risk descending, then IDs ascending.`
- `# pragma: no cover - defensive guard for runtime isolation` explains intentional coverage exclusions

**Config YAML comments:**
- `local.verify.yaml` and `config.example.yaml` use inline YAML comments extensively to document options
- Comments explain intent: `# always keep — ensures geometry is valid before other checks`

**README:**
- Present at `/README.md` — not read (contents not inspected), assumed to contain project overview

---

*Convention analysis: 2026-06-14*
