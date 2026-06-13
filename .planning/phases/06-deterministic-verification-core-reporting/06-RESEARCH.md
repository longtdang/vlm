# Phase 6: deterministic-verification-core-reporting - Research

**Researched:** 2026-06-13
**Domain:** Deterministic annotation verification pipeline
**Confidence:** MEDIUM

## User Constraints (from CONTEXT.md)

### Locked Decisions
- D-01 PASS/FAIL only (no REVIEW in Phase 6). [VERIFIED: 06-CONTEXT.md]
- D-02 Any failed deterministic rule => object FAIL, else PASS. [VERIFIED: 06-CONTEXT.md]
- D-03 Unevaluable rule => object FAIL with explicit reason. [VERIFIED: 06-CONTEXT.md]
- D-04 Only deterministic PASS objects are eligible for optional Phase 7 VLM checks. [VERIFIED: 06-CONTEXT.md]
- D-05 CLI run must complete with exit code 0 even when objects fail; failures live in artifacts. [VERIFIED: 06-CONTEXT.md]
- D-06..D-09 Rule config = global defaults + per-label overrides; unknown rule names warn, not hard fail. [VERIFIED: 06-CONTEXT.md]
- D-10..D-14 Crop policy and edge behavior are locked (fixed padding, skeleton pad-preserve, non-skeleton clip, invalid bbox fail). [VERIFIED: 06-CONTEXT.md]
- D-15..D-18 Emit CSV+JSON+NDJSON in timestamped run dir; include verdict, per-rule details, crop path, reasons. [VERIFIED: 06-CONTEXT.md]

### Claude's Discretion
No open discretion items for this phase. [VERIFIED: 06-CONTEXT.md]

### Deferred Ideas (OUT OF SCOPE)
None — discussion stayed within phase scope. [VERIFIED: 06-CONTEXT.md]

## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| VER-01 | Fixed-padding crop policy | Cropper design with deterministic pad/clip and invalid_bbox handling [VERIFIED: CONTEXT + ROADMAP] |
| VER-02 | Deterministic per-label rules | Rule registry + global/override config + fail-on-unevaluable [VERIFIED: CONTEXT + REQUIREMENTS] |
| VER-03 | CSV/JSON/NDJSON exports | Use stdlib csv/json + JSON Lines format [CITED: https://docs.python.org/3/library/csv.html] [CITED: https://docs.python.org/3/library/json.html] [CITED: https://jsonlines.org/] |
| VER-04 | Deterministic-only runnable | No VLM dependency in phase execution path [VERIFIED: REQUIREMENTS + CONTEXT] |

## Summary
Build Phase 6 as a backend-only deterministic pipeline extension: object cropper, deterministic rules, strict aggregation, and artifact writers. [VERIFIED: CONTEXT]
Reuse existing project patterns: Pydantic config validation, additive summaries, deterministic ordering, and categorized failures from run_import.py and summary.py. [VERIFIED: src/fiftyone_pose_importer/run_import.py] [VERIFIED: src/fiftyone_pose_importer/summary.py]

Primary recommendation: add a verification package with modules for config, cropper, rules, engine, and reporters; keep deterministic outputs stable via ordered iteration and standard serializers. [CITED: https://docs.python.org/3/library/csv.html] [CITED: https://docs.python.org/3/library/json.html] [ASSUMED]

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Crop generation | API / Backend | Storage | Deterministic image processing and artifact writing are backend tasks. [VERIFIED: CONTEXT] |
| Rule evaluation | API / Backend | — | Deterministic business logic. [VERIFIED: CONTEXT] |
| Verdict aggregation | API / Backend | — | Locked aggregation policy D-02. [VERIFIED: CONTEXT] |
| CSV/JSON/NDJSON export | API / Backend | Storage | Backend serialization to run artifacts. [VERIFIED: CONTEXT] |

## Project Constraints (from copilot-instructions.md)
- Work should stay in GSD workflow conventions. [VERIFIED: copilot-instructions.md]
- Local Python + FiftyOne + Pydantic + PyYAML baseline remains the project standard. [VERIFIED: copilot-instructions.md]
- No .github/skills or .agents/skills found. [VERIFIED: repository scan]

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| Python stdlib csv | Python 3.13 runtime | Deterministic CSV output | DictWriter supports explicit field order and proper CSV handling. [CITED: https://docs.python.org/3/library/csv.html] |
| Python stdlib json | Python 3.13 runtime | JSON/NDJSON serialization | sort_keys and separators support stable output shape. [CITED: https://docs.python.org/3/library/json.html] |
| fiftyone [WARNING: flagged as suspicious — verify before using.] | 1.17.0 | Existing dataset integration | Already project dependency and installed baseline. [VERIFIED: pyproject.toml + pip index versions] |
| Pillow [WARNING: flagged as suspicious — verify before using.] | 12.2.0 | Crop/canvas operations | Official Image APIs (new/crop/paste) fit deterministic cropper needs. [CITED: https://pillow.readthedocs.io/en/stable/reference/Image.html] |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| pydantic [WARNING: flagged as suspicious — verify before using.] | installed 2.12.4, latest 2.13.4 | typed verification config validation | For global/default/override rules schema. [VERIFIED: pyproject.toml + pip index versions] |
| PyYAML [WARNING: flagged as suspicious — verify before using.] | 6.0.3 | YAML config loading | Use safe_load-based config input path. [VERIFIED: codebase + pip index versions] |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Pillow | OpenCV | More dependency/complexity than needed for fixed-padding crop policy. [ASSUMED] |
| stdlib CSV/JSON | pandas | Less control over deterministic line-by-line trace writing. [ASSUMED] |

Installation:
No mandatory new install if environment already satisfies current project dependencies.
Optional if missing: pip install Pillow

Version verification commands:
pip3 index versions fiftyone
pip3 index versions pydantic
pip3 index versions PyYAML
pip3 index versions Pillow

## Package Legitimacy Audit

| Package | Registry | Age | Downloads | Source Repo | Verdict | Disposition |
|---------|----------|-----|-----------|-------------|---------|-------------|
| fiftyone | PyPI | published 2026-06-09 | unknown | github.com/voxel51/fiftyone | SUS | Existing dependency; human-verify before install/upgrade |
| pydantic | PyPI | published 2026-05-06 | unknown | github.com/pydantic/pydantic | SUS | Existing dependency; human-verify before install/upgrade |
| pyyaml | PyPI | published 2025-09-25 | unknown | pyyaml.org | SUS | Existing dependency; human-verify before install/upgrade |
| pillow | PyPI | published 2026-04-01 | unknown | github.com/python-pillow/Pillow | SUS | Optional for cropper; human-verify before install/upgrade |

Packages removed due to SLOP verdict: none.
Packages flagged as suspicious SUS: fiftyone, pydantic, pyyaml, pillow.

## Architecture Patterns

### System Architecture Diagram
Config YAML -> Config validation -> Object enumerator -> Cropper (pad/clip rules) -> Deterministic rule engine (detection, attribute, skeleton-count, visibility-format) -> Aggregator (any fail => FAIL) -> CSV/JSON/NDJSON writers -> timestamped run directory. [VERIFIED: CONTEXT]

### Recommended Project Structure
src/fiftyone_pose_importer/verification/
- config.py
- cropper.py
- rules.py
- engine.py
- report_csv.py
- report_json.py
- types.py
Plus run_verify.py and CLI wiring. [ASSUMED]

### Pattern 1: Ordered deterministic execution
What: sort objects and rules by stable keys before evaluate/write. [ASSUMED]
When: always, for reproducible artifacts.
Example:
Source: https://docs.python.org/3/library/csv.html
writer = csv.DictWriter(f, fieldnames=[run_id, sample_id, object_id, label, verdict])
for row in sorted(rows, key=lambda r: (r[sample_id], r[object_id], r[label])):
    writer.writerow(row)

### Anti-Patterns to Avoid
- Non-deterministic iteration in exporters. [ASSUMED]
- Treating rule runtime errors as PASS (violates D-03). [VERIFIED: CONTEXT]
- Forgetting crop path/failure reason in rows (violates D-18). [VERIFIED: CONTEXT]

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| CSV escaping/quoting | manual join formatter | csv.DictWriter | Correct escaping and stable schema control. [CITED: https://docs.python.org/3/library/csv.html] |
| JSON encoding | hand-built JSON strings | json.dump/json.dumps | Correct escaping and stable sort options. [CITED: https://docs.python.org/3/library/json.html] |
| Image canvas ops | custom pixel loops | Pillow Image.new/crop/paste | Standard tested image primitives. [CITED: https://pillow.readthedocs.io/en/stable/reference/Image.html] |

Key insight: deterministic planning should maximize standard-library serialization and explicit ordering. [ASSUMED]

## Common Pitfalls

### Pitfall 1: REVIEW-status mismatch
What goes wrong: VER-02 wording mentions PASS/FAIL/REVIEW, while D-01 locks PASS/FAIL only. [VERIFIED: REQUIREMENTS + CONTEXT]
How to avoid: plan Phase 6 outputs as PASS/FAIL only unless user reopens decision. [VERIFIED: CONTEXT]

### Pitfall 2: Schema drift across CSV/JSON/NDJSON
What goes wrong: exporters diverge in fields and reason strings. [ASSUMED]
How to avoid: define one canonical result model then project to all exporters. [ASSUMED]

## Code Examples

Source: https://docs.python.org/3/library/json.html and https://jsonlines.org/
json.dump(report, f_json, ensure_ascii=False, sort_keys=True, indent=2)
for evt in events:
    f_ndjson.write(json.dumps(evt, ensure_ascii=False, sort_keys=True, separators=(,, :)) + 
)

Source: https://pillow.readthedocs.io/en/stable/reference/Image.html
canvas = Image.new(image.mode, (crop_w, crop_h), color=0)
patch = image.crop((src_l, src_t, src_r, src_b))
canvas.paste(patch, (dst_x, dst_y))

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Import-only artifact reporting | Deterministic post-import verification artifacts | Phase 6 scope | Auditable per-object QA outcomes independent of VLM. [VERIFIED: ROADMAP + CONTEXT] |

Deprecated/outdated:
- Assuming deterministic verification requires VLM in Phase 6. [VERIFIED: VER-04 + CONTEXT]

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | OpenCV/pandas are unnecessary for this phase | Standard Stack | Team may prefer different internal standard |
| A2 | Sorted output keys should be sample_id/object_id/label | Patterns | Ordering might not match stakeholder preference |

## Open Questions
1. Should Phase 6 emit REVIEW at all?
   - What we know: D-01 says no REVIEW.
   - What is unclear: VER-02 text includes REVIEW.
   - Recommendation: treat D-01 as locked unless user explicitly changes it.

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| python3 | runtime | ✓ | 3.13.12 | — |
| pip3 | package management | ✓ | 26.0.1 | — |
| pytest | test execution | ✓ | 9.0.3 | python -m pytest |
| fiftyone | integration | ✓ | 1.17.0 | none |
| Pillow | cropper | ✓ | 12.2.0 | use existing image utility path [ASSUMED] |

Missing dependencies with no fallback: none.
Missing dependencies with fallback: none.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 9.0.3 |
| Config file | none detected |
| Quick run command | pytest tests/phase6 -q |
| Full suite command | pytest -q |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| VER-01 | crop policy and edge handling | unit | pytest tests/phase6/test_cropper.py -q | ❌ Wave 0 |
| VER-02 | deterministic rule engine + aggregation | unit | pytest tests/phase6/test_rules_engine.py -q | ❌ Wave 0 |
| VER-03 | CSV/JSON/NDJSON report schema | unit/integration | pytest tests/phase6/test_reporting.py -q | ❌ Wave 0 |
| VER-04 | deterministic-only execution path | integration | pytest tests/phase6/test_run_verify.py -q | ❌ Wave 0 |

### Sampling Rate
- Per task commit: pytest tests/phase6 -q
- Per wave merge: pytest -q
- Phase gate: full suite green before /gsd-verify-work

### Wave 0 Gaps
- tests/phase6/test_cropper.py
- tests/phase6/test_rules_engine.py
- tests/phase6/test_reporting.py
- tests/phase6/test_run_verify.py

## Security Domain

### Applicable ASVS Categories
| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | no | local CLI scope only [VERIFIED: PROJECT/ROADMAP] |
| V3 Session Management | no | local batch run only [VERIFIED: PROJECT/ROADMAP] |
| V4 Access Control | no | single-user local workflow [VERIFIED: STATE/PROJECT] |
| V5 Input Validation | yes | Pydantic config + annotation schema checks [VERIFIED: config_model.py + run_import.py] |
| V6 Cryptography | no | not required by phase scope [VERIFIED: REQUIREMENTS/ROADMAP] |

### Known Threat Patterns for stack
| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Path traversal via output names | Tampering | sanitize identifiers and enforce run-dir rooted writes [ASSUMED] |
| CSV formula injection in analyst tools | Tampering | escape risky leading characters in CSV cells [ASSUMED] |
| Malformed annotation crash | DoS | fail-object with reason and continue run (D-03/D-05) [VERIFIED: CONTEXT] |

## Sources

### Primary (HIGH confidence)
- .planning/phases/06-deterministic-verification-core-reporting/06-CONTEXT.md
- .planning/REQUIREMENTS.md
- .planning/ROADMAP.md
- src/fiftyone_pose_importer/run_import.py
- src/fiftyone_pose_importer/config_loader.py
- src/fiftyone_pose_importer/config_model.py
- src/fiftyone_pose_importer/summary.py

### Secondary (MEDIUM confidence)
- https://docs.python.org/3/library/csv.html
- https://docs.python.org/3/library/json.html
- https://pillow.readthedocs.io/en/stable/reference/Image.html
- https://jsonlines.org/

### Tertiary (LOW confidence)
- Assumptions A1-A2.

## Metadata

Confidence breakdown:
- Standard stack: MEDIUM (official docs + local version checks, but legitimacy seam flagged SUS due missing download telemetry)
- Architecture: HIGH (locked by CONTEXT decisions)
- Pitfalls: MEDIUM (one verified contract mismatch + assumption-based operational pitfalls)

Research date: 2026-06-13
Valid until: 2026-07-13
