---
phase: 03
slug: visibility-fidelity
status: verified
threats_open: 0
asvs_level: 1
created: 2026-06-12
---

# Phase 03 — Security

> Per-phase security contract: threat register, accepted risks, and audit trail.

---

## Trust Boundaries

| Boundary | Description | Data Crossing |
|----------|-------------|---------------|
| Datumaro annotation payload -> visibility mapper | Untrusted visibility arrays enter conversion and validation path | Visibility vectors and point coordinates |
| Mapper output -> keypoint metadata | Visibility semantics are persisted for rendering and audit | `visibility`, `source_visibility`, `visibility_defaulted` |
| Keypoint mapping -> run summary diagnostics | User-facing counts must reflect mapped outputs consistently | Absent/hidden/visible counters and defaulted counts |

---

## Threat Register

| Threat ID | Category | Component | Disposition | Mitigation | Status |
|-----------|----------|-----------|-------------|------------|--------|
| T-03-01 | Tampering | `run_import.py` visibility parsing | mitigate | Strict visibility domain/length validation with invalid payload mismatch handling | closed |
| T-03-02 | Integrity | keypoint rendering semantics | mitigate | Absent -> `NaN` rendering and preserved hidden/visible distinction in metadata | closed |
| T-03-03 | Repudiation | visibility audit metadata | mitigate | Persist source visibility and default-applied marker per keypoint | closed |
| T-03-04 | Repudiation | run summary diagnostics | mitigate | Stable visibility summary payload (`absent/hidden/visible/defaulted_annotations`) emitted per run | closed |
| T-03-05 | Integrity | counter derivation path | mitigate | Summary counters derived from same mapped visibility arrays used for keypoint writes | closed |
| T-03-06 | Denial of Service | malformed visibility payloads | mitigate | Preflight/write gate blocks dataset writes when mismatches are detected | closed |

*Status: open · closed*  
*Disposition: mitigate (implementation required) · accept (documented risk) · transfer (third-party)*

---

## Accepted Risks Log

None.

---

## Security Audit Trail

| Audit Date | Threats Total | Closed | Open | Run By |
|------------|---------------|--------|------|--------|
| 2026-06-12 | 6 | 6 | 0 | gsd-security-auditor + orchestrator |

---

## Sign-Off

- [x] All threats have a disposition (mitigate / accept / transfer)
- [x] Accepted risks documented in Accepted Risks Log
- [x] `threats_open: 0` confirmed
- [x] `status: verified` set in frontmatter

**Approval:** verified 2026-06-12
