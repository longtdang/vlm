# Phase 5: Contracts & Preflight - Research

**Researched:** 2026-06-13
**Domain:** Datumaro JSON → FiftyOne keypoint contract mapping + preflight validation
**Confidence:** HIGH

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
### Field identity contract
- **D-01:** Use `label_id` as canonical skeleton identity.
- **D-02:** Target keypoint field naming must be stable and ID-based: `keypoints_label_<id>`.
- **D-03:** Human-readable label slug/name is metadata only; it must not drive field identity.
- **D-04:** If label text changes while `label_id` is unchanged, keep the same field name and update alias metadata only.

### Visibility preflight policy
- **D-05:** Visibility vectors with invalid values (not in `{0,1,2}`) or length mismatches against points are hard preflight failures that block import.
- **D-06:** Missing visibility with valid points is allowed; default to `2` and record warning/count in summary.

### Mapping metadata artifact
- **D-07:** Persist mapping metadata in run summary JSON under a dedicated `mapping` section.
- **D-08:** Minimum mapping entry fields are: `label_id`, `source_label_name`, `target_field`, `skeleton_labels`, `skeleton_edges`, `visibility_policy`.

### Claude's Discretion
No open discretion items; implementation decisions above are locked.

### Deferred Ideas (OUT OF SCOPE)
None — discussion stayed within phase scope.
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| SKEL-01 | Import multi-skeleton annotations into separate label-specific keypoint fields | Per-field `dataset.skeletons` mapping pattern and ID-based field contract |
| SKEL-02 | Importer must not collapse skeleton types into one field | Locked D-01..D-04 + architecture pattern: route each `label_id` to dedicated field |
| SKEL-03 | Run output/metadata must show skeleton→field mapping | Dedicated `summary.mapping` artifact design with required fields D-07/D-08 |
</phase_requirements>

## Summary
Current importer already enforces critical preflight checks for keypoint visibility length/value validity and records warning/failure rollups in summary output. [VERIFIED: codebase `src/fiftyone_pose_importer/run_import.py`]

For Phase 5 planning, the main gap is **contract projection**: today keypoints are stored under a single `label_field`, while the phase requires deterministic per-skeleton field assignment keyed by `label_id` (`keypoints_label_<id>`) plus auditable mapping metadata in summary. [VERIFIED: codebase `src/fiftyone_pose_importer/run_import.py`; VERIFIED: context `05-CONTEXT.md`]

FiftyOne’s model supports this directly: dataset-level `skeletons` is a dict keyed by field name, and each field can have its own `KeypointSkeleton`; App rendering uses these skeleton definitions. [CITED: https://docs.voxel51.com/user_guide/using_datasets.html] [CITED: https://docs.voxel51.com/api/fiftyone.core.dataset.html]

**Primary recommendation:** Implement a deterministic `label_id -> keypoints_label_<id>` router in importer write path, set `dataset.skeletons[field]` per contract, and emit `summary.mapping[]` entries for every seen skeleton type. [VERIFIED: context `05-CONTEXT.md`]

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Parse Datumaro JSON categories/items | API / Backend | Database / Storage | Import-time transform logic lives in Python importer process. |
| Resolve skeleton contract by `label_id` | API / Backend | — | Domain validation/business rule; no UI ownership. |
| Preflight visibility validation (`0/1/2`, length) | API / Backend | — | Must hard-fail before dataset write. |
| Keypoint field routing (`keypoints_label_<id>`) | API / Backend | Database / Storage | Backend constructs sample fields; DB persists schema. |
| Skeleton rendering semantics in FiftyOne app | Frontend Server (SSR) | API / Backend | Backend stores skeleton metadata; app consumes for visualization. [CITED: https://docs.voxel51.com/user_guide/using_datasets.html] |
| Mapping audit artifact in summary JSON | API / Backend | Database / Storage | Import process generates run artifact for traceability. |

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| fiftyone | 1.17.0 (latest, 2026-06-09) | Dataset + keypoint/skeleton model + app rendering | Native support for `Keypoint`, `KeypointSkeleton`, per-field skeleton dict. [VERIFIED: PyPI + docs] |
| pydantic | 2.12.4 installed (2.13.4 latest, 2026-05-06) | Config contract validation | Already used; strong typed config and validation errors. [VERIFIED: codebase `config_model.py`; VERIFIED: PyPI] |
| PyYAML | 6.0.3 (latest, 2025-09-29) | YAML config loading | Already wired through `yaml.safe_load`. [VERIFIED: codebase `config_loader.py`; VERIFIED: PyPI] |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| pytest | 9.0.3 (latest, 2026-04-07) | Phase regression tests | Add phase5 contract/preflight tests before implementation changes. [VERIFIED: local env + tests/] |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Custom skeleton render metadata | FiftyOne `dataset.skeletons` | Built-in path is less error-prone and App-native. [CITED: https://docs.voxel51.com/user_guide/using_datasets.html] |
| Slug/name-based field IDs | `label_id`-based field IDs | Name-based IDs break on rename; violates locked D-01..D-04. [VERIFIED: `05-CONTEXT.md`] |

**Installation:**
```bash
pip install -e .
```

**Version verification:**
```bash
pip index versions fiftyone
pip index versions pydantic
pip index versions pyyaml
pip index versions pytest
```

## Package Legitimacy Audit

| Package | Registry | Age | Downloads | Source Repo | Verdict | Disposition |
|---------|----------|-----|-----------|-------------|---------|-------------|
| fiftyone | PyPI | ~5.5 years | 133,108/month | github.com/voxel51/fiftyone | OK | Approved (already project dependency) |
| pydantic | PyPI | ~9.1 years | 1,014,658,341/month | github.com/pydantic/pydantic | OK | Approved (already project dependency) |
| PyYAML | PyPI | ~15 years | 1,049,886,457/month | github.com/yaml/pyyaml | OK | Approved (already project dependency) |

**Packages removed due to [SLOP] verdict:** none
**Packages flagged as suspicious [SUS]:** none

## Architecture Patterns

### System Architecture Diagram
```text
Datumaro JSON
   |
   v
[Contract Extractor]
  - parse categories.points.items
  - build by_label_id contracts
   |
   +--> preflight: invalid/missing contract? ----> [Fail summary + stop]
   |
   v
[Annotation Mapper]
  - read per annotation label_id
  - validate visibility (0/1/2 + length)
  - default missing visibility to 2 (+warning)
   |
   +--> invalid visibility? ----------------------> [Fail summary + stop]
   |
   v
[Field Router]
  label_id -> keypoints_label_<id>
  create fo.Keypoint + metadata attrs
   |
   v
[FiftyOne Dataset Writer]
  - sample[field] = fo.Keypoints(...)
  - dataset.skeletons[field] = KeypointSkeleton(...)
   |
   v
[Summary Writer]
  preflight + failures/warnings + mapping[]
```

### Recommended Project Structure
```text
src/fiftyone_pose_importer/
├── run_import.py        # orchestration + routing + summary assembly
├── pose_contract.py     # extract/normalize per-label skeleton contracts
├── preflight.py         # mismatch aggregation model
├── summary.py           # summary JSON writer
└── config_model.py      # import config contract
```

### Pattern 1: ID-Based Skeleton Field Router
**What:** Route each skeleton annotation into its own field using canonical `label_id`.
**When to use:** Multi-skeleton datasets where each type has distinct edges/labels.
**Example:**
```python
field = f"keypoints_label_{label_id}"
sample.setdefault(field, fo.Keypoints(keypoints=[]))
sample[field].keypoints.append(kp)
dataset.skeletons[field] = fo.KeypointSkeleton(labels=contract.labels, edges=contract.edges)
# Source: FiftyOne dataset skeleton docs + phase D-01..D-04
```

### Pattern 2: Strict Visibility Preflight with Auditable Defaulting
**What:** Enforce allowed values/length; default only when visibility missing entirely.
**When to use:** Contract-first import where semantic fidelity is critical.
**Example:**
```python
if len(visibility) != len(points):
    raise ValueError("Visibility length does not match points length")
if any(v not in (0, 1, 2) for v in visibility):
    raise ValueError("Visibility values must be one of 0, 1, or 2")
if source_visibility is None:
    visibility = [2] * len(points)
    summary["warnings"]["counts"]["defaulted_visibility_annotations"] += 1
# Source: src/fiftyone_pose_importer/run_import.py
```

### Anti-Patterns to Avoid
- **Slug-driven field identity:** breaks deterministic mapping on rename; violates D-03/D-04.
- **Single-field collapse for all skeleton types:** destroys per-type edge rendering (SKEL-01/SKEL-02).
- **Silent visibility coercion of invalid values:** must fail preflight per D-05.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Keypoint skeleton rendering metadata | Custom sidecar schema consumed by UI | `dataset.skeletons` / `default_skeleton` | Native app rendering + less integration risk. [CITED: https://docs.voxel51.com/user_guide/using_datasets.html] |
| Config parsing/validation | Manual dict parsing and ad-hoc errors | Pydantic models + validators | Existing code already standardized and strict. [VERIFIED: codebase `config_model.py`] |
| Summary file path policy | Inline duplicated path logic | `write_summary()` helper | Existing stable output contract. [VERIFIED: codebase `summary.py`] |

**Key insight:** Phase 5 risk is semantic drift, not algorithm complexity—reuse existing strict contract points and only extend deterministic routing/audit surfaces.

## Common Pitfalls

### Pitfall 1: Assigning skeleton by label name instead of `label_id`
**What goes wrong:** Renamed labels create new fields and break continuity.
**Why it happens:** Name is human-friendly but not stable identity.
**How to avoid:** Always compute field from integer `label_id` and keep display name as metadata.
**Warning signs:** Same `label_id` appears in multiple output fields across runs.

### Pitfall 2: Mixing 1-based and 0-based joint indices
**What goes wrong:** Edge endpoints point to wrong keypoints or fail validation.
**Why it happens:** Datumaro `points.items.joints` commonly exported 1-based in sample data.
**How to avoid:** Normalize joints once in `pose_contract.py` and test it.
**Warning signs:** Valid source skeleton produces out-of-range edge errors. [VERIFIED: codebase `pose_contract.py`; VERIFIED: sample `data/datumaro.json`]

### Pitfall 3: Treating missing visibility and invalid visibility the same
**What goes wrong:** Bad annotations sneak through or good annotations fail unnecessarily.
**Why it happens:** Over-simplified “default everything” logic.
**How to avoid:** Missing visibility => default+warn (D-06); invalid values/length => hard fail (D-05).
**Warning signs:** preflight summary lacks explicit mismatch categories for invalid visibility.

## Code Examples

### Setting per-field keypoint skeletons
```python
import fiftyone as fo

dataset.skeletons = {
    "keypoints_label_4": fo.KeypointSkeleton(labels=["base-LU", "arm-LU"], edges=[[0, 1]]),
    "keypoints_label_17": fo.KeypointSkeleton(labels=["base-LU", "arm-LU", "base-LM"], edges=[[0, 1], [1, 2]]),
}
```
Source: [CITED: https://docs.voxel51.com/user_guide/using_datasets.html]

### Keypoint coordinate contract
```python
# points are normalized [0,1] pairs
kp = fo.Keypoint(points=[[0.1, 0.2], [0.3, 0.4]])
```
Source: [CITED: https://docs.voxel51.com/api/fiftyone.core.labels.html#fiftyone.core.labels.Keypoint]

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Single `label_field` keypoints with one default skeleton | Per-skeleton-type field mapping with per-field skeletons | Required by v1.1 SKEL-01..03 | Correct connected-edge rendering and auditable mapping |
| Implicit mapping behavior | Explicit run summary `mapping` artifact | Phase 5 design decision D-07/D-08 | Deterministic traceability for downstream verification |

**Deprecated/outdated:**
- Name/slug-based field identity for skeleton contracts — replaced by `label_id` contract in this phase.

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | ASVS V2/V3/V4 are not directly in scope for this local importer phase | Security Domain | Could under-specify security controls if auth/session is later introduced |

## Open Questions (RESOLVED)

1. **Should `datumaro` Python package become an explicit dependency in this phase?** **RESOLVED: No.**
   - What we know: Current importer succeeds with direct JSON parsing; `datumaro` package is not installed locally.
   - Resolution: Phase 5 remains contract-and-preflight focused, so no parser-library migration is introduced here.
   - Follow-up: Re-evaluate in a later phase only if requirements explicitly add parser abstraction/library migration.

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| python3 | importer runtime/tests | ✓ | 3.13.12 | — |
| pip3 | dependency management | ✓ | 26.0.1 | — |
| pytest | validation architecture | ✓ | 9.0.3 | — |
| fiftyone | dataset model/render integration | ✓ | 1.17.0 | mock module in tests |
| pydantic | config validation | ✓ | 2.12.4 | — |
| PyYAML | config loading | ✓ | 6.0.3 | — |
| datumaro (python lib) | optional parser path | ✗ | — | Continue JSON contract parsing (current implementation) |

**Missing dependencies with no fallback:**
- none

**Missing dependencies with fallback:**
- datumaro Python package (fallback: current JSON-based importer path)

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 9.0.3 |
| Config file | none (uses defaults + `tests/conftest.py`) |
| Quick run command | `pytest -q tests/phase2 tests/phase4 -x` |
| Full suite command | `pytest -q tests -x` |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| SKEL-01 | Separate keypoint field per skeleton type + skeleton assignment | unit | `pytest -q tests/phase5/test_contracts_preflight.py::test_per_label_id_field_mapping -x` | ❌ Wave 0 |
| SKEL-02 | No collapse into shared field | unit | `pytest -q tests/phase5/test_contracts_preflight.py::test_no_single_field_collapse -x` | ❌ Wave 0 |
| SKEL-03 | Summary includes auditable mapping section | unit | `pytest -q tests/phase5/test_contracts_preflight.py::test_mapping_metadata_emitted -x` | ❌ Wave 0 |

### Sampling Rate
- **Per task commit:** `pytest -q tests/phase5 -x` (once created)
- **Per wave merge:** `pytest -q tests -x`
- **Phase gate:** Full suite green before `/gsd-verify-work`

### Wave 0 Gaps
- [ ] `tests/phase5/test_contracts_preflight.py` — SKEL-01/02/03 contract tests
- [ ] Fixture helper for synthetic multi-skeleton datumaro payloads

## Security Domain

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | no | N/A for local importer CLI [ASSUMED] |
| V3 Session Management | no | N/A for local importer CLI [ASSUMED] |
| V4 Access Control | no | Local file access only; no user roles [ASSUMED] |
| V5 Input Validation | yes | Pydantic config validation + strict preflight checks [VERIFIED: codebase `config_loader.py`, `run_import.py`] |
| V6 Cryptography | no | Not required in current phase scope [ASSUMED] |

### Known Threat Patterns for Python local-import stack

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Malformed JSON causing silent bad import | Tampering | Fail-fast schema checks + `SchemaContractError` buckets [VERIFIED: codebase `pose_contract.py`, `run_import.py`] |
| Path misuse in config | Tampering | URL rejection + path existence checks [VERIFIED: codebase `config_model.py`, `config_loader.py`] |
| Oversized/invalid visibility vectors | Tampering | Length/value validation before write [VERIFIED: codebase `run_import.py`] |

## Project Constraints (from copilot-instructions.md)

- Runtime is local single-user workflow. [VERIFIED: `copilot-instructions.md`]
- Required source format is Datumaro JSON export from CVAT. [VERIFIED: `copilot-instructions.md`]
- Config-first setup (no hardcoded paths in import logic). [VERIFIED: `copilot-instructions.md`]
- Visibility semantics correctness is mandatory for trust. [VERIFIED: `copilot-instructions.md`]

## Sources

### Primary (HIGH confidence)
- Local codebase: `src/fiftyone_pose_importer/run_import.py`, `pose_contract.py`, `config_loader.py`, `config_model.py`, `summary.py`, tests under `tests/phase2`, `tests/phase4`.
- Phase context: `.planning/phases/05-contracts-preflight/05-CONTEXT.md`
- Requirements: `.planning/REQUIREMENTS.md`

### Secondary (MEDIUM confidence)
- FiftyOne user guide (keypoint skeleton storage): https://docs.voxel51.com/user_guide/using_datasets.html
- FiftyOne dataset API (`skeletons`, `default_skeleton`): https://docs.voxel51.com/api/fiftyone.core.dataset.html
- FiftyOne Keypoint API (`points` normalized in [0,1]): https://docs.voxel51.com/api/fiftyone.core.labels.html#fiftyone.core.labels.Keypoint
- CVAT Datumaro format docs: https://docs.cvat.ai/docs/dataset_management/formats/format-datumaro/

### Tertiary (LOW confidence)
- None.

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - versions verified from local env + PyPI index; stack already in repo.
- Architecture: HIGH - driven by locked decisions D-01..D-08 and existing importer seams.
- Pitfalls: HIGH - directly observed from current code/tests and phase constraints.

**Research date:** 2026-06-13
**Valid until:** 2026-07-13
