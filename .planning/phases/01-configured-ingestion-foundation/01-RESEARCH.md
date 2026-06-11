# Phase 1: Configured Ingestion Foundation - Research

**Researched:** 2026-06-11  
**Phase:** 1 - Configured Ingestion Foundation

## Locked Decisions to Preserve

- YAML-only config input.
- Local filesystem paths only.
- Relative paths resolved from config file directory.
- Unknown config fields are fatal validation errors.
- Matching by normalized basename stem, case-insensitive.
- Duplicate match is fatal.
- Report all mismatches, then fail when any mismatch exists.
- Preflight validation before writing dataset samples.
- Malformed keypoint records fail the whole run (with full report).
- JSON run summary must be written next to config.

## Recommended Implementation Approach

1. `load_config()` with `yaml.safe_load`.
2. `validate_config()` with strict Pydantic model (`extra=forbid`).
3. `resolve_paths()` against config file directory.
4. `index_images()` from configured image root.
5. `load_datumaro_items()` from configured Datumaro JSON source.
6. `build_match_report()` using normalized basename stem keys.
7. `preflight_gate()` (duplicates, mismatches, malformed inputs).
8. Only if preflight passes: create/write FiftyOne dataset entities.
9. Always emit JSON summary.

## Libraries

- `fiftyone` for dataset lifecycle and downstream rendering compatibility.
- `datumaro` for robust annotation parsing.
- `pydantic` for strict config schema and clear errors.
- `PyYAML` for safe YAML parsing.
- `typer` for a clear CLI entrypoint.

## Key Risks

- Path resolution bugs causing incorrect source discovery.
- Ambiguous image-item matching when filenames collide.
- Silent coercion/ignoring in config parsing.
- Partial writes before preflight completion.

## Validation Architecture

- Unit tests for config schema/path handling and unknown-field failures.
- Unit tests for deterministic matching, duplicate detection, mismatch reports.
- Integration tests for preflight fail/commit behavior and summary output.
- Gate: no dataset writes occur when preflight reports fatal issues.

## Open Questions

- None blocking for planning; scope and behavior are sufficiently locked for Phase 1 planning.

## RESEARCH COMPLETE

Phase research is complete and ready for planning.
