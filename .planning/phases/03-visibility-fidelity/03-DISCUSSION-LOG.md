# Phase 3: Visibility Fidelity - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-06-12
**Phase:** 3-visibility-fidelity
**Areas discussed:** visibility semantics mapping, source metadata fidelity, diagnostics and reporting

---

## Visibility semantics mapping

| Option | Description | Selected |
|--------|-------------|----------|
| Preserve exact 0/1/2 semantics end-to-end (recommended) | Keep absent/hidden/visible states distinct through import output | ✓ |
| Collapse hidden/visible into binary visible flag | Simpler output but loses source fidelity | |
| Store visibility only as summary-level aggregate | No per-keypoint auditability | |

**User's choice:** Auto-selected recommended option.
**Notes:** [auto] Preserve strict three-state contract with non-rendered absent handling.

---

## Source metadata fidelity

| Option | Description | Selected |
|--------|-------------|----------|
| Preserve raw source visibility metadata + default markers (recommended) | Keep traceability and indicate fallback/default usage | ✓ |
| Keep only normalized visibility used for rendering | Lower verbosity, reduced auditability | |
| Drop visibility metadata after conversion | Not acceptable for VIS-03 | |

**User's choice:** Auto-selected recommended option.
**Notes:** [auto] Raw source visibility retained; missing visibility default behavior explicitly marked.

---

## Diagnostics and reporting

| Option | Description | Selected |
|--------|-------------|----------|
| Report per-visibility-state counts and failures in summary (recommended) | Makes fidelity and drift auditable per run | ✓ |
| Report only generic mismatch totals | Less actionable for debugging | |
| No visibility-specific reporting | Violates phase goal | |

**User's choice:** Auto-selected recommended option.
**Notes:** [auto] Visibility counts and mismatch diagnostics are required outputs.

---

## the agent's Discretion

Metadata field naming conventions are left to implementation as long as machine-readable visibility audit semantics are preserved.

## Deferred Ideas

None.
