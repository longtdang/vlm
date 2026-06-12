---
phase: 02
slug: pose-contract-mapping
status: verified
threats_open: 0
asvs_level: 1
created: 2026-06-12
---

# Phase 02 — Security

> Per-phase security contract: threat register, accepted risks, and audit trail.

---

## Trust Boundaries

| Boundary | Description | Data Crossing |
|----------|-------------|---------------|
| Datumaro JSON -> importer preflight | Untrusted annotation/category structure enters validation layer | Annotation schema payloads |
| preflight diagnostics -> summary output | Validation diagnostics are persisted as machine-readable output | Mismatch metadata and sample identifiers |
| preflight gate -> dataset write path | Invalid data must not pass into persisted labels | Keypoint coordinates and visibility labels |

---

## Threat Register

| Threat ID | Category | Component | Disposition | Mitigation | Status |
|-----------|----------|-----------|-------------|------------|--------|
| T-02-01 | Tampering | `pose_contract.py` skeleton parsing | mitigate | Strict type/range validation and ambiguity rejection in `extract_canonical_skeleton_contract` | closed |
| T-02-02 | Repudiation | `preflight.py` mismatch reporting | mitigate | Structured category buckets with bounded sample IDs in `PreflightReport` | closed |
| T-02-03 | Denial of Service | malformed schema propagation | mitigate | Fail-fast preflight gates before any dataset writes | closed |
| T-02-04 | Tampering | `run_import.py` keypoint mapping | mitigate | Canonical mapping checks reject extra joints and enforce deterministic alignment | closed |
| T-02-05 | Integrity | visibility semantics | mitigate | Visibility defaults only when absent; invalid values/length rejected | closed |
| T-02-06 | Repudiation | mismatch diagnostics expected/actual detail | accept | Gap accepted for Phase 2; diagnostics remain aggregated but without explicit expected/actual fields | closed |

*Status: open · closed*  
*Disposition: mitigate (implementation required) · accept (documented risk) · transfer (third-party)*

---

## Accepted Risks Log

| Risk ID | Threat Ref | Rationale | Accepted By | Date |
|---------|------------|-----------|-------------|------|
| AR-02-01 | T-02-06 | Current implementation reports mismatch categories and sample IDs but does not yet emit explicit expected/actual fields; accepted to avoid reopening Phase 2 scope. | user | 2026-06-12 |

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
