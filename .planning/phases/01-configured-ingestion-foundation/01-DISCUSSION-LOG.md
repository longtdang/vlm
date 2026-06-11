# Phase 1: Configured Ingestion Foundation - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves alternatives considered.

**Date:** 2026-06-11
**Phase:** 1-Configured Ingestion Foundation
**Areas discussed:** Config format and path rules, Image-annotation matching policy, Failure behavior

---

## Config format and path rules

| Option | Description | Selected |
|--------|-------------|----------|
| YAML only | Single clear format for v1 | ✓ |
| JSON only | Alternative single format | |
| Support both YAML and JSON | More flexibility, more parsing surface | |

**User's choice:** YAML only  
**Notes:** Local filesystem paths only, resolve relative paths from config directory, fail on unknown config fields.

---

## Image-annotation matching policy

| Option | Description | Selected |
|--------|-------------|----------|
| Basename stem match | Normalized stem used as primary key | ✓ |
| Exact relative path match | Stricter but brittle across exports | |
| Prefer annotation image.path + fallback | Mixed strategy | |

**User's choice:** Basename stem match  
**Notes:** Matching is case-insensitive. Duplicate matches are fatal. Unmatched entries are all reported, then import fails.

---

## Failure behavior

| Option | Description | Selected |
|--------|-------------|----------|
| Preflight validation | Validate before writes | ✓ |
| Validate during write | Validate while writing samples | |

**User's choice:** Strict failure mode  
**Notes:** Malformed keypoint samples fail the run after full report. JSON summary file is required. Exit code is non-zero for any failure.

---

## the agent's Discretion

None.

## Deferred Ideas

None.
