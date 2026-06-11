from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .run_import import run_import
from .summary import write_summary


def main() -> int:
    parser = argparse.ArgumentParser(description="Import image folder + Datumaro JSON into FiftyOne")
    parser.add_argument("--config", required=True, help="Path to YAML config file")
    parser.add_argument("--launch", action="store_true", help="Launch FiftyOne app after import")
    args = parser.parse_args()

    try:
        ok, summary = run_import(args.config, launch_app=args.launch)
        print(json.dumps(summary, indent=2))
        return 0 if ok else 1
    except Exception as exc:
        error_summary = {"ok": False, "error": str(exc)}
        try:
            summary_path = write_summary(Path(args.config).resolve(), error_summary)
        except Exception:
            fallback_cfg = Path.cwd() / "import-run.yaml"
            summary_path = write_summary(fallback_cfg, error_summary)
        error_summary["summary_path"] = str(summary_path)
        print(json.dumps(error_summary, indent=2), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
