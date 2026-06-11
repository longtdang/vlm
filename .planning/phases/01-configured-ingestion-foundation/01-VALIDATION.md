---
phase: 1
slug: configured-ingestion-foundation
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-06-11
---

# Phase 1 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest |
| **Config file** | none — Wave 0 installs |
| **Quick run command** | `pytest -q tests/phase1 -x` |
| **Full suite command** | `pytest -q` |
| **Estimated runtime** | ~60 seconds |

---

## Sampling Rate

- **After every task commit:** Run `pytest -q tests/phase1 -x`
- **After every plan wave:** Run `pytest -q`
- **Before `/gsd-verify-work`:** Full suite must be green
- **Max feedback latency:** 90 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 1-01-01 | 01 | 1 | CONF-01..04 | T-1-01 | Reject invalid config and unknown fields | unit | `pytest -q tests/phase1/test_config.py -x` | ❌ W0 | ⬜ pending |
| 1-01-02 | 01 | 1 | ING-01..03 | T-1-02 | Deterministic matching and mismatch failure policy | unit+integration | `pytest -q tests/phase1/test_ingestion_matching.py -x` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/phase1/test_config.py` — config schema/path validation stubs
- [ ] `tests/phase1/test_ingestion_matching.py` — matching/mismatch behavior stubs
- [ ] `tests/conftest.py` — shared temporary dataset fixtures

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Validate CLI summary readability | ING-03 | Human readability judgment | Run importer on mixed-good/bad sample set and review console + JSON summary clarity |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 90s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
