# FiftyOne Datumaro Importer + Verification

This project provides commands for:
1. Importing Datumaro/CVAT pose data into FiftyOne
2. Running deterministic verification
3. Running optional VLM verification (model-zoo Qwen3-VL)

## Install

```bash
pip install -e .
```

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

## Commands

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

Notes:
- VLM is **model-zoo only** in this milestone (`qwen3-vl-{2b,4b,8b}-instruct-torch`)
- VLM runs only for deterministic `PASS` objects and VLM-enabled labels
- Outputs include deterministic and VLM artifacts under the same timestamped run directory

## Output artifacts

- Import run summary: `<config_stem>.summary.json`
- Deterministic reports: `deterministic_report.csv/json`, `deterministic_trace.ndjson`
- VLM reports (when enabled): `vlm_report.csv/json`, `vlm_trace.ndjson`

## Troubleshooting

- `ModuleNotFoundError` with `python -m`:
  - ✅ `python -m fiftyone_pose_importer.cli ...`
  - ✅ `python -m fiftyone_pose_importer.run_verify ...`
  - ❌ `python -m src/fiftyone_pose_importer...`
- `ModuleNotFoundError: No module named 'fiftyone'`:
  - Run `pip install -e .` in your active environment
- `preflight.schema_mismatches.ambiguous_skeleton`:
  - Import is blocked until the source skeleton contract is unambiguous
