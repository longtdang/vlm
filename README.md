# FiftyOne Datumaro Importer

Use `config.example.yaml` to provide:

- `image_dir`: image folder path
- `datumaro_json`: Datumaro JSON path (CVAT export)
- `dataset_name`
- `label_field`

## Run importer

Recommended (installed console entrypoint):

```bash
pip install -e .
fiftyone-datumaro-import --config ./config.example.yaml --launch
```

Fallback (module invocation from repo root):

```bash
PYTHONPATH=src python -m fiftyone_pose_importer.cli --config ./config.example.yaml --launch
```

## Manual visibility verification quick path

1. Create a local verification config:
   ```bash
   cp config.example.yaml local.verify.yaml
   ```
2. Edit `local.verify.yaml` paths to point to your local image folder and Datumaro JSON.
3. Run importer with `--launch` and inspect keypoint metadata (`visibility`, `source_visibility`, `visibility_defaulted`).

## Troubleshooting

- `ModuleNotFoundError` when running `python -m ...` usually means the module path is wrong.
  - ✅ Use: `python -m fiftyone_pose_importer.cli`
  - ❌ Do not use: `python -m src/fiftyone_pose_importer.cli`
- `ModuleNotFoundError: No module named 'fiftyone'` means runtime dependency is missing.
  - Install project dependencies first (for editable install, ensure `pip install -e .` completed successfully in your active environment).
- If summary shows `preflight.schema_mismatches.ambiguous_skeleton`, import stops before writing samples.
  - This means skeleton labels/edges cannot be resolved to one canonical contract from the source data.
  - Fix by normalizing the source/categories skeleton definition or choosing a single canonical skeleton contract before rerun.
