# Phase 2: Pose Contract Mapping - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-06-12
**Phase:** 2-pose-contract-mapping
**Areas discussed:** Skeleton source-of-truth policy, Schema mismatch failure policy, Keypoint ordering contract

---

## Skeleton source-of-truth policy

| Option | Description | Selected |
|--------|-------------|----------|
| Datumaro categories.points as canonical; optional config only for validation | Treat source annotations as authority and use config for contract checks only | ✓ |
| Config skeleton as canonical; Datumaro only as fallback | Config defines final structure even when source provides skeleton | |
| Require exact match between Datumaro and config, otherwise fail | Enforce strict dual-source alignment | |

**User's choice:** Datumaro categories.points as canonical; optional config only for validation.
**Notes:** User also selected strict fail behavior for missing skeleton, invalid edges, and ambiguous multi-spec skeleton input.

---

## Schema mismatch failure policy

| Option | Description | Selected |
|--------|-------------|----------|
| Preflight before creating any samples | Validate contract up front before write operations | ✓ |
| Per-sample during mapping; fail at first bad item | Detect during loop and stop immediately | |
| Per-sample with warnings, fail only at end | Continue collecting errors before final fail | |

**User's choice:** Preflight validation before sample creation with hard-fail mismatch policy.
**Notes:** User selected hard-fail on keypoint count mismatch, default-only for missing visibility, hard-fail for invalid visibility data, and aggregated mismatch reporting with sample ID previews.

---

## Keypoint ordering contract

| Option | Description | Selected |
|--------|-------------|----------|
| Skeleton labels order from canonical Datumaro spec | Use canonical skeleton label index ordering | ✓ |
| Order as provided per annotation instance | Keep per-record order without canonical reindex | |
| Sort labels alphabetically | Canonicalize by lexical order | |

**User's choice:** Canonical ordering from skeleton labels.
**Notes:** User chose indexed NaN padding for missing joints, hard-fail for extra joints, and deterministic pose list ordering via Datumaro order with ID sorting when available.

---

## the agent's Discretion

None.

## Deferred Ideas

None.
