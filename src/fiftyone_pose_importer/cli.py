from __future__ import annotations

import argparse
import json
import sys

from .run_import import run_import


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
        print(json.dumps({"ok": False, "error": str(exc)}, indent=2), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())

