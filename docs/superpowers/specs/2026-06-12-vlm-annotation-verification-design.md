# VLM Annotation Verification Design (Qwen2.5-7B-Instruct)

## Goal

Build a per-annotation quality gate that validates cropped annotations against class-specific rules, using deterministic checks first and Qwen2.5-7B-Instruct only where configured and needed.

## Scope

- Input: FiftyOne samples and annotation crops
- Rules: YAML/JSON class-level rule definitions
- Decision output per annotation: `PASS`, `FAIL`, or `REVIEW`
- Reports: detailed CSV + aggregate JSON summary

Out of scope:

- Auto-editing annotations
- Full dashboard UI (first version is file-based reporting)

## Why Qwen2.5-7B-Instruct is suitable

For small batches (<1000 per run), Qwen2.5-7B-Instruct is suitable as a fallback verifier for ambiguous visual checks. It is not the primary judge. Deterministic rules remain the source of truth for hard constraints and auditability.

## Architecture

1. **Input Loader**
   - Reads dataset samples and target annotations
   - Produces crops + metadata (`sample_id`, `annotation_id`, `class`, geometry, optional context)
   - Cropping is mandatory before VLM checks for enabled classes

2. **Rule Spec Parser**
   - Loads and validates YAML/JSON config
   - Normalizes into:
     - `hard_checks` (must pass)
     - `soft_checks` (quality indicators)
     - `vlm_checks` (visual checks routed to VLM)
   - Supports class-level VLM policy:
     - `vlm_enabled: true|false`
     - `vlm_policy: never | ambiguous_only | always`

3. **Deterministic Validator**
   - Runs all deterministic checks per annotation
   - Emits structured evidence: `rule_id`, observed values, threshold, pass/fail, severity

4. **Ambiguity Router**
   - Routes to VLM only when:
     - class has `vlm_enabled: true`
     - and policy allows (`ambiguous_only` or `always`)
     - and case is uncertain or policy is forced

5. **Qwen Verifier**
   - Uses constrained prompts tied to explicit rule IDs
   - Requires structured result: `PASS|FAIL|REVIEW`, reason code, confidence

6. **Decision Combiner**
   - `hard fail` => `FAIL`
   - deterministic pass and no VLM route => `PASS`
   - VLM conflict/low confidence/error => `REVIEW`

7. **Report Exporter**
   - CSV rows: one row per annotation with final decision and evidence
   - JSON summary: totals, per-class metrics, per-rule failures, review queue

## Data Flow

1. Select target annotations from FiftyOne
2. Create crops + metadata bundle
3. Run deterministic checks
4. Optionally run VLM checks (class-scoped policy)
5. Merge decisions
6. Write CSV and JSON report outputs

## Crop Logic (mandatory for VLM path)

Default policy: **tight bbox + fixed padding**.

1. Start from annotation bbox or polygon envelope
2. Expand by fixed padding ratio (default `0.15` on each side)
3. Clamp crop bounds to image size
4. Enforce minimum crop size (default `32x32`) by symmetric expansion where possible
5. Export crop and include crop metadata (`crop_x`, `crop_y`, `crop_w`, `crop_h`, `padding_ratio`) for traceability

If crop cannot be produced (invalid geometry or unreadable image), mark annotation `REVIEW` with `io_error`.

## Error Handling

- Invalid rule spec => fail-fast before processing
- Crop/read failures => mark annotation as `REVIEW` with `io_error`
- VLM timeout/format error => `REVIEW` with `vlm_error`
- Never silently convert uncertain results to `PASS`

## Testing Strategy

- Unit tests for rule parser and deterministic checks
- Prompt-output parser tests for strict schema handling
- Integration test with fixture dataset and expected CSV/JSON snapshots
- Regression test for class-scoped VLM policy (`vlm_enabled` and `vlm_policy`)

## Configuration Sketch

```yaml
defaults:
  crop:
    mode: tight_bbox_fixed_padding
    padding_ratio: 0.15
    min_w: 32
    min_h: 32

classes:
  person:
    vlm_enabled: true
    vlm_policy: ambiguous_only
    hard_checks:
      - rule_id: bbox_min_size
        min_w: 24
        min_h: 24
    vlm_checks:
      - rule_id: pose_is_human_like
        prompt_template: "Does this crop depict a valid human pose annotation?"

  traffic_sign:
    vlm_enabled: false
    vlm_policy: never
    hard_checks:
      - rule_id: bbox_aspect_range
        min_ratio: 0.6
        max_ratio: 1.6
```

## Success Criteria

- Deterministic checks run for all configured classes
- VLM runs only for explicitly enabled classes
- Every annotation has a deterministic/auditable trail in CSV
- JSON summary supports class-level triage and failure analysis
