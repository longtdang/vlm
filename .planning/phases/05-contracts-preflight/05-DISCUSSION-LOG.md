# Phase 5: Contracts & Preflight - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-06-13
**Phase:** 5-contracts-preflight
**Areas discussed:** Mapping metadata entry schema, field identity contract, visibility preflight policy

---

## Mapping metadata entry schema

| Option | Description | Selected |
|--------|-------------|----------|
| label_id + full mapping fields | `label_id, source_label_name, target_field, skeleton_labels, skeleton_edges, visibility_policy` | ✓ |
| Minimal id/field only | `label_id, target_field` | |
| Name/count only | `label_name, target_field, point_count` | |

**User's choice:** `label_id, source_label_name, target_field, skeleton_labels, skeleton_edges, visibility_policy`
**Notes:** User asked purpose; clarified this supports audit/debug traceability and downstream rule joins.

---

## Field identity contract

| Option | Description | Selected |
|--------|-------------|----------|
| Stable ID-based target field | `keypoints_label_<id>` + readable alias in metadata | ✓ |
| Label-slug based field | Use label text slug as identity | |
| Parent+label composite | Use hierarchy text identity | |

**User's choice:** Stable ID-based field with metadata alias.
**Notes:** User explicitly prefers stable field names when label text changes; alias can change, field name cannot.

---

## Visibility preflight policy

| Option | Description | Selected |
|--------|-------------|----------|
| Hard fail invalid visibility | Block import on invalid values or point/visibility length mismatch | ✓ |
| Soft-review invalid visibility | Continue import with REVIEW-marked items | |
| Silent coercion | Coerce values to nearest valid state | |

**User's choice:** Hard fail invalid visibility.
**Notes:** Missing visibility remains allowed with default `2` and warning/count tracking.

---

## the agent's Discretion

No discretion requested.

## Deferred Ideas

None.
