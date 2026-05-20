#!/usr/bin/env python3
"""MNQH25 5m wrapper around tools/sync_public_report_bundle.py."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_SOURCE = (
    REPO_ROOT.parent
    / "supabase-opti-database"
    / "docs"
    / "reports"
    / "vwap-mnqh25-5m-historical-sample-20260519"
)

APPROVAL = "GO_REPLACE_PUBLIC_REPORT_MNQH25_5M_CERTIFIED_20260519"
TARGET = "MNQH25_20241216-20250314_5m"
SLUG = "vwap-mnqh25-5m-historical-sample-20260519"


def main(argv: list[str] | None = None) -> int:
    import argparse

    parser = argparse.ArgumentParser(description="Sync MNQH25 5m certified public sample")
    parser.add_argument("--source", type=Path, default=DEFAULT_SOURCE)
    parser.add_argument(
        "--approval",
        default=APPROVAL,
        help="Operator approval gate string",
    )
    args = parser.parse_args(argv)

    cmd = [
        sys.executable,
        str(REPO_ROOT / "tools" / "sync_public_report_bundle.py"),
        "--source",
        str(args.source.resolve()),
        "--contract",
        "MNQH25",
        "--timeframe",
        "5m",
        "--start",
        "20241216",
        "--end",
        "20250314",
        "--target-folder",
        TARGET,
        "--keep-slug-alias",
        SLUG,
        "--replace-same-contract-timeframe",
        "--approval",
        args.approval,
    ]
    return subprocess.call(cmd)


if __name__ == "__main__":
    raise SystemExit(main())
