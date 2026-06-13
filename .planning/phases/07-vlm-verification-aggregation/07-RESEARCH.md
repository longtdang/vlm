# Phase 7: VLM Verification & Aggregation - Research

**Researched:** 2026-06-13
**Domain:** FiftyOne model zoo VLM inference · Python duck-type adapter pattern · Risk aggregation pipeline
**Confidence:** HIGH (all claims verified against live installed codebase and FiftyOne source)

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**Adapter strategy**
- D-01: Phase 7 uses only FiftyOne model-zoo models — no external HTTP adapter endpoint.
- D-02: Active model is configured by name (one model at a time, e.g., `qwen3-vl-2b`, `qwen3-vl-4b`, `qwen3-vl-8b`).
- D-03: If the configured model fails to load or inference throws, mark object as `REVIEW` with failure_reason recorded.
- D-04: No fallback chain — single configured model, fail → REVIEW.

**VLM label scope**
- D-05: VLM verification is opt-in per label — controlled via config (`verification.vlm.labels.<label>.enabled: true`).
- D-06: Labels not in the VLM opt-in list remain deterministic-only; their final status is the deterministic verdict.
- D-07: Per VLM-enabled label, a per-label explicit rule list specifies which of the six rules to evaluate (`bbox_localization`, `bbox_coverage`, `clamp_type`, `roll_count`, `keypoint_position`, `occlusion_state`).

**VLM execution gate**
- D-08: Objects that failed deterministic checks skip VLM entirely; their final status remains `FAIL`.
- D-09: Only deterministic `PASS` objects in VLM-enabled labels proceed to VLM rules.

**Prompt and response contract**
- D-10: Per-label per-rule prompt templates are supported; each label/rule pair may define a custom template. A global default template is used as fallback when no per-label template is set.
- D-11: Each VLM rule prompt receives: crop image + label name + rule name + relevant annotation fields (bbox, visibility, attribute values as applicable to the rule).
- D-12: VLM response must be strict JSON: `{"error_probability": float, "reason": str, "evidence": str (optional)}`.
- D-13: If `error_probability` is missing, non-numeric, or outside `[0.0, 1.0]`, the rule result is marked `invalid_output`; the object is marked `REVIEW` with reason.
- D-14: VLM generation parameters default to deterministic settings (e.g., temperature=0 equivalent). User may override in config.

**Risk aggregation**
- D-15: `object_risk = max(error_probability across all VLM rules for the object)`.
- D-16: Default thresholds (configurable): PASS ≤ 0.20, REVIEW ≤ 0.60, FAIL > 0.60.
- D-17: Thresholds support global defaults with optional per-label overrides in config.
- D-18: If VLM produces no valid rule result (adapter fail / all invalid_output), object status is `REVIEW` with failure_reason.

**Artifacts**
- D-19: Phase 7 emits separate VLM artifacts alongside Phase 6 deterministic artifacts in the same timestamped run directory: `vlm_report.csv`, `vlm_report.json`, `vlm_trace.ndjson`.
- D-20: Each VLM artifact row/entry includes: `sample_id`, `object_id`, `label`, `vlm_status` (PASS/REVIEW/FAIL), `object_risk`, per-rule `error_probability` + `reason`, `adapter_model`, `failure_reason`.

**Review queue**
- D-21: Review queue is embedded in `vlm_report.json` as an ordered list (`review_queue`), sorted by: risk descending → adapter_failure first → sample_id/object_id ascending.

**Testing**
- D-22: Phase 7 tests use a mock FiftyOne model that returns deterministic JSON responses — no real GPU or model download required for CI.

### Claude's Discretion
No open discretion items; all decisions above are locked.

### Deferred Ideas (OUT OF SCOPE)
- External OpenAI-compatible HTTP endpoint — removed from Phase 7 scope per D-01; defer to future milestone if needed.
- Interactive review dashboard (VLM-06) — explicitly deferred in REQUIREMENTS.md.
- Auto-apply VLM correction suggestions (VLM-07) — explicitly deferred in REQUIREMENTS.md.

</user_constraints>

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| VLM-01 | User can configure which labels/classes are VLM-verified and which remain deterministic-only. | VLM config schema (vlm_config.py), per-label `enabled` flag, global-defaults + per-label-override pattern identical to existing `config.py`. |
| VLM-02 | User can configure prompt templates and rule-linked prompt parameters per verified label; per-rule prompt mapping covers rules: bbox_localization, bbox_coverage, clamp_type, roll_count, keypoint_position, occlusion_state. | Prompt template config in vlm_config.py; rule→annotation-field mapping documented in §Rule Prompt Mapping. |
| VLM-03 | User can run VLM verification only as an optional stage after deterministic checks; each VLM rule returns an error_probability and per-object aggregation computes a risk score (object_risk = max(rule error_probability)). | vlm_engine.py runs per eligible object; aggregation formula confirmed in CONTEXT.md D-15. |
| VLM-04 | User can receive safe fallback `REVIEW` outcomes when VLM checks fail, timeout, or return invalid outputs; all failures recorded with reason. | `invalid_output` path (D-13) and adapter failure path (D-03) both produce REVIEW with failure_reason. |
| VLM-05 | System defaults to using installed model-zoo Qwen3-VL models (qwen3-vl-2b, qwen3-vl-4b, qwen3-vl-8b). ⚠️ The external OpenAI-compatible adapter portion of this requirement is **deferred** per CONTEXT.md D-01. | Model zoo names verified: `qwen3-vl-2b-instruct-torch`, `qwen3-vl-4b-instruct-torch`, `qwen3-vl-8b-instruct-torch`. FiftyOne 1.17 confirmed installed with these models available. |

</phase_requirements>

---

## Summary

Phase 7 adds an **optional VLM stage** on top of Phase 6's deterministic pipeline. Objects that received a deterministic `PASS` verdict and whose label is configured for VLM evaluation are passed through a per-rule VLM evaluation loop that calls a FiftyOne model-zoo Qwen3-VL model with a crop image and a rule-specific prompt. Each call returns a JSON blob with `error_probability`; the maximum across all rules becomes the object's risk score, which maps to PASS/REVIEW/FAIL based on configurable thresholds. Three new artifacts are written to the existing run directory alongside the Phase 6 deterministic artifacts.

The implementation maps cleanly to five new modules (`vlm_config.py`, `vlm_types.py`, `vlm_client.py`, `vlm_engine.py`, `report_vlm.py`) that each mirror the structure of their Phase 6 counterparts. The VLM stage hooks into `run_verify.py` after the deterministic loop, using the `vlm_eligible` flag already set on each `ObjectVerificationResult`.

FiftyOne 1.17 ships `qwen3_vl.Qwen3VLModel` (see `fiftyone.utils.qwen3_vl`). For VLM rule evaluation we need **raw text output** rather than the default `Detections` output. The correct approach is to load the model via `foz.load_zoo_model(model_name)`, set `model.config.prompt = custom_prompt`, then call `model._generate_detections([pil_image])` directly — this bypasses the detection output processor and returns the raw model text string, which is then parsed as JSON. The mock adapter for CI uses the same duck-type interface without loading any real model.

**⚠️ CONFLICT — PLANNER MUST RESOLVE:** CONTEXT.md D-01 locks out any external HTTP adapter, but VLM-05 (REQUIREMENTS.md) and ROADMAP.md Phase 7 success criteria #3 both explicitly require configurable external OpenAI-compatible adapter endpoint support for Qwen2.5-VL-7B-Instruct. This research covers only the model-zoo path per D-01. If the external adapter portion of VLM-05 must be satisfied, it requires reopening D-01 with the user.

**Primary recommendation:** Implement `vlm_client.py` as a Protocol + FiftyOneZooAdapter + MockAdapter; load the zoo model lazily; call `_generate_detections` for raw text; parse JSON per-rule; aggregate via `max()`; emit three VLM artifacts to the existing run directory.

---

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| VLM adapter / model loading | Python process (local) | — | FiftyOne zoo models run in-process via PyTorch; no server tier |
| Config parsing (VLM scope/templates) | Application layer | — | Mirrors existing `verification/config.py` pattern; same YAML config file |
| Crop loading | Filesystem | Application layer | Crop PNGs already materialized by Phase 6 cropper; loaded via PIL |
| Rule execution + prompt building | Application layer | — | `vlm_engine.py` iterates per rule, constructs prompt, calls adapter |
| Response parsing + invalid_output handling | Application layer | — | `vlm_engine.py` JSON parse with validation; marks REVIEW on failure |
| Risk aggregation | Application layer | — | Simple `max()` in engine; threshold lookup from VlmConfig |
| Report writing (CSV/JSON/NDJSON) | Filesystem | Application layer | Mirrors `report_csv.py`/`report_json.py`/`report_ndjson.py` from Phase 6 |
| Review queue ordering | Application layer | — | Computed in `report_vlm.py` from VlmObjectResult list |
| CLI wiring | CLI (cli.py) | — | No CLI changes required per CONTEXT.md; `vlm.enabled` flag already present |

---

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| `fiftyone` | 1.17.0 (installed) | Zoo model loading + inference via `fiftyone.utils.qwen3_vl.Qwen3VLModel` | Already installed; ships the Qwen3-VL wrapper |
| `Pillow` (PIL) | (transitive) | Load crop PNGs → `PILImage` for model input | Already used in `materialize_crop`; `_prepare_image` accepts PIL directly |
| `PyYAML` | ≥6.0 (installed) | VLM config loading | Already used throughout |
| `json` (stdlib) | — | Parse VLM JSON responses | No external dep needed |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `transformers` | ≥4.57.0 | HuggingFace model execution (transitive via fiftyone) | Auto-installed as zoo model requirement; do NOT import directly in vlm_client.py |
| `torch` | (transitive) | GPU/CPU tensor ops | Loaded by FiftyOne zoo model; do NOT import directly |
| `qwen-vl-utils` | ≥0.0.1 | Image preprocessing for Qwen3-VL (transitive) | Zoo model requirement; auto-installed |
| `accelerate` | (transitive) | Device mapping for large models | Zoo model requirement; auto-installed |

[VERIFIED: fiftyone.utils.qwen3_vl source inspected live] — all transitive requirements confirmed in `Qwen3VLModel` requirements block.

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| `foz.load_zoo_model` + `_generate_detections` | Direct HuggingFace `transformers` API | Direct HF avoids the internal `_generate_detections` call but duplicates all model loading, device handling, and processor logic already in `Qwen3VLModel`. Zoo wrapper is simpler. |
| `model._generate_detections([img])` | `model.predict(img)` then re-parse | `predict()` routes through `Qwen3VLOutputProcessor` which returns `Detections`, not raw text. `_generate_detections` returns the raw string list before output processing. |
| Per-rule adapter call | Batch multiple rules in one prompt | Single combined prompt reduces calls but makes per-rule `error_probability` extraction ambiguous and harder to validate. One call per rule is cleaner. |

---

## Package Legitimacy Audit

No new packages are added by Phase 7. All required libraries (`fiftyone`, `Pillow`, `PyYAML`) are already installed and have been verified in previous phases.

| Package | Registry | Status |
|---------|----------|--------|
| `fiftyone` | PyPI | Already installed (v1.17.0) — verified in prior phases |
| `Pillow` | PyPI | Already installed — verified in prior phases |
| `PyYAML` | PyPI | Already installed — verified in prior phases |

**No new packages to install.**

---

## Architecture Patterns

### System Architecture Diagram

```
                         ┌──────────────────────────────┐
                         │        run_verify.py         │
                         │                              │
  config.yaml ──────────▶│  load_verification_config()  │
  datumaro.json ─────────▶│  deterministic loop          │
                         │  → ObjectVerificationResult  │
                         │    verdict = PASS/FAIL        │
                         │    vlm_eligible = True/False  │
                         └──────────┬───────────────────┘
                                    │  PASS results + vlm_enabled
                                    ▼
                         ┌──────────────────────────────┐
                         │  VLM Stage (run_verify.py)   │
                         │                              │
  config.yaml ──────────▶│  load_vlm_config()           │
                         │  filter: vlm_eligible=True   │
                         │       + label in vlm scope   │
                         │                              │
                         │  for each eligible object:   │
                         │    pil_img = PIL.open(crop)  │
                         │    evaluate_vlm_object()     │◀── vlm_engine.py
                         │                              │
                         │    → VlmObjectResult         │
                         └──────────┬───────────────────┘
                                    │  list[VlmObjectResult]
                                    ▼
                         ┌──────────────────────────────┐
                         │      report_vlm.py           │
                         │  vlm_report.csv              │
                         │  vlm_report.json             │   (same run_dir
                         │    + review_queue            │    as Phase 6
                         │  vlm_trace.ndjson            │    artifacts)
                         └──────────────────────────────┘

  vlm_engine.py:
    for each rule in label_config.rules:
      prompt = build_prompt(template, label, rule, annotation_fields)
      raw_text = adapter.generate_text(pil_img, prompt)  ◀── vlm_client.py
      result = parse_vlm_response(raw_text)              ─▶  VlmRuleResult
      if invalid → REVIEW + failure_reason
    object_risk = max(r.error_probability for r in valid_results)
    vlm_status = threshold_lookup(object_risk, thresholds)

  vlm_client.py adapters:
    FiftyOneZooAdapter.generate_text(pil_img, prompt) → str
      model.config.prompt = prompt
      return model._generate_detections([pil_img])[0]
    MockVlmAdapter.generate_text(pil_img, prompt) → str
      return self._responses[rule_key]  # deterministic JSON
```

### Recommended Project Structure

```
src/fiftyone_pose_importer/verification/
├── vlm_types.py          # VlmVerdict, VlmRuleResult, VlmObjectResult dataclasses
├── vlm_config.py         # VlmConfig, load_vlm_config() — mirrors config.py
├── vlm_client.py         # VlmAdapter Protocol + FiftyOneZooAdapter + MockVlmAdapter
├── vlm_engine.py         # evaluate_vlm_object(), build_prompt(), parse_vlm_response()
└── report_vlm.py         # write_vlm_reports() → csv + json(+review_queue) + ndjson

tests/phase7/
├── test_vlm_config.py    # config loading, defaults, per-label overrides, thresholds
├── test_vlm_engine.py    # rule execution, invalid_output, risk aggregation, gating
├── test_vlm_client.py    # FiftyOneZooAdapter (mock model), MockVlmAdapter
├── test_report_vlm.py    # CSV/JSON/NDJSON shape, review_queue ordering
└── test_run_verify_vlm.py  # integration: full pipeline with vlm.enabled=true
```

### Pattern 1: VLM Adapter Protocol (duck-type for CI mock)

**What:** Define a `VlmAdapter` Protocol that both `FiftyOneZooAdapter` and `MockVlmAdapter` implement. The engine depends only on the protocol — no fiftyone import needed in vlm_engine.py.

**When to use:** Every time the engine calls the model. The mock is injected in tests; the real adapter is used in production.

```python
# Source: project-level pattern; mirrors existing engine/config duck-typing style
from __future__ import annotations
from typing import Protocol
from PIL import Image as PILImage


class VlmAdapter(Protocol):
    """Duck-type interface for VLM text generation — real or mock."""
    def generate_text(self, image: PILImage.Image, prompt: str) -> str: ...


class FiftyOneZooAdapter:
    """Thin wrapper around FiftyOne zoo Qwen3-VL model for raw text generation."""

    def __init__(self, model_name: str, max_new_tokens: int = 256) -> None:
        self._model_name = model_name
        self._max_new_tokens = max_new_tokens
        self._model = None  # lazy-loaded on first call

    def generate_text(self, image: PILImage.Image, prompt: str) -> str:
        if self._model is None:
            import fiftyone.zoo as foz
            # cache=True (default) means repeated calls reuse same instance
            self._model = foz.load_zoo_model(
                self._model_name,
                max_new_tokens=self._max_new_tokens,
            )
        # Override the prompt for this specific rule call
        self._model.config.prompt = prompt
        # _generate_detections bypasses the detection output processor
        # and returns raw model text (list of strings, one per image)
        raw_texts: list[str] = self._model._generate_detections([image])
        return raw_texts[0]


class MockVlmAdapter:
    """Deterministic mock — returns pre-set JSON per rule key or a default."""

    def __init__(
        self,
        responses: dict[str, str] | None = None,
        default_response: str = '{"error_probability": 0.1, "reason": "mock-ok"}',
    ) -> None:
        self._responses: dict[str, str] = responses or {}
        self._default = default_response

    def generate_text(self, image: PILImage.Image, prompt: str) -> str:
        # Tests can key by prompt substring or rule name
        for key, resp in self._responses.items():
            if key in prompt:
                return resp
        return self._default
```

### Pattern 2: VLM Response Parsing with `invalid_output` Guard

**What:** Parse the raw text string from the model, strip markdown fences if present (Qwen3-VL wraps in ` ```json ``` `), validate the schema, return a `VlmRuleResult`.

**When to use:** After every `adapter.generate_text()` call. Never trust the response without validation.

```python
# Source: fiftyone.utils.qwen3_vl.Qwen3VLOutputProcessor shows markdown fence stripping pattern
import json
import re

_FENCE_RE = re.compile(r"```(?:json)?\s*([\s\S]*?)```", re.DOTALL)


def parse_vlm_response(raw: str, rule_name: str) -> VlmRuleResult:
    """Parse model text into VlmRuleResult. Returns invalid_output on any failure."""
    stripped = raw.strip()
    # Strip markdown code fences (Qwen3-VL wraps output in ```json ... ```)
    fence_match = _FENCE_RE.search(stripped)
    if fence_match:
        stripped = fence_match.group(1).strip()

    try:
        parsed = json.loads(stripped)
    except (json.JSONDecodeError, ValueError):
        return VlmRuleResult(
            rule_name=rule_name,
            error_probability=None,
            reason="invalid_output: JSON parse failed",
            evidence=None,
            invalid_output=True,
        )

    ep = parsed.get("error_probability")
    if not isinstance(ep, (int, float)) or not (0.0 <= float(ep) <= 1.0):
        return VlmRuleResult(
            rule_name=rule_name,
            error_probability=None,
            reason=f"invalid_output: error_probability={ep!r}",
            evidence=None,
            invalid_output=True,
        )

    return VlmRuleResult(
        rule_name=rule_name,
        error_probability=float(ep),
        reason=str(parsed.get("reason", "")),
        evidence=parsed.get("evidence"),
        invalid_output=False,
    )
```

### Pattern 3: VLM Config Loading (mirrors `config.py` exactly)

**What:** Load VLM scope, per-label rule lists, prompt templates, and thresholds from the existing YAML config. Follows the global-defaults + per-label-override pattern of Phase 6.

**Config shape:**
```yaml
verification:
  vlm:
    enabled: true
    model_name: qwen3-vl-2b-instruct-torch  # or 4b, 8b
    thresholds:             # global defaults (D-16)
      pass_below: 0.20
      review_below: 0.60   # > 0.60 → FAIL
    generation:
      max_new_tokens: 256
    default_prompt_template: |
      You are an annotation quality checker. Crop shows a {label} object.
      Evaluate rule '{rule}': {rule_description}
      Annotation fields: {annotation_fields_json}
      Return ONLY strict JSON: {"error_probability": <float 0-1>, "reason": "<text>"}
    labels:
      forklift-with-roll:
        enabled: true
        rules:
          - bbox_localization
          - bbox_coverage
          - clamp_type
          - roll_count
        thresholds:           # optional per-label threshold override (D-17)
          pass_below: 0.25
          review_below: 0.65
        prompts:              # optional per-label per-rule template overrides (D-10)
          bbox_coverage: |
            Does the bounding box cover forklift + clamp + all clamped rolls?
            BBox (x,y,w,h): {bbox}. Return JSON.
      forklift-no-roll:
        enabled: true
        rules:
          - bbox_localization
          - bbox_coverage
          - clamp_type
```

### Pattern 4: Integration Point in `run_verify.py`

**What:** After the deterministic loop and before `write_run_reports`, collect VLM-eligible results and run the VLM stage.

**When to use:** Only when `vlm_enabled=True` and `vlm_config` has at least one enabled label.

```python
# After deterministic loop in run_verify.py — integration point (D-08, D-09)
from .verification.vlm_config import load_vlm_config
from .verification.vlm_engine import evaluate_vlm_object
from .verification.vlm_client import FiftyOneZooAdapter
from .verification.report_vlm import write_vlm_reports
from .verification.types import DeterministicVerdict

vlm_results: list[VlmObjectResult] = []
if vlm_enabled:
    vlm_config_raw = (verification_root.get("vlm") or {})
    vlm_config, vlm_warnings = load_vlm_config(vlm_config_raw)
    warnings.extend(vlm_warnings)

    adapter = FiftyOneZooAdapter(
        model_name=vlm_config.model_name,
        max_new_tokens=vlm_config.generation.max_new_tokens,
    )

    for result in results:
        if result.verdict is not DeterministicVerdict.PASS:
            continue  # D-08: deterministic FAILs skip VLM
        if not vlm_config.is_label_enabled(result.label):
            continue  # D-05: label not in VLM scope → skip

        from PIL import Image as PILImage
        try:
            crop_img = PILImage.open(result.crop_path).convert("RGB")
        except Exception as exc:
            vlm_results.append(_vlm_failure_result(result, f"crop_load_error:{type(exc).__name__}"))
            continue

        vlm_outcome = evaluate_vlm_object(
            result=result,
            crop_image=crop_img,
            adapter=adapter,
            vlm_config=vlm_config,
        )
        vlm_results.append(vlm_outcome)

    write_vlm_reports(vlm_results, run_root=run_root, run_timestamp=safe_timestamp)
```

### Pattern 5: VLM Types (parallel to `types.py`)

```python
# src/fiftyone_pose_importer/verification/vlm_types.py
from __future__ import annotations
from dataclasses import dataclass
from enum import Enum


class VlmVerdict(str, Enum):
    PASS = "PASS"
    REVIEW = "REVIEW"
    FAIL = "FAIL"


@dataclass(frozen=True)
class VlmRuleResult:
    rule_name: str
    error_probability: float | None   # None when invalid_output
    reason: str
    evidence: str | None
    invalid_output: bool


@dataclass(frozen=True)
class VlmObjectResult:
    sample_id: str
    object_id: str
    label: str
    vlm_status: VlmVerdict
    object_risk: float | None       # None when all rules invalid / adapter fail
    rule_results: list[VlmRuleResult]
    adapter_model: str
    failure_reason: str | None      # set when adapter fail or all-invalid
    crop_path: str
```

### Pattern 6: Review Queue Ordering (D-21)

```python
# In report_vlm.py — review_queue sort key
# Sort: risk desc → adapter_failure first → sample_id asc → object_id asc
def _review_queue_key(r: VlmObjectResult) -> tuple:
    risk = -(r.object_risk or 0.0)                        # desc
    is_adapter_fail = 0 if r.failure_reason else 1        # failure first
    return (risk, is_adapter_fail, r.sample_id, r.object_id)
```

### Anti-Patterns to Avoid

- **Importing `torch` or `transformers` directly in `vlm_client.py`:** Import only `fiftyone.zoo`; let the zoo model's lazy import mechanism handle ML dependencies. This keeps the module importable without GPU packages present.
- **Calling `model.predict(img)` for raw text:** `predict()` routes through `Qwen3VLOutputProcessor` which returns `fiftyone.core.labels.Detections`, not a string. Use `model._generate_detections([img])` instead.
- **Calling `foz.load_zoo_model` on every rule evaluation:** Load once per run (lazy on first call) and reuse. Zoo model loading downloads weights from HuggingFace on first use.
- **Parsing VLM responses without stripping markdown fences:** Qwen3-VL models wrap JSON responses in ` ```json ... ``` ` code blocks. Always strip fences before `json.loads()`.
- **Mutating `ObjectVerificationResult` in the VLM stage:** Phase 6 deterministic results must not be modified. VLM outputs go into a separate `VlmObjectResult` type.
- **Failing the entire run when one object's VLM call fails:** Per D-03, individual model failures produce `REVIEW` for that object; the pipeline continues and completes normally.
- **Skipping the `invalid_output` check:** An `error_probability` of `0` (integer) is valid; `None`, a string, or a value outside `[0.0, 1.0]` are all `invalid_output` per D-13.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| VLM model loading and GPU device handling | Custom HuggingFace model loader | `foz.load_zoo_model()` | Handles dtype (bfloat16 vs float32), device_map, processor loading, model caching — 50+ lines of correct handling already done |
| Image preprocessing for Qwen3-VL | Manual tensor construction | `model._generate_detections([pil_image])` | Uses `_prepare_image` and `apply_chat_template` correctly — wrong preprocessing produces garbage output |
| Markdown fence stripping | `re.split` variants | The `_FENCE_RE` pattern shown in §Pattern 2 (derived from `Qwen3VLOutputProcessor`) | FiftyOne's own output processor shows the canonical fence-strip approach |
| Report writing boilerplate | Custom CSV/JSON writers | Extend `report_csv.py` / `report_json.py` patterns | Phase 6 report writers already handle path safety, `_sanitize_csv_cell`, sorted output — reuse the pattern exactly |
| Timestamped run dir management | New path logic | Reuse `_safe_run_dir` and `_safe_run_timestamp` from `report_csv.py` | VLM artifacts go to the **same** run_dir as deterministic artifacts |

**Key insight:** The FiftyOne qwen3_vl module already handles all VLM inference complexity. The vlm_client.py is a ~40-line thin wrapper; the heavy lifting is done by the installed library.

---

## Rule Prompt Mapping

Each VLM rule receives the crop image + a constructed prompt. The relevant annotation fields per rule (D-11):

| Rule | Annotation Fields Used | What VLM Evaluates |
|------|----------------------|-------------------|
| `bbox_localization` | `bbox [x, y, w, h]`, `label` | Is the box correctly attached to the right object? |
| `bbox_coverage` | `bbox [x, y, w, h]`, `label`, `attributes.clamp_type` (if present) | Does the box cover the class-specific required region? |
| `clamp_type` | `attributes.clamp_type`, `label` | Does the visible clamp match the annotated type (2-arm / 3-arm)? |
| `roll_count` | `attributes.roll_count`, `label` | Does visible roll count match annotated count? |
| `keypoint_position` | `keypoints [[x,y]...]`, `visibility [0/1/2...]`, `label` | Are keypoints at correct semantic locations? |
| `occlusion_state` | `keypoints [[x,y]...]`, `visibility [0/1/2...]`, `label` | Does each keypoint's visibility code match image reality? |

The **global default prompt template** should be parameterized with `{label}`, `{rule}`, `{annotation_fields_json}` and explicitly instruct the model to return only the JSON schema — no prose, no markdown (this reduces fence-stripping failures). Per D-14, generation should use `do_sample=False` (already the default in `_generate_detections`).

---

## Common Pitfalls

### Pitfall 1: Qwen3-VL returns JSON wrapped in markdown fences
**What goes wrong:** `json.loads(raw_text)` raises `JSONDecodeError` even though the response is valid JSON, because the model emits ` ```json\n{...}\n``` `.
**Why it happens:** The model is trained to format code blocks. `Qwen3VLOutputProcessor._parse_detections` already handles this pattern.
**How to avoid:** Always apply `_FENCE_RE.search` before `json.loads`. See §Pattern 2.
**Warning signs:** `JSONDecodeError` on the first few model responses; text starts with ` ``` `.

### Pitfall 2: `model.predict()` returns `Detections`, not a string
**What goes wrong:** `vlm_client.py` calls `model.predict(img)` and gets a `fiftyone.core.labels.Detections` object — can't parse that as JSON.
**Why it happens:** `predict()` → `_predict_all()` → `_forward_pass()` → `_generate_detections()` → **then** `_output_processor(raw_texts, ...)`. The output processor converts strings to `Detections`.
**How to avoid:** Call `model._generate_detections([img])` directly to get `list[str]` before output processing.
**Warning signs:** `AttributeError: 'Detections' object has no attribute 'strip'`.

### Pitfall 3: FiftyOne zoo model downloads weights on first call
**What goes wrong:** The first `foz.load_zoo_model("qwen3-vl-2b-instruct-torch")` triggers a HuggingFace download (~2-8 GB depending on model). In CI without `--skip-download` or pre-cached weights, this hangs indefinitely.
**Why it happens:** `download_if_necessary=True` is the default in `load_zoo_model`.
**How to avoid:** (a) Use `MockVlmAdapter` in all CI tests per D-22. (b) For manual testing with real model, ensure weights are cached first. Never call `foz.load_zoo_model` in unit tests without a mock.
**Warning signs:** Tests hang for minutes with no output.

### Pitfall 4: `error_probability=0` (integer) parsed as `invalid_output`
**What goes wrong:** The model returns `{"error_probability": 0, "reason": "ok"}`. Code checks `if not ep:` → treats 0 as falsy → marks invalid_output.
**Why it happens:** Python falsy check for zero.
**How to avoid:** Validate `isinstance(ep, (int, float)) and 0.0 <= float(ep) <= 1.0`. See §Pattern 2.
**Warning signs:** Objects with low error probability unexpectedly marked REVIEW.

### Pitfall 5: `model.config.prompt` mutation is not thread-safe
**What goes wrong:** If two threads share a `FiftyOneZooAdapter` instance, concurrent `config.prompt` mutations produce wrong prompts being evaluated for the wrong rules.
**Why it happens:** `config.prompt` is a simple mutable attribute.
**How to avoid:** The Phase 7 pipeline runs sequentially (one object at a time); no threading. Document that the adapter is not thread-safe and must not be shared across threads.
**Warning signs:** Symptoms only appear if concurrent rule evaluation is introduced in a future refactor.

### Pitfall 6: VLM artifacts written to wrong directory
**What goes wrong:** VLM report files land in a different directory from Phase 6 deterministic artifacts, making triage tooling unable to find them.
**Why it happens:** Forgetting to pass the same `run_root` + `run_timestamp` to `write_vlm_reports`.
**How to avoid:** `write_vlm_reports` must receive the same `run_root` and `safe_timestamp` already computed in `run_verify.py` for deterministic artifacts. The `_safe_run_dir` function from `report_csv.py` is reused to produce the identical run directory path.
**Warning signs:** `vlm_report.csv` exists but not in the run directory listed in `summary["artifacts"]["run_dir"]`.

---

## Code Examples

### Loading and calling a zoo VLM for raw text (verified against live FiftyOne 1.17 source)

```python
# Source: fiftyone.utils.qwen3_vl.Qwen3VLModel._generate_detections (inspected live)
import fiftyone.zoo as foz
from PIL import Image as PILImage

# 1. Load model (lazy download on first use; cache=True keeps same instance)
model = foz.load_zoo_model("qwen3-vl-2b-instruct-torch", max_new_tokens=256)

# 2. Set the per-call prompt (config.prompt overrides DEFAULT_DETECTION_PROMPT)
model.config.prompt = (
    'You are an annotation quality checker. The image shows a forklift-with-roll crop.\n'
    'Evaluate rule "bbox_coverage": does the bounding box cover forklift + clamp + all clamped rolls?\n'
    'Annotation: {"bbox": [10, 20, 80, 60], "attributes": {"clamp_type": "2-arm"}}\n'
    'Return ONLY: {"error_probability": <float 0.0-1.0>, "reason": "<text>"}'
)

# 3. Load crop as PIL image (crop already materialized by Phase 6 cropper)
pil_img = PILImage.open("/path/to/crop.png").convert("RGB")

# 4. Get raw text — bypasses Qwen3VLOutputProcessor (which would produce Detections)
raw_texts: list[str] = model._generate_detections([pil_img])
raw_text: str = raw_texts[0]
# raw_text may be: '{"error_probability": 0.15, "reason": "box coverage looks correct"}'
# or wrapped:      '```json\n{"error_probability": 0.15, ...}\n```'
```

### Zoo model names (verified against installed FiftyOne 1.17)

```python
# Source: fiftyone.zoo.list_zoo_models() — executed live
VALID_ZOO_MODEL_NAMES = [
    "qwen3-vl-2b-instruct-torch",   # 2B param, fastest
    "qwen3-vl-4b-instruct-torch",   # 4B param, balanced
    "qwen3-vl-8b-instruct-torch",   # 8B param, most accurate
]
# NOT in zoo (requires external adapter if needed): qwen2.5-vl-7b-instruct
```

### Model requirements (verified from zoo model info)

```python
# Source: foz.get_zoo_model("qwen3-vl-2b-instruct-torch").requirements — executed live
# Required: torch, torchvision, transformers>=4.51.0, accelerate, qwen-vl-utils
# CPU support: True
# GPU support: True
# HuggingFace name: "Qwen/Qwen3-VL-2B-Instruct"
```

---

## FiftyOne Zoo VLM Inference — Key API Facts

[VERIFIED: fiftyone.utils.qwen3_vl source inspected live]

1. **Model class:** `fiftyone.utils.qwen3_vl.Qwen3VLModel` — loaded via `foz.load_zoo_model(name)`
2. **Zoo model names:** `qwen3-vl-2b-instruct-torch`, `qwen3-vl-4b-instruct-torch`, `qwen3-vl-8b-instruct-torch`
3. **Prompt override:** Set `model.config.prompt = "..."` before each `_generate_detections` call
4. **Raw text extraction:** `list[str] = model._generate_detections([pil_image])` — returns text before output processing
5. **Image input:** PIL `Image` (RGB), numpy array (HWC), or torch tensor (CHW) — PIL is simplest since crops are already saved as PNG files
6. **Response format:** Plain JSON or JSON wrapped in ` ```json ``` ` markdown fences
7. **Deterministic generation:** `do_sample=False` is already the default (`_generate_detections` uses `generate(..., do_sample=False)`)
8. **Model caching:** `foz.load_zoo_model(..., cache=True)` (default) returns same instance on repeat calls — safe to call multiple times
9. **Lazy import:** `fiftyone.utils.qwen3_vl` is available but `transformers`/`torch` are imported only when the model is loaded — import of `foz` module itself is always safe

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Qwen2-VL (external only) | Qwen3-VL in FiftyOne 1.17 zoo | FiftyOne 1.17 | qwen3-vl-{2b,4b,8b} available locally; no external server needed for default path |
| FiftyOne `apply_model` for VLM | Direct `_generate_detections` for raw text | — | `apply_model` targets `Detections` output; rule evaluation needs raw JSON text |

**Deprecated/outdated:**
- `qwen2.5-vl-7b-instruct` in zoo: Not in FiftyOne 1.17 zoo (verified via `foz.list_zoo_models()`). Requires external adapter if needed — deferred per D-01.

---

## Runtime State Inventory

> Not applicable — Phase 7 is a greenfield feature addition, not a rename/refactor/migration.

None required.

---

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Python | All | ✓ | (project requirement) | — |
| `fiftyone` | Zoo model loading, zoo model listing | ✓ | 1.17.0 | — |
| `qwen3-vl-2b-instruct-torch` (zoo model, weights) | Real inference | ⚠️ Download required | — | Use MockVlmAdapter for CI (D-22) |
| `torch` / `transformers` / `qwen-vl-utils` | Zoo model execution | ⚠️ Auto-installed by zoo | — | Auto-installed on first `foz.load_zoo_model`; MockVlmAdapter avoids this in CI |
| `Pillow` | Crop loading | ✓ | (transitive, used by Phase 6) | — |
| GPU (CUDA/MPS) | Fast inference | ⚠️ Unknown | — | Model supports CPU (slower); `supports_cpu: true` confirmed in zoo model requirements |

**Missing dependencies with no fallback:** None that block CI (MockVlmAdapter satisfies D-22).

**Missing dependencies with fallback:** Real qwen3-vl model weights — MockVlmAdapter used in CI per D-22.

---

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest (existing) |
| Config file | `tests/conftest.py` (adds `src/` to `sys.path`) |
| Quick run command | `pytest tests/phase7/ -x -q` |
| Full suite command | `pytest tests/ -q` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| VLM-01 | `load_vlm_config` returns correct per-label enabled flags | unit | `pytest tests/phase7/test_vlm_config.py -x` | ❌ Wave 0 |
| VLM-01 | Labels not in VLM scope produce no VlmObjectResult | unit | `pytest tests/phase7/test_vlm_engine.py::test_non_vlm_label_skipped -x` | ❌ Wave 0 |
| VLM-02 | Per-label per-rule prompt templates override global default | unit | `pytest tests/phase7/test_vlm_engine.py::test_prompt_template_override -x` | ❌ Wave 0 |
| VLM-02 | Annotation fields injected into prompt correctly | unit | `pytest tests/phase7/test_vlm_engine.py::test_prompt_annotation_fields -x` | ❌ Wave 0 |
| VLM-03 | object_risk = max(error_probabilities) | unit | `pytest tests/phase7/test_vlm_engine.py::test_risk_aggregation_is_max -x` | ❌ Wave 0 |
| VLM-03 | Deterministic FAIL objects skip VLM stage entirely | unit | `pytest tests/phase7/test_vlm_engine.py::test_deterministic_fail_skips_vlm -x` | ❌ Wave 0 |
| VLM-03 | Full integration: vlm.enabled=true with mock adapter produces vlm artifacts | integration | `pytest tests/phase7/test_run_verify_vlm.py -x` | ❌ Wave 0 |
| VLM-04 | invalid_output response → REVIEW with reason | unit | `pytest tests/phase7/test_vlm_engine.py::test_invalid_output_review -x` | ❌ Wave 0 |
| VLM-04 | Adapter exception → REVIEW with failure_reason | unit | `pytest tests/phase7/test_vlm_engine.py::test_adapter_failure_review -x` | ❌ Wave 0 |
| VLM-04 | error_probability=0 (integer) is valid, not invalid_output | unit | `pytest tests/phase7/test_vlm_engine.py::test_zero_probability_valid -x` | ❌ Wave 0 |
| VLM-05 | model_name from config is passed to FiftyOneZooAdapter | unit | `pytest tests/phase7/test_vlm_client.py::test_model_name_forwarded -x` | ❌ Wave 0 |
| D-19 | vlm_report.csv, vlm_report.json, vlm_trace.ndjson written to same run_dir | unit | `pytest tests/phase7/test_report_vlm.py::test_vlm_artifacts_in_run_dir -x` | ❌ Wave 0 |
| D-21 | review_queue sorted: risk desc → adapter_failure first → sample_id/object_id asc | unit | `pytest tests/phase7/test_report_vlm.py::test_review_queue_ordering -x` | ❌ Wave 0 |

### Sampling Rate
- **Per task commit:** `pytest tests/phase7/ -x -q`
- **Per wave merge:** `pytest tests/ -q`
- **Phase gate:** Full suite green before `/gsd-verify-work`

### Wave 0 Gaps
- [ ] `tests/phase7/__init__.py` — package init
- [ ] `tests/phase7/test_vlm_config.py` — VLM config loading tests
- [ ] `tests/phase7/test_vlm_engine.py` — engine tests (rule execution, aggregation, invalid_output, gating)
- [ ] `tests/phase7/test_vlm_client.py` — adapter tests (MockVlmAdapter behavior, FiftyOneZooAdapter interface shape)
- [ ] `tests/phase7/test_report_vlm.py` — CSV/JSON/NDJSON shape + review_queue ordering
- [ ] `tests/phase7/test_run_verify_vlm.py` — full integration test with mock adapter

---

## Security Domain

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V5 Input Validation | yes | Parse VLM responses with strict JSON schema validation; reject any `error_probability` not in `[0.0, 1.0]` |
| V2 Authentication | no | Local workflow, no auth required |
| V4 Access Control | yes (minimal) | Crop file paths validated to remain within `run_dir` — same `_safe_run_dir` guard as Phase 6 |
| V6 Cryptography | no | No secrets involved |

**Path traversal guard:** Crop paths are already constrained by Phase 6's `_crop_output_path` (relative to `run_dir`). Phase 7 only opens paths that were produced by Phase 6 — no user-controlled path input.

---

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | `model._generate_detections([pil_img])` is stable API across FiftyOne 1.17.x patch releases | FiftyOne Zoo VLM Inference, Standard Stack | Method is prefixed with `_` (internal); could be renamed in future FiftyOne versions. Risk: LOW for 1.17 patch line; revisit on major version upgrade. |
| A2 | VLM-05's external adapter requirement is fully satisfied by implementing only the model-zoo path (treating external adapter as deferred per D-01) | Phase Requirements (VLM-05) | If product review requires external adapter for VLM-05 sign-off, D-01 must be reopened. Flag to planner. |

---

## Open Questions

1. **VLM-05 vs D-01 conflict (PLANNER MUST RESOLVE)**
   - What we know: CONTEXT.md D-01 locks out external HTTP adapter. VLM-05 in REQUIREMENTS.md and ROADMAP.md Phase 7 success criteria #3 both explicitly require a configurable external OpenAI-compatible adapter endpoint.
   - What's unclear: Whether VLM-05 is considered satisfied by implementing only the model-zoo path (treating external adapter as deferred), or whether VLM-05 requires the external adapter to be implemented.
   - Recommendation: Planner should implement D-01 (model-zoo only) and mark VLM-05 as "partially satisfied — model-zoo default path delivered; external adapter deferred per CONTEXT.md D-01." Flag to the user that the external adapter requirement is explicitly deferred.

2. **Whether to add an `--adapter` CLI flag**
   - What we know: CONTEXT.md says no CLI changes needed unless `--vlm-only` mode is desired. The external adapter is deferred.
   - What's unclear: Whether the model_name should be CLI-overrideable (in addition to config).
   - Recommendation: Keep model_name config-only for Phase 7. No CLI changes needed.

---

## Sources

### Primary (HIGH confidence)
- `fiftyone.utils.qwen3_vl` (inspected live via `inspect.getsource`) — Qwen3VLModel class, `_generate_detections`, `_prepare_image`, fence-stripping pattern
- `fiftyone.zoo.list_zoo_models()` (executed live) — confirmed model names `qwen3-vl-2b-instruct-torch`, `qwen3-vl-4b-instruct-torch`, `qwen3-vl-8b-instruct-torch`
- `foz.get_zoo_model("qwen3-vl-2b-instruct-torch")` (executed live) — confirmed HuggingFace name `Qwen/Qwen3-VL-2B-Instruct`, requirements, `default_deployment_config_dict`
- `fiftyone.utils.torch.TorchImageModel._predict_all` (inspected live) — confirmed `predict()` routes through `_output_processor`

### Secondary (matches locked CONTEXT.md decisions)
- `.planning/phases/07-vlm-verification-aggregation/07-CONTEXT.md` — all locked decisions D-01 through D-22
- `src/fiftyone_pose_importer/run_verify.py` — integration point, `vlm_eligible` flag, `write_run_reports` pattern
- `src/fiftyone_pose_importer/verification/config.py` — global defaults + per-label override pattern to replicate
- `src/fiftyone_pose_importer/verification/engine.py` — engine structure pattern
- `src/fiftyone_pose_importer/verification/report_csv.py` — `_safe_run_dir`, report writers pattern

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — verified against installed FiftyOne 1.17.0 source
- Architecture: HIGH — derived from existing Phase 6 patterns + verified FiftyOne API
- Pitfalls: HIGH — verified from live FiftyOne source (fence pattern, predict vs _generate_detections)
- VLM-05 external adapter: N/A — deferred per D-01

**Research date:** 2026-06-13
**Valid until:** 2026-09-13 (FiftyOne 1.17.x stable; revisit on FiftyOne major version bump)
