# Testing Patterns

**Analysis Date:** 2026-06-14

## Test Framework

**Runner:** pytest (inferred from test file structure and fixture usage — no `pytest.ini` or `[tool.pytest.ini_options]` in `pyproject.toml`)

**Assertion style:** Plain `assert` statements throughout — no assertion helper library

**Built-in fixtures used:** `tmp_path: Path`, `capsys` (pytest built-ins only — no `pytest-mock` or other plugins observed)

**Run Commands:**
```bash
# Run all tests (from repo root)
pytest tests/

# Run a specific phase
pytest tests/phase7/

# Run a single file
pytest tests/phase7/test_vlm_engine.py

# Run with coverage (if pytest-cov installed)
pytest tests/ --cov=src/fiftyone_pose_importer --cov-report=term-missing
```

## Test Structure

| Directory | What's Tested |
|-----------|--------------|
| `tests/conftest.py` | Shared path setup — injects `src/` into `sys.path` |
| `tests/phase2/` | Pose contract preflight, pose mapping import (legacy fiftyone integration) |
| `tests/phase4/` | Run summary schema, CLI launch behavior |
| `tests/phase5/` | Contract preflight with fake fiftyone injection |
| `tests/phase6/` | Verification engine, config loading, cropper, reporting (CSV/JSON/NDJSON), deterministic pipeline integration |
| `tests/phase7/` | VLM engine, VLM client adapters, VLM config loading, VLM report writing, full VLM pipeline integration |

**Total test count:** 108 `def test_*` functions

**`__init__.py` presence:** Only `tests/phase7/__init__.py` exists; other phase directories are plain directories (no `__init__.py`)

## Test Types

**Unit tests (pure function, no I/O):**
- `tests/phase7/test_vlm_engine.py` — `build_prompt`, `parse_vlm_response`, `_FENCE_RE` regex
- `tests/phase6/test_rules_engine.py` — deterministic rule evaluation
- `tests/phase6/test_verification_config.py` — config loader validation
- `tests/phase7/test_vlm_config.py` — VLM config loader validation
- `tests/phase6/test_verification_types.py` — type/dataclass behavior

**Integration tests (pipeline with real I/O via `tmp_path`):**
- `tests/phase6/test_run_verify.py` — full deterministic pipeline: writes real YAML configs, real Datumaro JSON, real PNG images; calls `run_verify()`; asserts on filesystem artifacts and summary dict
- `tests/phase7/test_run_verify_vlm.py` — same as above but with VLM enabled, using `MockVlmAdapter` for injection
- `tests/phase6/test_reporting.py` — CSV/JSON/NDJSON report writing with `tmp_path`
- `tests/phase7/test_report_vlm.py` — VLM report writing with `tmp_path`
- `tests/phase6/test_cropper.py` — PIL image crop materialization with `tmp_path`

**CLI tests:**
- `tests/phase6/test_run_verify.py::test_cli_exit_code_zero_with_object_failures` — calls `cli.main(["verify", "--config", ...])`, uses `capsys` to capture stdout JSON
- `tests/phase6/test_run_verify.py::test_cli_verify_returns_non_zero_for_fatal_errors` — asserts non-zero exit and stderr JSON error payload

**E2E tests:** Not present (no browser/HTTP tests)

## Coverage

**Enforced target:** None (no coverage config in `pyproject.toml`)

**Known exclusions:**
- `# pragma: no cover - defensive guard for runtime isolation` on two `except Exception` blocks in `src/fiftyone_pose_importer/run_verify.py` (lines 315, 345) — guards for unexpected runtime errors that are intentionally not tested

**Known gaps:**
- `src/fiftyone_pose_importer/run_import.py` — FiftyOne import path; tests use fake fiftyone module injection (phase 4/5 pattern), not full pipeline
- `src/fiftyone_pose_importer/cli.py` — CLI main for import command is partially tested via phase 4 launch tests
- `FiftyOneZooAdapter.generate_text` lazy model loading via real `fiftyone.zoo` — tested by injecting `adapter._model = FakeModel()` directly, bypassing actual zoo load

## Test Conventions

### Helper Factory Functions (not pytest fixtures)

Tests use module-level `_make_*` factory functions instead of `@pytest.fixture`:

```python
# From tests/phase7/test_vlm_engine.py
def _make_det_result(
    sample_id: str = "s1",
    object_id: str = "o1",
    label: str = "forklift",
    verdict: DeterministicVerdict = DeterministicVerdict.PASS,
    crop_path: str = "crop.png",
) -> ObjectVerificationResult:
    return ObjectVerificationResult(
        sample_id=sample_id,
        object_id=object_id,
        label=label,
        verdict=verdict,
        crop_path=crop_path,
        rule_results=[],
        failure_reasons=[],
    )
```

```python
# From tests/phase7/test_report_vlm.py
def _make_vlm_result(
    sample_id: str,
    object_id: str,
    label: str,
    vlm_status: VlmVerdict,
    object_risk: float | None,
    *,
    rules: list[str] | None = None,
    failure_reason: str | None = None,
    crop_path: str = "c.png",
    adapter_model: str = "qwen3-vl-2b-instruct-torch",
) -> VlmObjectResult: ...
```

### Integration Test Setup Pattern

Integration tests write all fixtures to `tmp_path` using private helper functions:

```python
# From tests/phase6/test_run_verify.py
def _write_datumaro(tmp_path: Path) -> Path:
    datumaro_path = tmp_path / "datumaro.json"
    image_dir = tmp_path / "images"
    image_dir.mkdir(parents=True, exist_ok=True)
    Image.new("RGB", (120, 100), (200, 64, 32)).save(image_dir / "sample-1.png")
    datumaro_path.write_text(json.dumps(payload), encoding="utf-8")
    return datumaro_path

def _write_config(tmp_path: Path, datumaro_path: Path) -> Path:
    config_path.write_text(yaml.safe_dump({...}), encoding="utf-8")
    return config_path

def test_deterministic_only_pipeline_without_vlm(tmp_path: Path) -> None:
    datumaro_path = _write_datumaro(tmp_path)
    config_path = _write_config(tmp_path, datumaro_path)
    ok, summary = run_verify(str(config_path))
    assert ok is True
    assert summary["counts"]["objects_total"] == 2
```

### Mocking Strategy

**No `unittest.mock` or `pytest-mock`** — adapters are injected via Protocol:

```python
# MockVlmAdapter in src/fiftyone_pose_importer/verification/vlm_client.py
class MockVlmAdapter:
    def __init__(self, responses: dict[str, str] | None = None, default_response: str = ...):
        ...
    def generate_text(self, image: PILImage.Image, prompt: str) -> str:
        for key, resp in self._responses.items():
            if key in prompt:
                return resp
        return self._default
```

Used in tests via `_vlm_adapter=` injection parameter on `run_verify()`:
```python
mock = MockVlmAdapter(default_response='{"error_probability": 0.1, "reason": "ok"}')
ok, summary = run_verify(str(config), _vlm_adapter=mock)
```

**Inline anonymous adapter classes** used for edge-case behaviors:
```python
class FailAdapter:
    def generate_text(self, image, prompt):
        raise RuntimeError("GPU OOM")

class SlowMockAdapter:
    def generate_text(self, image, prompt):
        time.sleep(0.2)
        return '{"error_probability": 0.1, "reason": "ok"}'

class CaptureAdapter:
    def __init__(self) -> None:
        self.prompts: list[str] = []
    def generate_text(self, image, prompt):
        self.prompts.append(prompt)
        return '{"error_probability": 0.1, "reason": "ok"}'
```

**Fake fiftyone injection** (phase 2/4/5 pattern — avoid for new tests):
```python
# sys.modules injection at test module level
def _install_fake_fiftyone() -> types.ModuleType:
    module = types.ModuleType("fiftyone")
    # ... populate fake classes ...
    return module

sys.modules["fiftyone"] = _install_fake_fiftyone()
importlib.import_module("fiftyone_pose_importer.run_import")
```

**FiftyOneZooAdapter internal state injection** (bypass zoo load):
```python
adapter = FiftyOneZooAdapter(model_name="qwen3-vl-2b-instruct-torch")
adapter._model = FakeModel()  # inject directly into private attribute
assert adapter.generate_text(_img(), "my prompt") == "raw text from fake model"
```

### Error Assertion Pattern

```python
with pytest.raises(VlmConfigError):
    load_vlm_config({})

with pytest.raises(VerificationConfigError):
    load_verification_config({"padding_px": -1})

with pytest.raises(RuntimeError, match="inference failed"):
    adapter.generate_text(_img(), "prompt")
```

### Assertion Style

- Direct equality for scalar values: `assert result.error_probability == 0.3`
- Identity for enum comparisons: `assert result.verdict is DeterministicVerdict.FAIL`
- `assert ... in ...` for substring membership: `assert "JSON parse failed" in result.reason`
- `assert any(...)` for list membership without caring about index
- Set comparison for unordered collection equality: `assert set(parsed_bbox) == {"bbox"}`

### conftest.py

`tests/conftest.py` does one thing — adds `src/` to `sys.path`:
```python
ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))
```
No shared fixtures defined at the conftest level — all test data setup is local to each test file.

### Return Type Annotations on Tests

All test functions use `-> None` return annotation:
```python
def test_parse_vlm_response_valid_json() -> None:
    ...
```

---

*Testing analysis: 2026-06-14*
