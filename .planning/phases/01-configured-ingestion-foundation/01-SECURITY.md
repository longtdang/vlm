---
phase: 1
slug: configured-ingestion-foundation
status: verified
threats_open: 0
asvs_level: 1
created: 2026-06-11
---

# Phase 1 — Security

> Per-phase security contract: threat register, accepted risks, and audit trail.

---

## Trust Boundaries

| Boundary | Description | Data Crossing |
|----------|-------------|---------------|
| CLI -> Config Loader | Untrusted user config enters parsing/validation boundary | File paths and dataset parameters |
| Filesystem -> Ingestion Logic | Local image and annotation data enters matching pipeline | Metadata and annotation payloads |
| Preflight -> Dataset Write | Validation decision gates whether writes are allowed | Matched sample payloads |

---

## Threat Register

| Threat ID | Category | Component | Disposition | Mitigation | Status |
|-----------|----------|-----------|-------------|------------|--------|
| D-01 | Tampering | config_loader.py | mitigate | Enforce YAML-only extension gate (`.yaml`/`.yml`) | closed |
| D-02 | Tampering | config_model.py | mitigate | Reject non-local path schemes (`://`) | closed |
| D-03 | Tampering | config_model.py | mitigate | Resolve relative paths from config directory | closed |
| D-04 | Tampering | config_model.py | mitigate | Forbid unknown config fields (`extra=forbid`) | closed |
| D-05 | Integrity | matching.py/image_index.py | mitigate | Deterministic normalized basename matching | closed |
| D-06 | Integrity | matching.py/preflight.py | mitigate | Detect duplicate annotation keys as fatal preflight errors | closed |
| D-07 | Integrity | matching.py/preflight.py | mitigate | Aggregate unmatched annotations/images and fail after full report | closed |
| D-08 | Integrity | image_index.py | mitigate | Case-insensitive matching strategy | closed |
| D-09 | Tampering | run_import.py | mitigate | Block dataset writes until preflight passes | closed |
| D-10 | Integrity | run_import.py | mitigate | Aggregate malformed annotations and fail full run | closed |
| D-11 | Repudiation | run_import.py/cli.py/summary.py | mitigate | Always emit machine-readable summary on success/failure/exception | closed |
| D-12 | Repudiation | cli.py | mitigate | Strict exit code policy (0 success, non-zero failure) | closed |

*Status: open · closed*  
*Disposition: mitigate (implementation required) · accept (documented risk) · transfer (third-party)*

---

## Accepted Risks Log

No accepted risks.

---

## Security Audit Trail

| Audit Date | Threats Total | Closed | Open | Run By |
|------------|---------------|--------|------|--------|
| 2026-06-11 | 12 | 12 | 0 | gsd-security-auditor + orchestrator |

---

## Sign-Off

- [x] All threats have a disposition (mitigate / accept / transfer)
- [x] Accepted risks documented in Accepted Risks Log
- [x] `threats_open: 0` confirmed
- [x] `status: verified` set in frontmatter

**Approval:** verified 2026-06-11
