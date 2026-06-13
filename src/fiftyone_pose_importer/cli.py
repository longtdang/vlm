from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .run_import import run_import
from .run_verify import run_verify
from .summary import write_summary


def _run_import_command(config_path: str, launch: bool) -> int:
    try:
        ok, summary = run_import(config_path, launch_app=launch)
        print(json.dumps(summary, indent=2))
        return 0 if ok else 1
    except Exception as exc:
        error_summary = {"ok": False, "error": str(exc)}
        try:
            summary_path = write_summary(Path(config_path).resolve(), error_summary)
        except Exception:
            fallback_cfg = Path.cwd() / "import-run.yaml"
            summary_path = write_summary(fallback_cfg, error_summary)
        error_summary["summary_path"] = str(summary_path)
        print(json.dumps(error_summary, indent=2), file=sys.stderr)
        return 1


def _run_verify_command(config_path: str) -> int:
    try:
        ok, summary = run_verify(config_path)
        print(json.dumps(summary, indent=2))
        return 0 if ok else 1
    except Exception as exc:
        print(json.dumps({"ok": False, "error": str(exc)}, indent=2), file=sys.stderr)
        return 1


def _main_with_subcommands(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description="FiftyOne importer and verification CLI")
    subparsers = parser.add_subparsers(dest="command", required=True)

    import_parser = subparsers.add_parser("import", help="Import image folder + Datumaro JSON into FiftyOne")
    import_parser.add_argument("--config", required=True, help="Path to YAML config file")
    import_parser.add_argument("--launch", action="store_true", help="Launch FiftyOne app after import")

    verify_parser = subparsers.add_parser("verify", help="Run deterministic verification without VLM")
    verify_parser.add_argument("--config", required=True, help="Path to YAML config file")

    args = parser.parse_args(argv)
    if args.command == "import":
        return _run_import_command(args.config, launch=args.launch)
    if args.command == "verify":
        return _run_verify_command(args.config)
    return 1


def _main_legacy_import(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description="Import image folder + Datumaro JSON into FiftyOne")
    parser.add_argument("--config", required=True, help="Path to YAML config file")
    parser.add_argument("--launch", action="store_true", help="Launch FiftyOne app after import")
    args = parser.parse_args(argv)
    return _run_import_command(args.config, launch=args.launch)


def main(argv: list[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    if args and args[0] in {"import", "verify"}:
        return _main_with_subcommands(args)
    return _main_legacy_import(args)


if __name__ == "__main__":
    raise SystemExit(main())
