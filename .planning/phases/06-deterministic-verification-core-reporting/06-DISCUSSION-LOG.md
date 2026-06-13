# Phase 6: Deterministic Verification Core & Reporting - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-06-13
**Phase:** 6-deterministic-verification-core-reporting
**Areas discussed:** Deterministic verdict policy, Rule config shape per label/class, Crop policy and edge handling, Report schema and output files

---

## Deterministic verdict policy

| Option | Description | Selected |
|--------|-------------|----------|
| PASS/FAIL/REVIEW | Tri-state deterministic verdicts | |
| PASS/FAIL only | Binary deterministic verdicts | ✓ |

**User's choice:** PASS/FAIL only; no REVIEW in deterministic stage.
**Notes:** Rule evaluation failures/missing data should become explicit FAIL reasons; run still completes with zero exit code and report carries failures.

---

## Rule config shape per label/class

| Option | Description | Selected |
|--------|-------------|----------|
| Global defaults + per-label overrides | Shared baseline with class-specific tuning | ✓ |
| Per-label only | No global defaults | |
| Global only | One rule set for all labels/classes | |

**User's choice:** Global defaults + per-label overrides.
**Notes:** Labels inherit full global rule set when no override exists; all 4 rule categories enabled by default; unknown rule names should be ignored with warning.

---

## Crop policy and edge handling

| Option | Description | Selected |
|--------|-------------|----------|
| Fixed pixel padding | Deterministic crop expansion in pixels | ✓ |
| Relative ratio padding | Percent-based expansion | |
| Mixed policy | Support both policy types | |

**User's choice:** Fixed pixel padding.
**Notes:** Skeleton/keypoint crops keep full padded canvas with out-of-image padding; out-of-frame skeleton points remain valid and should be treated as occluded (`v=1`). Non-skeleton labels clip to image bounds. Zero/negative bbox => FAIL (`invalid_bbox`).

---

## Report schema and output files

| Option | Description | Selected |
|--------|-------------|----------|
| CSV + JSON + NDJSON | Flat triage + structured + trace stream | ✓ |
| CSV + JSON only | No line-oriented trace output | |
| JSON only | Structured output only | |

**User's choice:** CSV + JSON + NDJSON.
**Notes:** Include final verdict + per-rule detail in CSV/JSON; always include crop path + failure reasons; write to unique timestamped run directory.

---

## the agent's Discretion

No discretion requested.

## Deferred Ideas

None.
