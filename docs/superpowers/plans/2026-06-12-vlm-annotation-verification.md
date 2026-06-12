# VLM Annotation Verification Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a rule-driven annotation verifier that crops each annotation, applies deterministic checks, optionally applies Qwen2.5-7B-Instruct per class policy, and exports CSV + JSON reports.

**Architecture:** Add a separate verification pipeline under `src/fiftyone_pose_importer/` to avoid coupling with importer logic. The pipeline runs in stages: load config and annotations, crop, deterministic validate, optional VLM validate, decision combine, and report export. Class-level policy controls whether VLM is used (`never`, `ambiguous_only`, `always`).

**Tech Stack:** Python 3.10+, FiftyOne, Pydantic, PyYAML, pytest, csv/json stdlib, urllib (for optional OpenAI-compatible HTTP endpoint).

---

## File Structure

- Create: `src/fiftyone_pose_importer/verify_config.py` — config model for verification mode and rule files
- Create: `src/fiftyone_pose_importer/verify_rules.py` — rule schema + parser/validator
- Create: `src/fiftyone_pose_importer/cropper.py` — crop generation with fixed padding policy
- Create: `src/fiftyone_pose_importer/deterministic_checks.py` — deterministic rule evaluators
- Create: `src/fiftyone_pose_importer/vlm_client.py` — Qwen request/response adapter
- Create: `src/fiftyone_pose_importer/verify_runner.py` — orchestration pipeline and decision combiner
- Create: `src/fiftyone_pose_importer/verify_report.py` — CSV + JSON report writing
- Modify: `src/fiftyone_pose_importer/cli.py` — add `verify` command path
- Modify: `README.md` — usage + config examples for verification mode
- Create: `tests/verify/test_verify_config.py`
- Create: `tests/verify/test_cropper.py`
- Create: `tests/verify/test_deterministic_checks.py`
- Create: `tests/verify/test_verify_runner.py`
- Create: `tests/verify/test_verify_report.py`

### Task 1: Add verification config and CLI entry

**Files:**
- Create: `src/fiftyone_pose_importer/verify_config.py`
- Modify: `src/fiftyone_pose_importer/cli.py`
- Test: `tests/verify/test_verify_config.py`

- [ ] **Step 1: Write failing config tests**

```python
# tests/verify/test_verify_config.py
from pathlib import Path
from fiftyone_pose_importer.verify_config import load_verify_config


def test_load_verify_config_resolves_rule_path(tmp_path: Path) -> None:
    cfg = tmp_path / "verify.yaml"
    cfg.write_text(
        "dataset_name: ds\n"
        "label_field: ground_truth\n"
        "rules_path: ./rules.yaml\n"
        "output_dir: ./reports\n",
        encoding="utf-8",
    )
    (tmp_path / "rules.yaml").write_text("classes: {}\n", encoding="utf-8")
    out = load_verify_config(cfg)
    assert out.rules_path == (tmp_path / "rules.yaml").resolve()
    assert out.output_dir == (tmp_path / "reports").resolve()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/verify/test_verify_config.py -v`  
Expected: FAIL with `ModuleNotFoundError` for `verify_config`

- [ ] **Step 3: Write minimal config implementation**

```python
# src/fiftyone_pose_importer/verify_config.py
from pathlib import Path
import yaml
from pydantic import BaseModel, ConfigDict


class VerifyConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")
    dataset_name: str
    label_field: str = "ground_truth"
    rules_path: Path
    output_dir: Path
    crop_padding_ratio: float = 0.15
    crop_min_w: int = 32
    crop_min_h: int = 32
    vlm_endpoint: str | None = None
    vlm_model: str = "Qwen/Qwen2.5-7B-Instruct"


def load_verify_config(config_path: Path) -> VerifyConfig:
    raw = yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}
    base = config_path.parent.resolve()
    if "rules_path" in raw:
        raw["rules_path"] = (base / raw["rules_path"]).resolve()
    if "output_dir" in raw:
        raw["output_dir"] = (base / raw["output_dir"]).resolve()
    return VerifyConfig(**raw)
```

- [ ] **Step 4: Add CLI command skeleton for verify**

```python
# in src/fiftyone_pose_importer/cli.py (argparse additions)
parser.add_argument("--verify-config", help="Path to YAML verification config file")

# in main() before import flow
if args.verify_config:
    from .verify_runner import run_verify
    ok, summary = run_verify(args.verify_config)
    print(json.dumps(summary, indent=2))
    return 0 if ok else 1
```

- [ ] **Step 5: Run tests to verify pass**

Run: `pytest tests/verify/test_verify_config.py -v`  
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add tests/verify/test_verify_config.py src/fiftyone_pose_importer/verify_config.py src/fiftyone_pose_importer/cli.py
git commit -m "feat: add verification config loading and CLI entry"
```

### Task 2: Implement cropper (tight bbox + fixed padding)

**Files:**
- Create: `src/fiftyone_pose_importer/cropper.py`
- Test: `tests/verify/test_cropper.py`

- [ ] **Step 1: Write failing crop logic tests**

```python
# tests/verify/test_cropper.py
from fiftyone_pose_importer.cropper import compute_crop_bounds


def test_compute_crop_bounds_with_padding_and_clamp() -> None:
    bounds = compute_crop_bounds(
        x=10, y=10, w=20, h=20, img_w=50, img_h=50, padding_ratio=0.15, min_w=32, min_h=32
    )
    assert bounds == (4, 4, 36, 36)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/verify/test_cropper.py::test_compute_crop_bounds_with_padding_and_clamp -v`  
Expected: FAIL because function does not exist

- [ ] **Step 3: Write minimal crop implementation**

```python
# src/fiftyone_pose_importer/cropper.py
from __future__ import annotations


def compute_crop_bounds(*, x: float, y: float, w: float, h: float, img_w: int, img_h: int, padding_ratio: float, min_w: int, min_h: int) -> tuple[int, int, int, int]:
    pad_w = w * padding_ratio
    pad_h = h * padding_ratio
    left = max(0, int(round(x - pad_w)))
    top = max(0, int(round(y - pad_h)))
    right = min(img_w, int(round(x + w + pad_w)))
    bottom = min(img_h, int(round(y + h + pad_h)))
    cur_w = right - left
    cur_h = bottom - top
    if cur_w < min_w:
        grow = min_w - cur_w
        left = max(0, left - grow // 2)
        right = min(img_w, right + (grow - grow // 2))
    if cur_h < min_h:
        grow = min_h - cur_h
        top = max(0, top - grow // 2)
        bottom = min(img_h, bottom + (grow - grow // 2))
    return left, top, right, bottom
```

- [ ] **Step 4: Add crop extraction helper test and implementation**

```python
# test
import numpy as np
from fiftyone_pose_importer.cropper import crop_image

def test_crop_image_returns_expected_shape() -> None:
    img = np.zeros((100, 120, 3), dtype=np.uint8)
    out = crop_image(img, (10, 20, 50, 80))
    assert out.shape == (60, 40, 3)
```

```python
# implementation
def crop_image(image, bounds):
    left, top, right, bottom = bounds
    return image[top:bottom, left:right]
```

- [ ] **Step 5: Run tests to verify pass**

Run: `pytest tests/verify/test_cropper.py -v`  
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add tests/verify/test_cropper.py src/fiftyone_pose_importer/cropper.py
git commit -m "feat: add fixed-padding annotation cropper"
```

### Task 3: Add class rule parser + deterministic checks

**Files:**
- Create: `src/fiftyone_pose_importer/verify_rules.py`
- Create: `src/fiftyone_pose_importer/deterministic_checks.py`
- Test: `tests/verify/test_deterministic_checks.py`

- [ ] **Step 1: Write failing rule parser tests**

```python
# tests/verify/test_deterministic_checks.py
from fiftyone_pose_importer.verify_rules import parse_rules


def test_parse_rules_reads_class_vlm_policy() -> None:
    rules = {"classes": {"person": {"vlm_enabled": True, "vlm_policy": "ambiguous_only", "hard_checks": []}}}
    parsed = parse_rules(rules)
    assert parsed.classes["person"].vlm_enabled is True
    assert parsed.classes["person"].vlm_policy == "ambiguous_only"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/verify/test_deterministic_checks.py::test_parse_rules_reads_class_vlm_policy -v`  
Expected: FAIL with missing module/function

- [ ] **Step 3: Implement rule models and parser**

```python
# src/fiftyone_pose_importer/verify_rules.py
from pydantic import BaseModel, ConfigDict


class HardCheck(BaseModel):
    rule_id: str
    min_w: float | None = None
    min_h: float | None = None
    min_ratio: float | None = None
    max_ratio: float | None = None


class ClassRule(BaseModel):
    model_config = ConfigDict(extra="forbid")
    vlm_enabled: bool = False
    vlm_policy: str = "never"
    hard_checks: list[HardCheck] = []
    vlm_checks: list[dict] = []


class RuleSet(BaseModel):
    classes: dict[str, ClassRule]


def parse_rules(raw: dict) -> RuleSet:
    return RuleSet(**raw)
```

- [ ] **Step 4: Write failing deterministic check tests**

```python
from fiftyone_pose_importer.deterministic_checks import evaluate_hard_checks
from fiftyone_pose_importer.verify_rules import parse_rules


def test_evaluate_hard_checks_bbox_min_size_fail() -> None:
    rules = parse_rules({"classes": {"person": {"hard_checks": [{"rule_id": "bbox_min_size", "min_w": 24, "min_h": 24}]}}})
    verdict = evaluate_hard_checks("person", {"w": 10, "h": 20, "ratio": 0.5}, rules)
    assert verdict["hard_fail"] is True
    assert verdict["failed_rule_ids"] == ["bbox_min_size"]
```

- [ ] **Step 5: Implement deterministic evaluator**

```python
# src/fiftyone_pose_importer/deterministic_checks.py
from __future__ import annotations


def evaluate_hard_checks(class_name: str, metrics: dict, ruleset) -> dict:
    class_rule = ruleset.classes.get(class_name)
    if class_rule is None:
        return {"hard_fail": False, "failed_rule_ids": []}
    failed: list[str] = []
    for check in class_rule.hard_checks:
        if check.rule_id == "bbox_min_size":
            if metrics["w"] < (check.min_w or 0) or metrics["h"] < (check.min_h or 0):
                failed.append(check.rule_id)
        elif check.rule_id == "bbox_aspect_range":
            ratio = metrics["ratio"]
            if check.min_ratio is not None and ratio < check.min_ratio:
                failed.append(check.rule_id)
            if check.max_ratio is not None and ratio > check.max_ratio:
                failed.append(check.rule_id)
    return {"hard_fail": len(failed) > 0, "failed_rule_ids": failed}
```

- [ ] **Step 6: Run tests to verify pass**

Run: `pytest tests/verify/test_deterministic_checks.py -v`  
Expected: PASS

- [ ] **Step 7: Commit**

```bash
git add tests/verify/test_deterministic_checks.py src/fiftyone_pose_importer/verify_rules.py src/fiftyone_pose_importer/deterministic_checks.py
git commit -m "feat: add class rule parsing and deterministic checks"
```

### Task 4: Add VLM adapter, routing, and decision combiner

**Files:**
- Create: `src/fiftyone_pose_importer/vlm_client.py`
- Create: `src/fiftyone_pose_importer/verify_runner.py`
- Test: `tests/verify/test_verify_runner.py`

- [ ] **Step 1: Write failing routing/decision tests**

```python
# tests/verify/test_verify_runner.py
from fiftyone_pose_importer.verify_runner import should_run_vlm, combine_decision


def test_should_run_vlm_uses_class_policy() -> None:
    assert should_run_vlm(vlm_enabled=True, vlm_policy="ambiguous_only", is_ambiguous=True) is True
    assert should_run_vlm(vlm_enabled=True, vlm_policy="ambiguous_only", is_ambiguous=False) is False
    assert should_run_vlm(vlm_enabled=False, vlm_policy="always", is_ambiguous=True) is False


def test_combine_decision_prefers_hard_fail() -> None:
    out = combine_decision(hard_fail=True, vlm_status="PASS", vlm_confidence=0.9)
    assert out == "FAIL"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/verify/test_verify_runner.py -v`  
Expected: FAIL with missing symbols

- [ ] **Step 3: Implement routing/combiner**

```python
# src/fiftyone_pose_importer/verify_runner.py
def should_run_vlm(*, vlm_enabled: bool, vlm_policy: str, is_ambiguous: bool) -> bool:
    if not vlm_enabled or vlm_policy == "never":
        return False
    if vlm_policy == "always":
        return True
    return is_ambiguous


def combine_decision(*, hard_fail: bool, vlm_status: str | None, vlm_confidence: float | None) -> str:
    if hard_fail:
        return "FAIL"
    if vlm_status is None:
        return "PASS"
    if vlm_status == "FAIL":
        return "FAIL"
    if vlm_status == "REVIEW" or (vlm_confidence is not None and vlm_confidence < 0.6):
        return "REVIEW"
    return "PASS"
```

- [ ] **Step 4: Add failing VLM client parser test**

```python
from fiftyone_pose_importer.vlm_client import parse_vlm_json

def test_parse_vlm_json_valid_schema() -> None:
    out = parse_vlm_json('{"status":"PASS","reason_code":"ok","confidence":0.92}')
    assert out["status"] == "PASS"
    assert out["confidence"] == 0.92
```

- [ ] **Step 5: Implement minimal VLM response parser**

```python
# src/fiftyone_pose_importer/vlm_client.py
import json


def parse_vlm_json(raw: str) -> dict:
    data = json.loads(raw)
    status = data.get("status")
    if status not in {"PASS", "FAIL", "REVIEW"}:
        raise ValueError("Invalid VLM status")
    return {
        "status": status,
        "reason_code": str(data.get("reason_code", "unknown")),
        "confidence": float(data.get("confidence", 0.0)),
    }
```

- [ ] **Step 6: Run tests to verify pass**

Run: `pytest tests/verify/test_verify_runner.py -v`  
Expected: PASS

- [ ] **Step 7: Commit**

```bash
git add tests/verify/test_verify_runner.py src/fiftyone_pose_importer/verify_runner.py src/fiftyone_pose_importer/vlm_client.py
git commit -m "feat: add class-scoped VLM routing and decision combiner"
```

### Task 5: Add report export and end-to-end verify runner integration

**Files:**
- Create: `src/fiftyone_pose_importer/verify_report.py`
- Modify: `src/fiftyone_pose_importer/verify_runner.py`
- Modify: `README.md`
- Test: `tests/verify/test_verify_report.py`

- [ ] **Step 1: Write failing report export tests**

```python
# tests/verify/test_verify_report.py
from pathlib import Path
from fiftyone_pose_importer.verify_report import write_verify_reports


def test_write_verify_reports_creates_csv_and_json(tmp_path: Path) -> None:
    rows = [{"annotation_id": "a1", "class": "person", "status": "PASS", "failed_rule_ids": ""}]
    summary = {"total": 1, "pass": 1, "fail": 0, "review": 0}
    out = write_verify_reports(tmp_path, rows, summary)
    assert out["csv_path"].exists()
    assert out["json_path"].exists()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/verify/test_verify_report.py -v`  
Expected: FAIL with missing module/function

- [ ] **Step 3: Implement report writer**

```python
# src/fiftyone_pose_importer/verify_report.py
from __future__ import annotations

import csv
import json
from pathlib import Path


def write_verify_reports(output_dir: Path, rows: list[dict], summary: dict) -> dict:
    output_dir.mkdir(parents=True, exist_ok=True)
    csv_path = output_dir / "verify-report.csv"
    json_path = output_dir / "verify-summary.json"
    fieldnames = sorted({k for row in rows for k in row.keys()}) if rows else ["annotation_id", "class", "status"]
    with csv_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)
    json_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    return {"csv_path": csv_path, "json_path": json_path}
```

- [ ] **Step 4: Implement verify runner `run_verify()` integration**

```python
# in src/fiftyone_pose_importer/verify_runner.py
from pathlib import Path
import json
import fiftyone as fo
import yaml
from .verify_config import load_verify_config
from .verify_rules import parse_rules
from .deterministic_checks import evaluate_hard_checks
from .verify_report import write_verify_reports


def run_verify(config_path: str) -> tuple[bool, dict]:
    cfg = load_verify_config(Path(config_path))
    rules = parse_rules(yaml.safe_load(cfg.rules_path.read_text(encoding="utf-8")) or {})
    dataset = fo.load_dataset(cfg.dataset_name)
    rows: list[dict] = []
    for sample in dataset:
        keypoints = sample.get(cfg.label_field)
        if keypoints is None:
            continue
        for idx, kp in enumerate(keypoints.keypoints):
            class_name = str(getattr(kp, "label", "unknown"))
            metrics = {"w": 0.0, "h": 0.0, "ratio": 0.0}
            det = evaluate_hard_checks(class_name, metrics, rules)
            status = "FAIL" if det["hard_fail"] else "PASS"
            rows.append(
                {
                    "sample_id": sample.id,
                    "annotation_id": f"{sample.id}:{idx}",
                    "class": class_name,
                    "status": status,
                    "failed_rule_ids": ",".join(det["failed_rule_ids"]),
                }
            )
    summary = {
        "total": len(rows),
        "pass": sum(1 for r in rows if r["status"] == "PASS"),
        "fail": sum(1 for r in rows if r["status"] == "FAIL"),
        "review": sum(1 for r in rows if r["status"] == "REVIEW"),
    }
    paths = write_verify_reports(cfg.output_dir, rows, summary)
    result = {
        "ok": summary["fail"] == 0 and summary["review"] == 0,
        "dataset_name": cfg.dataset_name,
        "label_field": cfg.label_field,
        "report_csv_path": str(paths["csv_path"]),
        "report_summary_path": str(paths["json_path"]),
        "summary": summary,
    }
    return result["ok"], result
```

- [ ] **Step 5: Add README usage section**

```markdown
## Verify annotations with rules + VLM

Run:

`python -m fiftyone_pose_importer.cli --verify-config ./verify.example.yaml`

Example `verify.example.yaml`:

```yaml
dataset_name: cvat_pose_dataset
label_field: ground_truth
rules_path: ./rules.yaml
output_dir: ./verify-reports
```

Optional:

- Set `vlm_endpoint` for OpenAI-compatible serving endpoint
- Keep class-level `vlm_enabled` as `false` for deterministic-only classes

Rules run first, then VLM (if enabled/policy allows).

Outputs:

- `verify-report.csv`
- `verify-summary.json`
```

```bash
python -m fiftyone_pose_importer.cli --verify-config ./verify.example.yaml
```

- [ ] **Step 6: Run full test pass**

Run: `pytest -q tests/verify tests/phase2 tests/phase4 -x`  
Expected: all PASS

- [ ] **Step 7: Commit**

```bash
git add tests/verify src/fiftyone_pose_importer/verify_report.py src/fiftyone_pose_importer/verify_runner.py README.md
git commit -m "feat: add verification reporting pipeline"
```

## Spec Coverage Check

- Crop-before-VLM with fixed padding: covered in Task 2 + Task 5 integration
- Class-scoped VLM policy (`vlm_enabled`, `vlm_policy`): covered in Task 3 + Task 4
- Deterministic-first validation and auditability: covered in Task 3 + Task 4 + Task 5
- CSV + JSON reporting: covered in Task 5
- Fail-safe handling (`REVIEW` on I/O/VLM errors): implemented in Task 4 + Task 5 integration
