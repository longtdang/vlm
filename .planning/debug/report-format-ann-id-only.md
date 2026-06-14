---
status: resolved
trigger: "/gsd-debug in every repose (csv or json), you should remove the image path, and rename the {file-name}-ann-id with only the ann-id"
created: 2026-06-14T09:10:10+07:00
updated: 2026-06-14T09:27:00+07:00
---

# Debug Session: report-format-ann-id-only

## Symptoms

- expected_behavior: "I just want to remove and change some field."
- actual_behavior: "Reports currently include image path and object IDs formatted like {file-name}-ann-id; user wants image path removed and only ann-id."
- error_messages: "Formatting/output change only."
- timeline: "It has always been like this."
- reproduction: "Run verify command and inspect CSV/JSON outputs."

## Current Focus

- hypothesis: "Report serializers include crop/image path fields and object ID normalization concatenates sample/file token with ann-id."
- next_action: "verify patched output and regression tests"
- test: "Trace run_verify result object_id creation and CSV/JSON report serializers for image/crop path emission."
- expecting: "Find object_id builder adding sample/file prefix and report writers including path fields."

## Evidence

- timestamp: 2026-06-14T09:10:10+07:00
  note: "User requested output format change for verify reports."
- timestamp: 2026-06-14T09:27:00+07:00
  note: "Patched object_id fallback to ann-{index} and removed crop_path from deterministic CSV/JSON/NDJSON + summary object serialization."

## Eliminated

- hypothesis: "Formatting issue caused by report writers."
  reason: "Confirmed and fixed; no runtime error path involved."

## Resolution

- root_cause: "run_verify fallback object_id used `{sample_id}-ann-{index}` and deterministic report serializers emitted `crop_path`."
- fix: "Changed fallback object_id to `ann-{index}` and removed `crop_path` from deterministic serialized outputs (CSV/JSON/NDJSON and summary objects). Updated tests accordingly."
- verification: "pytest -q tests/phase6 tests/phase7 && pytest -q passed (101 total)."
- files_changed:
  - src/fiftyone_pose_importer/run_verify.py
  - src/fiftyone_pose_importer/verification/report_json.py
  - src/fiftyone_pose_importer/verification/report_csv.py
  - tests/phase6/test_reporting.py
  - tests/phase6/test_run_verify.py
