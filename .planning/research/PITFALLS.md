# Domain Pitfalls: VLM-based Verification in Deterministic Pose Import Pipelines

**Project:** FiftyOne Datumaro Pose Importer (milestone v1.1)
**Researched:** 2026-06-12
**Scope:** Adding configurable VLM annotation verification to an existing deterministic importer (preserve skeleton rendering for mixed skeleton types).

Summary
-------
This document catalogs concrete, actionable pitfalls that commonly occur when introducing Visual Language Model (VLM)–based verification to deterministic annotation import pipelines like this project's. For each pitfall we give root causes, consequences, and concrete prevention/mitigation steps tied to the codebase phases and architecture locations (preflight, import/normalization, verification stage, and post-processing/reporting).

High-risk (Critical) Pitfalls
----------------------------
1) Non-determinism leaking into the canonical import

- What goes wrong
  - VLM checks are inherently non-deterministic by design (random seeds, model temperature, backend versioning, asynchronous timeouts). If the importer uses VLM outputs to mutate or gate sample writes (e.g. changing visibility, discarding/accepting annotations) without capturing determinism metadata and fallbacks, repeated runs produce different dataset contents.

- Why it happens
  - VLM responses vary across calls; verification heuristics may include thresholds/tunable prompts that change over time; import code may apply VLM results in-place before producing a stable summary artifact.

- Consequences
  - Tests and downstream training are flaky; dataset drift between runs; lost ability to reproduce past verification decisions.

- Prevention (where to implement)
  - Phase: Verification stage and Post-processing/reporting
  - Architecture location: run_import.run_import (after sample construction, before dataset.add_samples) and the verification module entrypoint
  - Actionable steps:
    1. Make VLM verification opt-in and config-driven (cfg.verify.vlm.enabled) — default: disabled. (config_loader)
    2. Never mutate source annotations in-place as a side-effect of a VLM call. Treat VLM outputs as advisory until a deterministic commit step. (run_import)
    3. Record full verification trace for each sample: model name+version, prompt template hash, timestamp, input hash (image+annotation), VLM response, deterministic decision (pass/fail), and run_id. Store as separate machine-readable verification report artifact (JSON/NDJSON) and embed a small reference token in the Sample metadata (e.g. sample["verification_id"]). Implement in run_import immediately after keypoints list is finalized and before dataset.add_samples. (write_summary + verification module)
    4. Provide a deterministic post-verification commit step: CLI flags --replay-verification <path> and --apply-verification <run_id> to reproduce and optionally apply prior decisions deterministically. (CLI / config loader)
    5. Fix VLM random seeds where supported and log the seed; but do not assume this makes the model fully deterministic across versions/providers. Log model/provider metadata. (verification adapter)

2) Using VLM decisions to change skeleton contracts or default_skeleton selection at write-time

- What goes wrong
  - The importer currently sets dataset.default_skeleton when canonical_contract is present. If VLM recommends a different contract and import applies it without preflight validation, skeleton rendering can break or become inconsistent for mixed skeleton types (edges not matching label fields).

- Why it happens
  - Contract resolution and VLM verification are done in different concerns; VLM outputs are trusted to pick contracts post-hoc.

- Consequences
  - FiftyOne visualization shows wrong edges; different samples in the same dataset end up with incompatible skeleton metadata; preflight errors may be ignored and dataset becomes invalid for expected rendering.

- Prevention (where to implement)
  - Phase: Preflight & Import
  - Architecture location: extract_skeleton_contract_bundle, run_import canonical_contract selection, and dataset.skeletons/dataset.default_skeleton assignment
  - Actionable steps:
    1. Enforce that contract selection remains schema-driven and deterministic: only set dataset.default_skeleton when extract_skeleton_contract_bundle yields an unambiguous canonical contract (existing behavior). If VLM suggests alternative contract mapping, record suggestion but do NOT apply automatically; surface as a verification warning to be resolved by human (or a deterministic migration step). (pose_contract + reporting)
    2. If project requires automated contract normalization, implement a separate deterministic migration utility that uses VLM suggestions but requires an explicit config flag (cfg.migration.auto_apply: true) and writes a migration report and snapshotted pre-migration dataset. (migration tool)
    3. Add a preflight rule to detect samples that would render with mismatched skeleton field vs dataset.default_skeleton (report ambiguous_skeleton per README). Fail fast in import when ambiguity exists unless a migration flag is set. (preflight)

3) Visibility semantics mismatch and silent overwrites

- What goes wrong
  - VLM may suggest that some keypoints are occluded/absent/visible differently than source visibility field. If import code blindly overwrites visibility or fails to preserve source_visibility, then debugging and auditability are lost.

- Why it happens
  - Import pipeline already stores kp["visibility"], kp["source_visibility"] and kp["visibility_defaulted"] (see run_import._extract_points_and_visibility) but may be extended to accept VLM overrides without tracking provenance.

- Consequences
  - Loss of trust in data; inability to triage false positives/negatives from VLM; posterity of original annotation lost.

- Prevention (where to implement)
  - Phase: Import normalization and Verification
  - Architecture location: _extract_points_and_visibility, normalization code path, and the verification module
  - Actionable steps:
    1. Always preserve source data: keep kp["source_visibility"] exactly as-parsed, and only add kp["vlm_visibility_suggestion"] (or similar) when VLM runs. Do not overwrite kp["visibility"] unless reconciliation policy is explicit. (run_import)
    2. Do not overwrite kp["visibility"] used for rendering unless an explicit deterministic reconciliation policy is configured (cfg.verify.vlm.reconcile: ["prefer_source","prefer_vlm","human_review"]). If reconciliation changes visibility, emit a grouped change record in the verification report and tag sample with verification_id. (verification module + write_summary)
    3. Add UAT dataset fixture(s) that include all three visibility states so changes can be visually inspected. (tests / uat fixtures)

Moderate-risk Pitfalls
----------------------
4) Implicit assumptions about image size metadata

- What goes wrong
  - run_import relies on image metadata for width/height (image_meta), and raises SchemaContractError if missing. VLM verification may be run on crops that assume exact pixel coordinates; missing or swapped width/height results in wrong normalization leading VLM to give incorrect feedback.

- Why it happens
  - Source Datumaro JSON may omit image size or export it in [height,width] vs [width,height], and code already handles some fallbacks but VLM addition increases sensitivity.

- Consequences
  - False positives/negatives from VLM, bad coordinate normalization, corrupted keypoint coordinates in dataset.

- Prevention (where to implement)
  - Phase: Preflight & Normalization
  - Architecture location: build_image_index, run_import image size extraction, _normalize_points
  - Actionable steps:
    1. Enforce strict preflight validation that image size exists and is in expected format. If missing, compute size from the image file (cv2.imread) during preflight indexing (build_image_index) and write it to the image index cache. (image_index)
    2. Add assertive unit tests around normalization with swapped dims and missing dims cases. (tests)
    3. When building VLM crops, always compute crop in pixel-space from normalized coords and clamp to image bounds; log when normalization required defaulting. (verification module)

5) Rate-limits, latency, and synchronous blocking of deterministic pipeline

- What goes wrong
  - Synchronous calls to an external VLM provider during import can make the import slow or fail under rate limiting. Developers may be tempted to retry unboundedly or fail the entire import when a VLM request times out.

- Why it happens
  - VLM providers limit RPS and bandwidth; import is currently a blocking, single-process loop.

- Consequences
  - Long-running imports, partial dataset writes, surprise failures.

- Prevention (where to implement)
  - Phase: Verification (runtime behaviour)
  - Architecture location: verification executor (new module) invoked from run_import after sample construction
  - Actionable steps:
    1. Implement verification as a separate batched step that can be executed in parallel but with configurable concurrency and rate-limit (cfg.verify.vlm.concurrent_requests, cfg.verify.vlm.max_retries, cfg.verify.vlm.timeout_seconds). (verification executor)
    2. Provide a local-only fallback (cfg.verify.vlm.local_model) or an offline heuristics-only mode to keep pipeline deterministic. (verification adapter)
    3. Never block final dataset write permanently on optional VLM checks: write two artifacts — the dataset (source canonical annotations) and a verification report; mark samples as "verification_pending" or "verification_failed" instead of aborting write. Optionally provide a --fail-on-verification-error flag for strict runs. (run_import + write_summary)

6) Privacy / data exfiltration and regulatory leakage

- What goes wrong
  - Sending crops or full images to third-party VLMs may violate privacy or legal constraints if images contain PII or user data.

- Why it happens
  - VLM verification is often implemented quickly by posting image crops to hosted APIs. The project is local-first but configuration may permit cloud backends.

- Consequences
  - Compliance breach, data exposure, loss of trust.

- Prevention (where to implement)
  - Phase: Verification configuration & operations
  - Architecture location: config_loader, verification executor
  - Actionable steps:
    1. Add explicit privacy guard rails in config (cfg.verify.vlm.send_images: false by default). Explicit opt-in required to send image bytes to external services. (config_loader)
    2. Provide a local-only VLM adapter and a mock adapter for CI. Document providers and expected SLA/privacy trade-offs. (verification adapter)
    3. Implement an allow-list for fields and experiments allowed to use external VLM providers. (config + runtime checks)

Lower-risk / Operational Pitfalls
--------------------------------
7) Prompt-template drift and brittle heuristics

- What goes wrong
  - Verification depends on prompt templates and heuristic parsing of VLM output; small prompt changes or response-format changes break parsers.

- Prevention (where to implement)
  - Phase: Verification module + CI tests
  - Architecture location: verification adapter + prompt templating code
  - Actionable steps:
    1. Use a strict, machine-readable VLM output format (JSON schema) and validate responses against that schema (fail the single verification item gracefully, do not crash the import). (verification adapter)
    2. Version and hash prompt templates; store the prompt used with the verification trace. (verification adapter + write_summary)
    3. Add snapshot tests for expected VLM responses (use canned responses / offline mock in CI). (tests)

8) Mixing per-label keypoint fields improperly

- What goes wrong
  - The importer maps label_name -> field_name (main.py label_to_keypoint_field and run_import uses skeleton_labels / skeleton_edges on Keypoint). If VLM verification tries to normalize or merge fields across samples, it can break per-skeleton rendering (edges only connect when field names line up in FiftyOne).

- Prevention (where to implement)
  - Phase: Import mapping and Post-processing
  - Architecture location: datumaro_reader, pose_contract extraction, and anywhere VLM suggests field remapping
  - Actionable steps:
    1. Keep per-label keypoint fields stable and immutable for the dataset run. If VLM suggests collapsing two label fields into one canonical field, emit a migration plan (separate tool) rather than changing fields inline during import. (migration tooling)
    2. Ensure when writing Keypoints you set kp["skeleton_labels"] and kp["skeleton_edges"] explicitly (run_import currently does this). Continue to do so and do not rely solely on dataset.default_skeleton for mixed-contract rendering. (run_import)

9) Poor error visibility and aggregation for triage

- What goes wrong
  - VLM results are stored only in logs, not in a machine-readable summary; developers cannot triage which samples were affected or why.

- Prevention (where to implement)
  - Phase: Post-processing/reporting
  - Architecture location: write_summary + verification report writer
  - Actionable steps:
    1. Expand the summary JSON to include a verification block: counts by status {passed, failed, pending, error}, list of sample ids with error reasons, and verification artifact path. Include confidence scores if available. (write_summary)
    2. Produce a CSV/NDJSON per-run that is directly consumable by triage tooling. Wire write_summary to include a summary["verification"] path. (write_summary)

Checklist: Minimum Implementable Safeguards for v1.1
--------------------------------------------------
1. Config-driven opt-in for VLM, default off. (config_loader)
2. Verification runs produce an NDJSON/JSONL artifact with per-sample traces (model/version/prompt hash/input hash/response/decision). (verification module + write_summary)
3. Never mutate original visibility fields without explicit reconcile mode; instead add vlm suggestion metadata on the Keypoint object. (run_import)
4. Keep contract selection deterministic; do not apply VLM-driven contract rewrites during import. (pose_contract + run_import)
5. Add rate-limit/timeouts and a local fallback option. Do not block dataset write on optional checks. (verification executor configuration)
6. Add unit and snapshot tests for visibility states and a small canonical dataset fixture for UAT visual checks. (tests/)
7. Improve summary output to include verification counters and artifact paths. (summary.write_summary)

Sources and Evidence from Codebase
----------------------------------
- run_import._extract_points_and_visibility preserves source_visibility and records visibility_defaulted — use these fields to attach VLM suggestions rather than overwrite. (src/fiftyone_pose_importer/run_import.py)
- run_import currently sets dataset.default_skeleton when canonical_contract exists — avoid changing this from VLM results at import time. (src/fiftyone_pose_importer/run_import.py)
- README.md already warns about ambiguous_skeleton preflight stops; extend this with explicit migration guidance instead of automated VLM-based fixes. (README.md)

Open Questions / Further Research
--------------------------------
- Which VLM provider(s) will be accepted by default (local open-source vs cloud)? This changes privacy mitigations and reproducibility strategy.
- Do we need to support an auto-apply migration mode that uses VLM suggestions to rewrite an entire dataset? If yes, define strong safety checks and snapshots.

Last updated: 2026-06-12
