# FiftyOne Datumaro Importer

Use `config.example.yaml` to provide:

- `image_dir`: image folder path
- `datumaro_json`: Datumaro JSON path (CVAT export)
- `dataset_name`
- `label_field`

Run:

```bash
pip install -e .
fiftyone-datumaro-import --config ./config.example.yaml --launch
```
