---
phase: 06
slug: deterministic-verification-core-reporting
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-06-13
---

# Phase 06 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest |
| **Config file** | `pyproject.toml` |
| **Quick run command** | `pytest -q tests/phase6` |
| **Full suite command** | `pytest -q` |
| **Estimated runtime** | ~120 seconds |

---

## Sampling Rate

- **After every task commit:** Run `pytest -q tests/phase6`
- **After every plan wave:** Run `pytest -q`
- **Before `/gsd-verify-work`:** Full suite must be green
- **Max feedback latency:** 120 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 06-01-01 | 01 | 1 | VER-01 | T-06-01 | Deterministic fixed-padding cropper with skeleton/non-skeleton edge policy | unit | `pytest -q tests/phase6/test_cropper.py -x` | ❌ W0 | ⬜ pending |
| 06-01-02 | 01 | 1 | VER-02 | T-06-02 | Deterministic rule engine enforces PASS/FAIL-only semantics | unit | `pytest -q tests/phase6/test_rules_engine.py -x` | ❌ W0 | ⬜ pending |
| 06-02-01 | 02 | 2 | VER-03 | T-06-03 | CSV/JSON/NDJSON include per-rule details and failure reasons | integration | `pytest -q tests/phase6/test_reporting.py -x` | ❌ W0 | ⬜ pending |
| 06-03-01 | 03 | 3 | VER-04 | T-06-04 | Deterministic-only execution works without VLM dependency | integration | `pytest -q tests/phase6/test_run_verify.py -x` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/phase6/test_cropper.py` — fixed-padding + out-of-frame policy coverage
- [ ] `tests/phase6/test_rules_engine.py` — rule evaluation + PASS/FAIL aggregation coverage
- [ ] `tests/phase6/test_reporting.py` — CSV/JSON/NDJSON schema and reason/path coverage
- [ ] `tests/phase6/test_run_verify.py` — deterministic-only run path and exit-code semantics

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Generated crop artifacts visually match expected padding policy | VER-01 | Human review is best for crop visual sanity across label types | Inspect representative crop images from timestamped run directory for skeleton and non-skeleton cases |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 120s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
