from __future__ import annotations

import json
from pathlib import Path
from types import TracebackType
from typing import IO

from .report_json import _sorted_results, serialize_object_result
from .types import ObjectVerificationResult


def write_ndjson_report(results: list[ObjectVerificationResult], output_path: Path) -> Path:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as handle:
        for result in _sorted_results(results):
            record = serialize_object_result(result)
            handle.write(json.dumps(record, ensure_ascii=False, sort_keys=True, separators=(",", ":")))
            handle.write("\n")
    return output_path


class NdjsonStreamWriter:
    """Context manager for incremental NDJSON writes during a processing loop.

    Writes one JSON record per line as results are produced, avoiding the need
    to buffer all results in memory before writing. Records are written in
    processing order (not sorted); use ``write_ndjson_report`` when a sorted
    trace is required.

    Usage::

        with NdjsonStreamWriter(output_path) as writer:
            for result in ...:
                writer.write(result)
    """

    def __init__(self, output_path: Path) -> None:
        self._output_path = output_path
        self._handle: IO[str] | None = None

    def __enter__(self) -> NdjsonStreamWriter:
        self._output_path.parent.mkdir(parents=True, exist_ok=True)
        self._handle = self._output_path.open("w", encoding="utf-8")
        return self

    def write(self, result: ObjectVerificationResult) -> None:
        if self._handle is None:
            raise RuntimeError("NdjsonStreamWriter must be used as a context manager")
        record = serialize_object_result(result)
        self._handle.write(json.dumps(record, ensure_ascii=False, sort_keys=True, separators=(",", ":")))
        self._handle.write("\n")

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        if self._handle is not None:
            self._handle.close()
            self._handle = None
