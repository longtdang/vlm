# FiftyOne Datumaro Importer + Verification

This project provides commands for:
1. Importing Datumaro/CVAT pose data into FiftyOne
2. Running deterministic verification
3. Running optional VLM verification (model-zoo Qwen3-VL)

---

## Install

```bash
pip install -e .
```

Check commands:

```bash
fiftyone-datumaro-import --help
fiftyone-datumaro-verify --help
```

---

## Quick start (end-to-end)

1. Copy config template

   ```bash
   cp config.example.yaml local.verify.yaml
   ```

2. Edit `local.verify.yaml`
   - `image_dir`
   - `datumaro_json`
   - `dataset_name`
   - `label_field`

3. Import and launch FiftyOne

   ```bash
   fiftyone-datumaro-import --config ./local.verify.yaml --launch
   ```

4. Run verification pipeline

   ```bash
   fiftyone-datumaro-import verify --config ./local.verify.yaml
   ```

5. Open reports under `verification.output_dir` (default: `./verification-runs/<timestamp>/`)

---

## Config basics

`config.example.yaml` contains the base import fields:
- `image_dir`
- `datumaro_json`
- `dataset_name`
- `label_field`

Create your local config:

```bash
cp config.example.yaml local.verify.yaml
```

Then edit paths in `local.verify.yaml`.

Additional ready-to-copy samples:
- `config.import-only.example.yaml` (deterministic only)
- `config.import-vlm.example.yaml` (deterministic + VLM)

---

## Commands

### Command reference

| Purpose | Command |
|---|---|
| Import (legacy form) | `fiftyone-datumaro-import --config ./local.verify.yaml --launch` |
| Import (subcommand form) | `fiftyone-datumaro-import import --config ./local.verify.yaml --launch` |
| Verify via main CLI | `fiftyone-datumaro-import verify --config ./local.verify.yaml` |
| Verify via dedicated entrypoint | `fiftyone-datumaro-verify --config ./local.verify.yaml` |
| Import module fallback | `PYTHONPATH=src python -m fiftyone_pose_importer.cli import --config ./local.verify.yaml --launch` |
| Verify module fallback | `PYTHONPATH=src python -m fiftyone_pose_importer.run_verify --config ./local.verify.yaml` |

### 1) Import dataset

```bash
fiftyone-datumaro-import --config ./local.verify.yaml --launch
```

Equivalent subcommand form:

```bash
fiftyone-datumaro-import import --config ./local.verify.yaml --launch
```

Module fallback:

```bash
PYTHONPATH=src python -m fiftyone_pose_importer.cli import --config ./local.verify.yaml --launch
```

### 2) Run verification pipeline (deterministic + optional VLM)

Subcommand form:

```bash
fiftyone-datumaro-import verify --config ./local.verify.yaml
```

Dedicated entrypoint:

```bash
fiftyone-datumaro-verify --config ./local.verify.yaml
```

Module fallback:

```bash
PYTHONPATH=src python -m fiftyone_pose_importer.run_verify --config ./local.verify.yaml
```

---

## Verification pipeline behavior

### Deterministic stage

- Uses `verification.deterministic` rules
- Produces PASS/FAIL evidence per object
- Generates deterministic artifacts:
  - `deterministic_report.csv`
  - `deterministic_report.json`
  - `deterministic_trace.ndjson`

### VLM stage (optional)

- Enabled by `verification.vlm.enabled: true`
- Runs **after** deterministic stage
- Only runs on deterministic `PASS` objects and VLM-enabled labels
- Uses FiftyOne model-zoo Qwen3-VL models:
  - `qwen3-vl-2b-instruct-torch`
  - `qwen3-vl-4b-instruct-torch`
  - `qwen3-vl-8b-instruct-torch`
- Produces:
  - `vlm_report.csv`
  - `vlm_report.json` (includes `review_queue`)
  - `vlm_trace.ndjson`

---

## Verification config (example)

Add a `verification:` block in your YAML:

```yaml
verification:
  output_dir: ./verification-runs
  deterministic:
    padding_px: 16
    rules:
      global:
        detection: ["bbox_format"]
        attribute: ["required_attributes"]
        skeleton-count: ["keypoint_count"]
        visibility-format: ["visibility_codes"]
  vlm:
    enabled: true
    model_name: qwen3-vl-2b-instruct-torch
    thresholds:
      pass_below: 0.20
      review_below: 0.60
    generation:
      max_new_tokens: 256
      timeout_seconds: 8.0
    labels:
      forklift:
        enabled: true
        rules: ["bbox_localization", "bbox_coverage", "clamp_type"]
```

### `verification` keys explained

| Key | Type | Meaning |
|---|---|---|
| `verification.output_dir` | string | Root folder for timestamped verification runs |
| `verification.image_dir` | string (optional) | Alternate root for resolving relative image paths |
| `verification.run_timestamp` | string (optional) | Override timestamp folder name |
| `verification.deterministic.padding_px` | int | Fixed padding in pixels for crops |
| `verification.deterministic.rules.global` | object | Default deterministic rules for all labels |
| `verification.deterministic.rules.overrides.<label>` | object | Per-label deterministic rule overrides |
| `verification.vlm.enabled` | bool | Enable/disable VLM stage |
| `verification.vlm.model_name` | string | Model-zoo model id |
| `verification.vlm.thresholds.pass_below` | float | PASS threshold |
| `verification.vlm.thresholds.review_below` | float | REVIEW threshold (above this => FAIL) |
| `verification.vlm.generation.max_new_tokens` | int | Max generated tokens per VLM call |
| `verification.vlm.generation.timeout_seconds` | float | Timeout per VLM rule call |
| `verification.vlm.labels.<label>.enabled` | bool | Enable VLM for that label |
| `verification.vlm.labels.<label>.rules` | list | Rule subset for that label |
| `verification.vlm.labels.<label>.prompts.<rule>` | string | Per-label per-rule prompt override |

Notes:
- VLM is **model-zoo only** in this milestone (`qwen3-vl-{2b,4b,8b}-instruct-torch`)
- VLM runs only for deterministic `PASS` objects and VLM-enabled labels
- Outputs include deterministic and VLM artifacts under the same timestamped run directory

---

## Deterministic rules reference

Deterministic rules run on every annotation before the VLM stage. An annotation that fails **any** enabled rule is marked `FAIL` and excluded from VLM processing.

Rules are grouped into four categories. Each category key maps to a list of rule entries in the config.

### Category: `detection`

| Rule name | What it checks | Fail reason |
|-----------|---------------|-------------|
| `bbox_format` | Bounding box exists and is a list of 4 numbers. For non-bbox annotation types (`polygon`, `skeleton`, `points`) the bbox is derived automatically from the `points` coordinates. | `unevaluable:bbox_missing_or_malformed` |
| `bbox_non_empty` | Derived or explicit bounding box has width > 0 **and** height > 0 | `invalid_bbox` |

### Category: `attribute`

| Rule name | Params | What it checks | Fail reason |
|-----------|--------|---------------|-------------|
| `required_attributes` | `required: [<key>, ...]` | Every key listed in `params.required` exists in `annotation.attributes` | `missing_required_attribute:<key>` |
| `roll_count_positive` | — | `attributes.roll_count` exists, is numeric, and > 0 | `missing_roll_count` / `roll_count_non_positive` |
| `clamp_type_allowed` | `allowed: [<str>, ...]` (default: `["2-arm", "3-arm"]`) | `attributes.clamp_type` is one of the allowed values | `invalid_clamp_type:<value>` |

### Category: `skeleton-count`

| Rule name | Params | What it checks | Fail reason |
|-----------|--------|---------------|-------------|
| `keypoint_count` | `expected: <int>` (**required**) | Number of keypoints equals `params.expected` exactly | `keypoint_count_mismatch:<actual>!=<expected>` |

> **Tip:** Different skeleton types usually have different keypoint counts. Use `rules.overrides.<label>` to set per-label `expected` values, and set `skeleton-count: []` in `rules.global` to disable the global default.

### Category: `visibility-format`

| Rule name | What it checks | Fail reason |
|-----------|---------------|-------------|
| `visibility_codes` | Every entry in the visibility list is `0` (not labeled), `1` (occluded), or `2` (visible) — COCO convention | `invalid_visibility_codes` |

### Unevaluable rules

When a rule cannot be evaluated because prerequisite data is missing or malformed (e.g. `attributes` field is absent, `keypoint_count` has no `expected` param), the result is still recorded as `FAIL` with reason `unevaluable:<reason>`. This ensures silent skipping never hides a configuration error.

Common unevaluable reasons:

| Reason | Cause |
|--------|-------|
| `unevaluable:bbox_missing_or_malformed` | `bbox` absent and no `points` to derive it from |
| `unevaluable:attributes_missing_or_malformed` | Annotation has no `attributes` dict |
| `unevaluable:expected_keypoint_count_missing` | `keypoint_count` rule has no `params.expected` — set it per label using `rules.overrides` |
| `unevaluable:required_attribute_params_invalid` | `required_attributes` rule missing `params.required` list |
| `unevaluable:clamp_type_missing` | `attributes.clamp_type` is absent or not a string |

### How annotation types are handled

All Datumaro annotation types are supported. The bounding box used for cropping and the `bbox_format`/`bbox_non_empty` rules is derived as follows:

| Datumaro type | Bbox source | `is_skeleton` crop policy |
|---------------|-------------|--------------------------|
| `bbox` | `bbox` field directly | Skeleton canvas if keypoints present, tight crop otherwise |
| `polygon` | AABB of `points` pairs `[x,y, x,y, ...]` | Tight crop (not skeleton) |
| `skeleton` | AABB of `points` triples `[x,y,v, x,y,v, ...]` | Skeleton canvas (preserves spatial offset) |
| `points` | AABB of `points` pairs `[x,y, x,y, ...]` | Skeleton canvas |

### Example: mixed label types

```yaml
verification:
  deterministic:
    rules:
      global:
        detection: ["bbox_format"]
        attribute: ["required_attributes"]
        skeleton-count: []           # disabled globally; set per label below
        visibility-format: ["visibility_codes"]
      overrides:
        clamp-2-arm:
          skeleton-count:
            - name: keypoint_count
              params:
                expected: 12
        clamp-3-arm:
          skeleton-count:
            - name: keypoint_count
              params:
                expected: 16
        roll-keypoints:
          skeleton-count:
            - name: keypoint_count
              params:
                expected: 4
        clamp-mask:
          skeleton-count: []         # polygon — variable point count, skip check
```

---

## Output artifacts

- Import run summary: `<config_stem>.summary.json`
- Deterministic reports: `deterministic_report.csv/json`, `deterministic_trace.ndjson`
- VLM reports (when enabled): `vlm_report.csv/json`, `vlm_trace.ndjson`

Typical run directory:

```text
verification-runs/
  20260613T170000Z/
    crops/
    deterministic_report.csv
    deterministic_report.json
    deterministic_trace.ndjson
    vlm_report.csv
    vlm_report.json
    vlm_trace.ndjson
```

---

## Troubleshooting

- `ModuleNotFoundError` with `python -m`:
  - ✅ `python -m fiftyone_pose_importer.cli ...`
  - ✅ `python -m fiftyone_pose_importer.run_verify ...`
  - ❌ `python -m src/fiftyone_pose_importer...`
- `ModuleNotFoundError: No module named 'fiftyone'`:
  - Run `pip install -e .` in your active environment
- `preflight.schema_mismatches.ambiguous_skeleton`:
  - Import is blocked until the source skeleton contract is unambiguous
- Verify command exits non-zero:
  - Check printed JSON `error` and `summary_path`
  - Validate config paths and model name
