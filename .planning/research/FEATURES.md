# Feature Landscape

**Domain:** Local annotation verification workflow (deterministic checks + optional VLM escalation)
**Researched:** 2026-06-12

## Table Stakes

Features users expect. Missing = workflow feels unreliable.

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| Per-skeleton-type field preservation in import output | Verification is meaningless if rendered skeleton structure is wrong | Medium | Must keep label→field mapping pattern in `src/main.py` |
| Configurable label targeting for verification | Teams verify only selected labels/classes in each run | Low | Include allowlist/denylist at config level |
| Deterministic rule checks (schema, geometry, visibility consistency) | Fast, repeatable baseline QA is mandatory | Medium | Rules should run without model/API dependency |
| Reusable crop generation from annotations | VLM or human triage needs standardized visual context | Medium | Consistent bbox expansion/padding policy |
| Unified verification result schema | Users need machine-readable PASS/FAIL + reason codes | Medium | Include sample id, label, rule id, severity |
| Report export (JSON + CSV summary) | Teams need triage and downstream automation | Low | JSON for full detail, CSV for quick review |

## Differentiators

Features that add clear value for v1.1 without blowing scope.

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| Optional VLM escalation only on flagged/ambiguous cases | Controls cost/latency while improving recall on hard cases | Medium | Keep deterministic checks as primary gate |
| Prompt templates configurable per label/rule-set | Reusable verification across skeleton types and projects | Medium | Variables: label, keypoint names, failure hints |
| Deterministic + VLM merged verdict with explicit provenance | Makes decisions auditable and easier to trust | Medium | Store `decision_source`: rule/vlm/hybrid |

## Anti-Features

Features to explicitly NOT build in this milestone.

| Anti-Feature | Why Avoid | What to Do Instead |
|--------------|-----------|-------------------|
| Run VLM on every annotation by default | Expensive, slow, and unnecessary for easy cases | Gate VLM behind deterministic failures/uncertainty |
| Auto-edit or auto-correct annotations | High risk; needs human-review UX and safety controls | Output actionable suggestions in report only |
| Full interactive QA web UI | Too large for single milestone | Export reports + use existing FiftyOne inspection flow |
| Multi-provider model orchestration/routing engine | Infrastructure-heavy and not required for v1.1 goal | Single configurable VLM backend interface |

## Feature Dependencies

```text
Per-skeleton-type field preservation
  -> Deterministic rule checks
    -> Optional VLM escalation
      -> Merged verdict schema
        -> JSON/CSV report export
```

## MVP Recommendation

Prioritize:
1. Per-skeleton-type field preservation + deterministic rule engine
2. Configurable label targeting + prompt/rule config schema
3. Optional VLM escalation on flagged cases + report export

Defer: Interactive review UI and auto-correction; they increase scope beyond a single milestone and are not required to ship reusable verification.

## Sources

- `.planning/PROJECT.md` (v1.1 milestone goals)
- `README.md` (current workflow constraints and troubleshooting expectations)
- `src/main.py` (current per-skeleton-type field rendering pattern)
