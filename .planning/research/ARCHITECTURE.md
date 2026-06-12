# Architecture Patterns

**Domain:** Local FiftyOne pose import + verification pipeline
**Researched:** 2026-06-12

## Recommended Architecture

Integrate verification as a **separate post-import pipeline package** under `src/fiftyone_pose_importer/verification/`, orchestrated by `run_import.py` but isolated from import parsing/matching logic.

Flow:
1. Existing import builds dataset + keypoint fields.
2. Verification runner reads imported samples and configured verification targets.
3. Per target: crop region -> deterministic checks -> optional VLM checks.
4. Reporter emits machine-readable artifact and summary linkage.

### Component Boundaries

| Component | Responsibility | Communicates With |
|-----------|---------------|-------------------|
| `config_model.py` (+ config_loader) | Parse/validate import + verification config | `run_import.py`, verification runner |
| `run_import.py` | Import orchestration + summary lifecycle | importer modules, verification facade |
| `verification/runner.py` (new) | Execute verification plan for dataset/samples | cropper, rules, vlm client, reporter |
| `verification/cropper.py` (new) | Build deterministic crop windows from keypoints/bboxes | runner |
| `verification/rules.py` (new) | Fast deterministic checks (missing points, geometry, visibility consistency) | runner |
| `verification/vlm_client.py` (new) | Optional model call behind stable interface | runner |
| `verification/report.py` (new) | Persist JSON report and aggregate counters | runner, `summary.py` |
| `cli.py` | Entry command + launch flag + output summary | `run_import.py` |
| `src/main.py` | Manual visualization/debug only (keep out of production pipeline) | FiftyOne app |

### Data Flow

`cli.py` -> `run_import(config)` -> existing import pipeline (datumaro reader, matching, contract validation, dataset write)
-> if `verification.enabled`: `verification.runner.run(dataset_name/config)`
-> crop candidates generated
-> deterministic checks run first
-> if enabled + eligible: VLM checks
-> `verification.report` writes `*.verification.json`
-> `summary.py` includes verification summary path + counters.

## Patterns to Follow

### Pattern 1: Facade + Pipeline Stages
**What:** Keep `run_import.py` as orchestrator; verification internals exposed as one facade function.
**When:** Any new verification logic (new rule sets, new model providers).
**Example:**
```python
result = run_verification(dataset=dataset, cfg=cfg.verification)
summary["verification"] = result.to_summary_dict()
```

### Pattern 2: Provider Interface for Optional VLM
**What:** `VLMClient` protocol with `verify(crop, prompt, context) -> verdict`.
**When:** Swapping OpenAI/local VLM/mock implementations.
**Example:**
```python
class VLMClient(Protocol):
    def verify(self, crop_path: Path, prompt: str, meta: dict) -> VLMResult: ...
```

## Anti-Patterns to Avoid

### Anti-Pattern 1: Mixing verification logic into import parsing loops
**What:** Running crop/rules/VLM directly inside annotation extraction loop in `run_import.py`.
**Why bad:** Couples concerns, hard to test, blocks future asynchronous execution.
**Instead:** Complete import first, then run verification stage.

### Anti-Pattern 2: Reusing `src/main.py` as pipeline runtime
**What:** Embedding production verification in ad-hoc visualization script.
**Why bad:** Script is monolithic/debug-oriented and bypasses config contracts.
**Instead:** Keep `main.py` for manual inspection only; all pipeline logic in package modules.

## New + Modified Interfaces

- **Config additions** (modify `ImportConfig`):
  - `verification.enabled: bool`
  - `verification.targets[]` (label/keypoint-field scope)
  - `verification.rules` (deterministic rule toggles/thresholds)
  - `verification.vlm` (enabled/provider/model/prompt_template)
  - `verification.output_path` (optional override)
- **Orchestrator hook** (modify `run_import`):
  - call `run_verification(...)` after dataset save, before final summary write.
- **Summary contract** (modify summary payload):
  - add `verification.counts`, `verification.failures`, `verification.report_path`.

## Build Order & Dependency Direction

1. **Define contracts first**
   - Extend config model + typed verification result schema.
2. **Implement deterministic core**
   - `cropper.py`, `rules.py`, `report.py` with no VLM dependency.
3. **Integrate orchestration**
   - `runner.py` + `run_import.py` hook + summary extension.
4. **Add VLM adapter last**
   - `vlm_client.py` behind interface; optional at runtime.
5. **CLI/doc updates and regression tests**
   - ensure import-only mode still passes.

Dependency rule: **CLI -> orchestrator -> verification facade -> (crop/rules/report) -> optional VLM adapter**. Lower layers must not import CLI or FiftyOne app launch code.

## Scalability Considerations

| Concern | At 100 users | At 10K users | At 1M users |
|---------|--------------|--------------|-------------|
| Verification runtime | synchronous local run | batch execution + sampling strategy | distributed workers + queued jobs |
| VLM cost/latency | verify all candidates | gate VLM by deterministic fail/suspicion score | aggressive prefilter + caching + budget caps |
| Report size | single JSON fine | chunked per run + index file | partitioned storage + warehouse ingestion |

## Sources

- `/src/fiftyone_pose_importer/run_import.py` (current orchestration and summary flow)
- `/src/fiftyone_pose_importer/config_model.py` + `config_loader.py` (config boundary)
- `/src/fiftyone_pose_importer/cli.py` (entrypoint boundary)
- `/src/main.py` (current monolithic visualization script, kept as non-pipeline)
- `/.planning/PROJECT.md` (v1.1 milestone intent)
