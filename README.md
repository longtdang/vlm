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
