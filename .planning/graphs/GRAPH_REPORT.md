# Graph Report - vlm  (2026-06-14)

## Corpus Check
- 111 files · ~74,562 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 1170 nodes · 1923 edges · 87 communities (80 shown, 7 thin omitted)
- Extraction: 85% EXTRACTED · 15% INFERRED · 0% AMBIGUOUS · INFERRED: 284 edges (avg confidence: 0.6)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `21dd30fd`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- [[_COMMUNITY_Community 0|Community 0]]
- [[_COMMUNITY_Community 1|Community 1]]
- [[_COMMUNITY_Community 2|Community 2]]
- [[_COMMUNITY_Community 3|Community 3]]
- [[_COMMUNITY_Community 4|Community 4]]
- [[_COMMUNITY_Community 5|Community 5]]
- [[_COMMUNITY_Community 6|Community 6]]
- [[_COMMUNITY_Community 7|Community 7]]
- [[_COMMUNITY_Community 8|Community 8]]
- [[_COMMUNITY_Community 9|Community 9]]
- [[_COMMUNITY_Community 10|Community 10]]
- [[_COMMUNITY_Community 11|Community 11]]
- [[_COMMUNITY_Community 12|Community 12]]
- [[_COMMUNITY_Community 13|Community 13]]
- [[_COMMUNITY_Community 14|Community 14]]
- [[_COMMUNITY_Community 15|Community 15]]
- [[_COMMUNITY_Community 16|Community 16]]
- [[_COMMUNITY_Community 17|Community 17]]
- [[_COMMUNITY_Community 18|Community 18]]
- [[_COMMUNITY_Community 19|Community 19]]
- [[_COMMUNITY_Community 20|Community 20]]
- [[_COMMUNITY_Community 21|Community 21]]
- [[_COMMUNITY_Community 22|Community 22]]
- [[_COMMUNITY_Community 23|Community 23]]
- [[_COMMUNITY_Community 24|Community 24]]
- [[_COMMUNITY_Community 25|Community 25]]
- [[_COMMUNITY_Community 26|Community 26]]
- [[_COMMUNITY_Community 27|Community 27]]
- [[_COMMUNITY_Community 28|Community 28]]
- [[_COMMUNITY_Community 29|Community 29]]
- [[_COMMUNITY_Community 30|Community 30]]
- [[_COMMUNITY_Community 31|Community 31]]
- [[_COMMUNITY_Community 32|Community 32]]
- [[_COMMUNITY_Community 33|Community 33]]
- [[_COMMUNITY_Community 34|Community 34]]
- [[_COMMUNITY_Community 35|Community 35]]
- [[_COMMUNITY_Community 36|Community 36]]
- [[_COMMUNITY_Community 37|Community 37]]
- [[_COMMUNITY_Community 38|Community 38]]
- [[_COMMUNITY_Community 39|Community 39]]
- [[_COMMUNITY_Community 40|Community 40]]
- [[_COMMUNITY_Community 41|Community 41]]
- [[_COMMUNITY_Community 42|Community 42]]
- [[_COMMUNITY_Community 43|Community 43]]
- [[_COMMUNITY_Community 44|Community 44]]
- [[_COMMUNITY_Community 45|Community 45]]
- [[_COMMUNITY_Community 46|Community 46]]
- [[_COMMUNITY_Community 47|Community 47]]
- [[_COMMUNITY_Community 48|Community 48]]
- [[_COMMUNITY_Community 49|Community 49]]
- [[_COMMUNITY_Community 50|Community 50]]
- [[_COMMUNITY_Community 51|Community 51]]
- [[_COMMUNITY_Community 52|Community 52]]
- [[_COMMUNITY_Community 53|Community 53]]
- [[_COMMUNITY_Community 54|Community 54]]
- [[_COMMUNITY_Community 55|Community 55]]
- [[_COMMUNITY_Community 56|Community 56]]
- [[_COMMUNITY_Community 57|Community 57]]
- [[_COMMUNITY_Community 58|Community 58]]
- [[_COMMUNITY_Community 59|Community 59]]
- [[_COMMUNITY_Community 60|Community 60]]
- [[_COMMUNITY_Community 61|Community 61]]
- [[_COMMUNITY_Community 62|Community 62]]
- [[_COMMUNITY_Community 63|Community 63]]
- [[_COMMUNITY_Community 64|Community 64]]
- [[_COMMUNITY_Community 65|Community 65]]
- [[_COMMUNITY_Community 66|Community 66]]
- [[_COMMUNITY_Community 67|Community 67]]
- [[_COMMUNITY_Community 68|Community 68]]
- [[_COMMUNITY_Community 69|Community 69]]
- [[_COMMUNITY_Community 70|Community 70]]
- [[_COMMUNITY_Community 71|Community 71]]
- [[_COMMUNITY_Community 72|Community 72]]
- [[_COMMUNITY_Community 73|Community 73]]
- [[_COMMUNITY_Community 74|Community 74]]
- [[_COMMUNITY_Community 75|Community 75]]
- [[_COMMUNITY_Community 76|Community 76]]
- [[_COMMUNITY_Community 77|Community 77]]
- [[_COMMUNITY_Community 78|Community 78]]
- [[_COMMUNITY_Community 79|Community 79]]

## God Nodes (most connected - your core abstractions)
1. `run_verify()` - 50 edges
2. `ObjectVerificationResult` - 38 edges
3. `VlmVerdict` - 29 edges
4. `DeterministicVerdict` - 28 edges
5. `MockVlmAdapter` - 25 edges
6. `evaluate_vlm_object()` - 23 edges
7. `run_import()` - 22 edges
8. `RuleSpec` - 22 edges
9. `Phase 7: VLM Verification & Aggregation - Research` - 22 edges
10. `load_vlm_config()` - 21 edges

## Surprising Connections (you probably didn't know these)
- `test_padding_px_is_consumed_from_config()` --calls--> `load_verification_config()`  [INFERRED]
  tests/phase6/test_cropper.py → src/fiftyone_pose_importer/verification/config.py
- `test_defaults_and_label_override_merge()` --calls--> `load_verification_config()`  [INFERRED]
  tests/phase6/test_verification_config.py → src/fiftyone_pose_importer/verification/config.py
- `test_invalid_padding_fails_fast()` --calls--> `load_verification_config()`  [INFERRED]
  tests/phase6/test_verification_config.py → src/fiftyone_pose_importer/verification/config.py
- `test_required_categories_exist_by_default()` --calls--> `load_verification_config()`  [INFERRED]
  tests/phase6/test_verification_config.py → src/fiftyone_pose_importer/verification/config.py
- `test_unknown_rule_is_warning_not_error()` --calls--> `load_verification_config()`  [INFERRED]
  tests/phase6/test_verification_config.py → src/fiftyone_pose_importer/verification/config.py

## Import Cycles
- None detected.

## Communities (87 total, 7 thin omitted)

### Community 0 - "Community 0"
Cohesion: 0.10
Nodes (57): BaseException, DeterministicRuleConfig, Enum, test_any_failed_rule_forces_object_fail(), test_per_label_override_rules_are_applied(), test_unevaluable_rule_is_converted_to_explicit_fail_reason(), test_unknown_rule_names_are_warning_only_and_skipped(), _valid_annotation() (+49 more)

### Community 1 - "Community 1"
Cohesion: 0.07
Nodes (66): _crop_output_path(), _derive_bbox_from_annotation(), _failure_result(), _image_size(), _is_within(), _label_lookup(), _load_raw_config(), main() (+58 more)

### Community 2 - "Community 2"
Cohesion: 0.08
Nodes (63): test_load_vlm_config_default_prompt_template_override(), test_load_vlm_config_defaults(), test_load_vlm_config_invalid_thresholds_raises(), test_load_vlm_config_per_label_enabled_flag(), test_load_vlm_config_per_label_prompt_override(), test_load_vlm_config_per_label_rules(), test_load_vlm_config_per_label_threshold_override(), test_load_vlm_config_raises_on_missing_model_name() (+55 more)

### Community 3 - "Community 3"
Cohesion: 0.09
Nodes (49): Dataset, main(), _main_legacy_import(), _main_with_subcommands(), _run_import_command(), _run_verify_command(), load_datumaro(), parse_keypoints_and_visibility() (+41 more)

### Community 4 - "Community 4"
Cohesion: 0.04
Nodes (48): Alternatives Considered, Anti-Patterns to Avoid, Applicable ASVS Categories, Architectural Responsibility Map, Architecture Patterns, Assumptions Log, Claude's Discretion, Code Examples (+40 more)

### Community 5 - "Community 5"
Cohesion: 0.05
Nodes (41): Alternatives Considered, Anti-Patterns to Avoid, Applicable ASVS Categories, Architectural Responsibility Map, Architecture Patterns, Assumptions Log, Claude's Discretion, Code Examples (+33 more)

### Community 6 - "Community 6"
Cohesion: 0.12
Nodes (28): Exception, test_deterministic_fail_objects_excluded_from_vlm(), test_label_not_in_vlm_scope_excluded(), test_review_queue_in_vlm_json_is_ordered(), test_vlm_artifacts_in_same_run_dir_as_deterministic(), test_vlm_counts_in_summary(), test_vlm_disabled_produces_no_vlm_artifacts(), test_vlm_high_ep_produces_fail_verdict() (+20 more)

### Community 7 - "Community 7"
Cohesion: 0.07
Nodes (29): All Results Buffered in Memory Before Writing Reports, Bare `assert` Statements in Production Control Flow, Codebase Concerns, Critical Issues, Dependency Risks, Duplicate Keypoint/Visibility Extraction Logic, `fiftyone>=1.0.0` — No Upper Bound, Private API Dependency, Fragile `is_skeleton` Heuristic (+21 more)

### Community 8 - "Community 8"
Cohesion: 0.13
Nodes (17): dict, _Dataset, _install_fake_fiftyone(), _Keypoint, _Keypoints, _KeypointSkeleton, _load_run_import_module(), _multi_skeleton_payload() (+9 more)

### Community 9 - "Community 9"
Cohesion: 0.08
Nodes (23): 1) Import dataset, 2) Run verification pipeline (deterministic + optional VLM), Category: `attribute`, Category: `detection`, Category: `skeleton-count`, Category: `visibility-format`, Command reference, Commands (+15 more)

### Community 10 - "Community 10"
Cohesion: 0.09
Nodes (22): Adapter strategy, Artifacts, Canonical References, Deferred Ideas, Established Patterns, Existing Code Insights, Implementation Decisions, Integration Points (+14 more)

### Community 11 - "Community 11"
Cohesion: 0.10
Nodes (42): _object_results(), test_csv_json_ndjson_emitted_with_required_columns(), test_json_ndjson_schema_and_order(), _make_vlm_result(), test_review_queue_adapter_failure_first(), test_serialize_vlm_object_result_has_all_keys(), test_serialize_vlm_object_result_review_failure_reason(), test_vlm_csv_has_correct_header() (+34 more)

### Community 12 - "Community 12"
Cohesion: 0.11
Nodes (18): Canonical References, Crop policy and edge handling, Deferred Ideas, Deterministic verdict policy, Established Patterns, Existing Code Insights, Implementation Decisions, Integration Points (+10 more)

### Community 13 - "Community 13"
Cohesion: 0.11
Nodes (17): Canonical References, Deferred Ideas, Established Patterns, Existing Code Insights, Field identity contract, Implementation Decisions, Import mapping behavior, Integration Points (+9 more)

### Community 14 - "Community 14"
Cohesion: 0.12
Nodes (15): Architectural Responsibility Map, Assumptions Log, Don't Hand-Roll, Environment Availability, FiftyOne Zoo VLM Inference — Key API Facts, Metadata, Open Questions (RESOLVED), Package Legitimacy Audit (+7 more)

### Community 15 - "Community 15"
Cohesion: 0.13
Nodes (14): Accomplishments, Auth Gates, Auto-fixed Issues, Decisions Made, Deviations from Plan, Files Created/Modified, Issues Encountered, Known Stubs (+6 more)

### Community 16 - "Community 16"
Cohesion: 0.13
Nodes (14): Active, Constraints, Context, Core Value, Current Milestone: v1.1 Skeleton Field Rendering + Configurable VLM Verification, Current State, Evolution, FiftyOne Datumaro Pose Importer (+6 more)

### Community 17 - "Community 17"
Cohesion: 0.13
Nodes (14): Anti-Pattern 1: Mixing verification logic into import parsing loops, Anti-Pattern 2: Reusing `src/main.py` as pipeline runtime, Anti-Patterns to Avoid, Architecture Patterns, Build Order & Dependency Direction, Component Boundaries, Data Flow, New + Modified Interfaces (+6 more)

### Community 18 - "Community 18"
Cohesion: 0.14
Nodes (13): Accomplishments, Auth Gates, Auto-fixed Issues, Decisions Made, Deviations from Plan, Files Created/Modified, Issues Encountered, Known Stubs (+5 more)

### Community 19 - "Community 19"
Cohesion: 0.14
Nodes (13): 1) Real FiftyOne dataset existence check, 2) Per-field skeleton edge rendering in viewer, 3) Visibility semantics in viewer, Anti-Patterns Found, Behavioral Spot-Checks, Data-Flow Trace (Level 4), Human Verification Required, Key Link Verification (+5 more)

### Community 20 - "Community 20"
Cohesion: 0.14
Nodes (13): Accomplishments, Auto-fixed Issues, Decisions Made, Deviations from Plan, Files Created/Modified, Issues Encountered, Known Stubs, Next Phase Readiness (+5 more)

### Community 21 - "Community 21"
Cohesion: 0.14
Nodes (13): Accomplishments, Auto-fixed Issues, Decisions Made, Deviations from Plan, Files Created/Modified, Issues Encountered, Known Stubs, Next Phase Readiness (+5 more)

### Community 22 - "Community 22"
Cohesion: 0.14
Nodes (13): Accomplishments, Auto-fixed Issues, Decisions Made, Deviations from Plan, Files Created/Modified, Issues Encountered, Known Stubs, Next Phase Readiness (+5 more)

### Community 23 - "Community 23"
Cohesion: 0.14
Nodes (13): Anti-Patterns, Architectural Constraints, Architecture, Components, Cross-Cutting Concerns, Data Flow, Entry Points, Error Handling (+5 more)

### Community 24 - "Community 24"
Cohesion: 0.14
Nodes (13): Auth & Identity, CI/CD & Deployment, Databases & Storage, Datumaro JSON Format (CVAT export), Environment Configuration, External Services, FiftyOne Dataset Management, FiftyOne Local MongoDB (+5 more)

### Community 25 - "Community 25"
Cohesion: 0.14
Nodes (13): Assertion Style, conftest.py, Coverage, Error Assertion Pattern, Helper Factory Functions (not pytest fixtures), Integration Test Setup Pattern, Mocking Strategy, Return Type Annotations on Tests (+5 more)

### Community 26 - "Community 26"
Cohesion: 0.33
Nodes (9): ConfigLoadError, load_config(), ImportConfig, ImportConfigError, ResolvedConfig, ResolvedConfig, Path, ResolvedConfig (+1 more)

### Community 27 - "Community 27"
Cohesion: 0.15
Nodes (12): Actionable Recommendations (short), Confidence Assessment, Executive Summary, From ARCHITECTURE.md, From FEATURES.md, From PITFALLS.md, From STACK.md, Implications for Roadmap (phased suggestions) (+4 more)

### Community 28 - "Community 28"
Cohesion: 0.17
Nodes (11): Accomplishments, Decisions Made, Deviations from Plan, Files Created/Modified, Issues Encountered, Next Phase Readiness, Performance, Phase 6 Plan 2: Deterministic Cropper and Rules Engine Summary (+3 more)

### Community 29 - "Community 29"
Cohesion: 0.17
Nodes (11): Accomplishments, Decisions Made, Deviations from Plan, Files Created/Modified, Issues Encountered, Next Phase Readiness, Performance, Phase 6 Plan 3: Deterministic Reporting Writers Summary (+3 more)

### Community 30 - "Community 30"
Cohesion: 0.17
Nodes (11): Conclusions, Deviations from Plan, Files Created/Modified, Issues Encountered, Known Stubs, Phase 06 Plan 05: Gap-closure — Real Crop Materialization Summary, Self-Check: PASSED, Task Commits (as found in repo) (+3 more)

### Community 31 - "Community 31"
Cohesion: 0.17
Nodes (11): Architecture, Avoid, Constraints, Conventions, Critical mapping contract, Developer Profile, GSD Workflow Enforcement, Project (+3 more)

### Community 32 - "Community 32"
Cohesion: 0.38
Nodes (11): _base_data(), _install_fake_fiftyone(), _load_run_import_module(), test_canonical_mapping_contract_padding(), test_multi_skeleton_dataset_imports_without_global_ambiguity_failure(), test_preflight_failfast_and_deterministic_pose_order(), test_skeleton_labels_edges_applied(), test_visibility_fidelity_mapping() (+3 more)

### Community 33 - "Community 33"
Cohesion: 0.17
Nodes (11): Architecture, Configuration Sketch, Crop Logic (mandatory for VLM path), Data Flow, Error Handling, Goal, Scope, Success Criteria (+3 more)

### Community 34 - "Community 34"
Cohesion: 0.18
Nodes (10): Accomplishments, Auth Gates, Auto-fixed Issues, Deviations from Plan, Known Stubs, Performance, Phase 5 Plan 02: Contracts & Preflight Summary, Self-Check: PASSED (+2 more)

### Community 35 - "Community 35"
Cohesion: 0.18
Nodes (10): Accomplishments, Decisions Made, Deviations from Plan, Files Created/Modified, Issues Encountered, Next Phase Readiness, Performance, Phase 6 Plan 1: Deterministic Verification Contracts Summary (+2 more)

### Community 36 - "Community 36"
Cohesion: 0.18
Nodes (10): Accomplishments, Deviations from Plan, Files Created/Modified, Issues Encountered, Known Stubs, Performance, Phase 6 Plan 4: Deterministic Runner + CLI Exit Semantics Summary, Self-Check: PASSED (+2 more)

### Community 37 - "Community 37"
Cohesion: 0.18
Nodes (10): Area 1: VLM Adapter Strategy, Area 2: VLM Label Scope, Area 3: VLM Execution Gate, Area 4: Prompt and Response Contract, Area 5: Risk Aggregation and Thresholds, Area 6: Phase 7 Artifacts and Review Queue, Area 7: CI/Testing Strategy, Deferred / Out of Scope (+2 more)

### Community 38 - "Community 38"
Cohesion: 0.44
Nodes (10): _base_data(), _configure(), _install_fake_fiftyone(), _load_run_import_module(), test_cli_launch_wiring(), test_launch_preflight_guard(), test_launch_preserves_connected_skeleton_contract(), test_launch_status_reporting() (+2 more)

### Community 39 - "Community 39"
Cohesion: 0.20
Nodes (9): Anti-Patterns and Debt Scan, Behavioral Spot-Checks, Gaps Summary, Human Verification Required, Observable Truths (Roadmap Success Criteria), Phase 06 Re-Verification Report, Re-verification Details (focused checks for previously failed items), Requirements Coverage (re-checked) (+1 more)

### Community 40 - "Community 40"
Cohesion: 0.20
Nodes (10): Anti-Patterns to Avoid, Architecture Patterns, Pattern 1: VLM Adapter Protocol (duck-type for CI mock), Pattern 2: VLM Response Parsing with `invalid_output` Guard, Pattern 3: VLM Config Loading (mirrors `config.py` exactly), Pattern 4: Integration Point in `run_verify.py`, Pattern 5: VLM Types (parallel to `types.py`), Pattern 6: Review Queue Ordering (D-21) (+2 more)

### Community 41 - "Community 41"
Cohesion: 0.20
Nodes (9): Notes, Phase 5: Contracts & Preflight, Phase 6: Deterministic Verification Core & Reporting, Phase 7: VLM Verification & Aggregation, Phase Details, Phases, Progress Table, ROADMAP: Milestone v1.1 — Skeleton Field Rendering + Configurable VLM Verification (+1 more)

### Community 42 - "Community 42"
Cohesion: 0.22
Nodes (8): Codebase Structure, Generated/Build Artifacts, Key Files, Module Breakdown, Naming Conventions, Special Directories, Top-Level Layout, Where to Add New Code

### Community 43 - "Community 43"
Cohesion: 0.22
Nodes (8): Milestone Summary, Milestone v1.0: milestone, Overview, Phase 01: Configured Ingestion Foundation, Phase 02: Pose Contract Mapping, Phase 03: Visibility Fidelity, Phase 04: FiftyOne Viewing and Run Reporting, Phases

### Community 44 - "Community 44"
Cohesion: 0.47
Nodes (8): _base_data(), _configure(), _install_fake_fiftyone(), _load_run_import_module(), test_summary_additive_schema(), test_summary_path_contract_success_and_failure(), test_warning_failure_rollups(), ModuleType

### Community 45 - "Community 45"
Cohesion: 0.22
Nodes (8): Deterministic Verification Core, Future Requirements (Deferred), Milestone Requirements: v1.1, Out of Scope (v1.1), Skeleton Rendering Foundation, Traceability, v1.1 Requirements, VLM Verification

### Community 46 - "Community 46"
Cohesion: 0.22
Nodes (8): File Structure, Spec Coverage Check, Task 1: Add verification config and CLI entry, Task 2: Implement cropper (tight bbox + fixed padding), Task 3: Add class rule parser + deterministic checks, Task 4: Add VLM adapter, routing, and decision combiner, Task 5: Add report export and end-to-end verify runner integration, VLM Annotation Verification Implementation Plan

### Community 47 - "Community 47"
Cohesion: 0.22
Nodes (8): Add (minimal), Architecture-Level Integration (code), Dependency Update (pyproject.toml), Explicitly NOT Add in v1.1 (scope control), Keep (already in project), Recommended Stack Changes for v1.1, Sources, Technology Stack

### Community 48 - "Community 48"
Cohesion: 0.25
Nodes (7): Manual-Only Verifications, Per-Task Verification Map, Phase 05 — Validation Strategy, Sampling Rate, Test Infrastructure, Validation Sign-Off, Wave 0 Requirements

### Community 49 - "Community 49"
Cohesion: 0.25
Nodes (7): Crop policy and edge handling, Deferred Ideas, Deterministic verdict policy, Phase 6: Deterministic Verification Core & Reporting - Discussion Log, Report schema and output files, Rule config shape per label/class, the agent's Discretion

### Community 50 - "Community 50"
Cohesion: 0.25
Nodes (7): Manual-Only Verifications, Per-Task Verification Map, Phase 06 — Validation Strategy, Sampling Rate, Test Infrastructure, Validation Sign-Off, Wave 0 Requirements

### Community 51 - "Community 51"
Cohesion: 0.25
Nodes (7): Core Frameworks & Libraries, Dev Tools, Infrastructure & Deployment, Languages, Runtimes & Package Managers, Tech Stack, VLM Model Support

### Community 52 - "Community 52"
Cohesion: 0.25
Nodes (7): Anti-Features, Differentiators, Feature Dependencies, Feature Landscape, MVP Recommendation, Sources, Table Stakes

### Community 53 - "Community 53"
Cohesion: 0.29
Nodes (6): Deferred Ideas, Field identity contract, Mapping metadata entry schema, Phase 5: Contracts & Preflight - Discussion Log, the agent's Discretion, Visibility preflight policy

### Community 54 - "Community 54"
Cohesion: 0.29
Nodes (7): Common Pitfalls, Pitfall 1: Qwen3-VL returns JSON wrapped in markdown fences, Pitfall 2: `model.predict()` returns `Detections`, not a string, Pitfall 3: FiftyOne zoo model downloads weights on first call, Pitfall 4: `error_probability=0` (integer) parsed as `invalid_output`, Pitfall 5: `model.config.prompt` mutation is not thread-safe, Pitfall 6: VLM artifacts written to wrong directory

### Community 55 - "Community 55"
Cohesion: 0.29
Nodes (6): Per-Task Verification Map, Phase 07 — Validation Strategy, Sampling Rate, Test Infrastructure, Validation Sign-Off, Wave 0 Requirements

### Community 56 - "Community 56"
Cohesion: 0.29
Nodes (6): Artifacts Verified, Observable Truths, Phase 7: VLM Verification & Aggregation Verification Report, Requirements Coverage, Summary, Verification Evidence

### Community 57 - "Community 57"
Cohesion: 0.29
Nodes (6): Anti-Patterns Observed, Code Style, Coding Conventions, Documentation Style, Naming Conventions, Patterns in Use

### Community 58 - "Community 58"
Cohesion: 0.29
Nodes (6): Current Focus, Debug Session: report-format-ann-id-only, Eliminated, Evidence, Resolution, Symptoms

### Community 59 - "Community 59"
Cohesion: 0.33
Nodes (5): Accumulated Context, Current Position, Next Actions, Project Reference, Project State

### Community 60 - "Community 60"
Cohesion: 0.33
Nodes (5): Cross-Phase Issues, Milestone Audit — v1.0, Nyquist Coverage, Summary, Unsatisfied Requirements

### Community 61 - "Community 61"
Cohesion: 0.40
Nodes (5): Phase Requirements → Test Map, Sampling Rate, Test Framework, Validation Architecture, Wave 0 Gaps

### Community 62 - "Community 62"
Cohesion: 0.50
Nodes (3): Artifacts this phase produces, STRIDE Threat Register, Trust Boundaries

### Community 63 - "Community 63"
Cohesion: 0.50
Nodes (3): Artifacts this phase produces, STRIDE Threat Register, Trust Boundaries

### Community 64 - "Community 64"
Cohesion: 0.50
Nodes (3): Artifacts this phase produces, STRIDE Threat Register, Trust Boundaries

### Community 65 - "Community 65"
Cohesion: 0.50
Nodes (3): Artifacts This Phase Produces, STRIDE Threat Register, Trust Boundaries

### Community 66 - "Community 66"
Cohesion: 0.50
Nodes (3): Artifacts This Phase Produces, STRIDE Threat Register, Trust Boundaries

### Community 67 - "Community 67"
Cohesion: 0.50
Nodes (3): Artifacts This Phase Produces, STRIDE Threat Register, Trust Boundaries

### Community 68 - "Community 68"
Cohesion: 0.50
Nodes (4): Alternatives Considered, Core, Standard Stack, Supporting

### Community 69 - "Community 69"
Cohesion: 0.50
Nodes (4): Claude's Discretion, Deferred Ideas (OUT OF SCOPE), Locked Decisions, User Constraints (from CONTEXT.md)

### Community 70 - "Community 70"
Cohesion: 0.50
Nodes (4): Code Examples, Loading and calling a zoo VLM for raw text (verified against live FiftyOne 1.17 source), Model requirements (verified from zoo model info), Zoo model names (verified against installed FiftyOne 1.17)

### Community 71 - "Community 71"
Cohesion: 0.50
Nodes (3): Requirements Archive: v1.0, v1 Requirement Outcomes, Validation References

### Community 73 - "Community 73"
Cohesion: 0.67
Nodes (3): Primary (HIGH confidence), Secondary (matches locked CONTEXT.md decisions), Sources

## Knowledge Gaps
- **562 isolated node(s):** `ResolvedConfig`, `Path`, `Path`, `ObjectVerificationResult`, `Path` (+557 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **7 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `run_verify()` connect `Community 1` to `Community 0`, `Community 2`, `Community 3`, `Community 6`, `Community 11`?**
  _High betweenness centrality (0.028) - this node is a cross-community bridge._
- **Why does `DeterministicVerdict` connect `Community 0` to `Community 1`?**
  _High betweenness centrality (0.010) - this node is a cross-community bridge._
- **Why does `ObjectVerificationResult` connect `Community 0` to `Community 1`, `Community 2`, `Community 11`?**
  _High betweenness centrality (0.010) - this node is a cross-community bridge._
- **Are the 28 inferred relationships involving `ObjectVerificationResult` (e.g. with `BaseException` and `Any`) actually correct?**
  _`ObjectVerificationResult` has 28 INFERRED edges - model-reasoned connections that need verification._
- **Are the 22 inferred relationships involving `VlmVerdict` (e.g. with `Any` and `Path`) actually correct?**
  _`VlmVerdict` has 22 INFERRED edges - model-reasoned connections that need verification._
- **Are the 20 inferred relationships involving `DeterministicVerdict` (e.g. with `RuleResult` and `Any`) actually correct?**
  _`DeterministicVerdict` has 20 INFERRED edges - model-reasoned connections that need verification._
- **Are the 20 inferred relationships involving `MockVlmAdapter` (e.g. with `test_deterministic_fail_objects_excluded_from_vlm()` and `test_label_not_in_vlm_scope_excluded()`) actually correct?**
  _`MockVlmAdapter` has 20 INFERRED edges - model-reasoned connections that need verification._