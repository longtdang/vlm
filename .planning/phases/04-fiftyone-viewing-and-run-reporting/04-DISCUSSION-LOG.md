# Phase 4: FiftyOne Viewing and Run Reporting - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-06-12
**Phase:** 4-fiftyone-viewing-and-run-reporting
**Areas discussed:** launch behavior, report schema shape, diagnostics stability

---

## Launch behavior

| Option | Description | Selected |
|--------|-------------|----------|
| Explicit `--launch` opt-in only (recommended) | Launch FiftyOne app only when user requests it | ✓ |
| Always launch after successful import | Convenient but disruptive for automation and CI usage | |
| Auto-launch on first run only | Stateful behavior increases complexity | |

**User's choice:** Auto-selected recommended option.
**Notes:** [auto] Maintain predictable CLI behavior for scripted usage.

---

## Report schema shape

| Option | Description | Selected |
|--------|-------------|----------|
| Additive summary expansion (recommended) | Keep existing keys, add warning/failure aggregates | ✓ |
| Replace summary schema with a new version | Breaks backward compatibility for consumers | |
| Keep minimal summary only | Insufficient for OUT-02 observability | |

**User's choice:** Auto-selected recommended option.
**Notes:** [auto] Preserve compatibility with Phase 2/3 summary consumers.

---

## Diagnostics stability

| Option | Description | Selected |
|--------|-------------|----------|
| Count + category buckets (recommended) | Simple to parse and actionable for users/automation | ✓ |
| Freeform text-only diagnostics | Hard to aggregate and test | |
| Per-sample verbose dump by default | Noisy output for common runs | |

**User's choice:** Auto-selected recommended option.
**Notes:** [auto] Structured counts with categorized details preferred.

---

## the agent's Discretion

Implementation may choose exact field names for new diagnostic aggregates as long as schema is stable and machine-readable.

## Deferred Ideas

- Advanced analytics beyond OUT-01/OUT-02 remain deferred to v2 enhancement phases.
