#!/usr/bin/env python3
"""
Resumable batch public report rollout for MNQ 2025 H/M/U contracts (VWAP-REPORT only).

Packages from supabase internal bundles, syncs into docs/reports/, validates public safety,
and checkpoints state under out/audits/vwap_report_rollout_20260520/.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import sys
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parent.parent
REPORTS_DIR = REPO_ROOT / "docs" / "reports"
MANIFEST_FILE = REPO_ROOT / "docs" / "manifest.json"
AUDIT_DIR = REPO_ROOT / "out" / "audits" / "vwap_report_rollout_20260520"
STATE_FILE = AUDIT_DIR / "rollout_state.json"

SUPABASE_ROOT = REPO_ROOT.parent / "supabase-opti-database"
BUNDLE_ROOT = (
    SUPABASE_ROOT
    / "LOCAL DATABASE/out/vwap_reports_internal_regen/hmu_existing_report_stack_bridge_dryrun_20260519"
)
CANON_ROOT = (
    SUPABASE_ROOT
    / "LOCAL DATABASE/out/vwap_strategy_research/mnq_2025_all_tf_canonicalization_20260518_170931"
)
PACKAGER = SUPABASE_ROOT / "scripts/package_vwap_public_sample_from_bundle.py"
SYNC_TOOL = REPO_ROOT / "tools/sync_public_report_bundle.py"

BATCH_APPROVAL_PREFIX = "GO_ROLLOUT_PUBLIC_REPORTS_MNQM25_MNQU25_CERTIFIED_"
FOLDER_PATTERN = re.compile(r"^(?P<contract>[A-Z0-9]+)_(?P<start>\d{8})-(?P<end>\d{8})_(?P<tf>\d+m)$")
PROTECTED_CONTRACTS = frozenset({"MNQZ25", "MNQH25"})
BLOCKED_SUFFIXES = {".csv", ".json", ".parquet", ".txt"}

CORE_PUBLIC_STEMS = (
    "daily_max_extensions",
    "dashboard_all_events",
    "dashboard_crosses",
    "extension_tail_metrics",
    "heatmap_time_of_day_x_reaction",
    "hold_fail_rates",
    "mfe_mae_by_event_window",
    "oos_by_month",
    "regime_segment_grid",
)

LATTICE = {
    "1m": (390, "09:31:00", "16:00:00"),
    "5m": (78, "09:35:00", "16:00:00"),
    "15m": (26, "09:45:00", "16:00:00"),
    "30m": (13, "10:00:00", "16:00:00"),
}

CONTRACT_META: dict[str, dict[str, Any]] = {
    "MNQM25": {
        "start": "20250317",
        "end": "20250613",
        "legacy_start": "20250316",
        "sessions": 63,
        "iso_start": "2025-03-17",
        "iso_end": "2025-06-13",
    },
    "MNQU25": {
        "start": "20250616",
        "end": "20250912",
        "legacy_start": "20250615",
        "sessions": 40,
        "iso_start": "2025-06-16",
        "iso_end": "2025-09-12",
    },
}

TIMEFRAMES = ("1m", "5m", "15m", "30m")


@dataclass
class Target:
    contract: str
    timeframe: str
    start: str
    end: str
    legacy_start: str
    sessions: int
    bars_per_session: int
    bundle_name: str
    target_folder: str
    legacy_folder: str
    staging_slug: str
    sync_approval: str

    @property
    def key(self) -> str:
        return f"{self.contract}|{self.timeframe}"

    @property
    def internal_bundle(self) -> Path:
        return BUNDLE_ROOT / self.bundle_name

    @property
    def staging_dir(self) -> Path:
        return SUPABASE_ROOT / "docs/reports" / self.staging_slug

    @property
    def public_dashboards(self) -> Path:
        return REPORTS_DIR / self.target_folder / "dashboards"


def _iso_from_yyyymmdd(value: str) -> str:
    return f"{value[:4]}-{value[4:6]}-{value[6:8]}"


def build_targets(contracts: list[str]) -> list[Target]:
    targets: list[Target] = []
    for contract in contracts:
        if contract not in CONTRACT_META:
            raise ValueError(f"Unknown contract: {contract}")
        meta = CONTRACT_META[contract]
        for tf in TIMEFRAMES:
            bars, _, _ = LATTICE[tf]
            targets.append(
                Target(
                    contract=contract,
                    timeframe=tf,
                    start=meta["start"],
                    end=meta["end"],
                    legacy_start=meta["legacy_start"],
                    sessions=meta["sessions"],
                    bars_per_session=bars,
                    bundle_name=f"{contract}_{meta['start']}-{meta['end']}_{tf}",
                    target_folder=f"{contract}_{meta['start']}-{meta['end']}_{tf}",
                    legacy_folder=f"{contract}_{meta['legacy_start']}-{meta['end']}_{tf}",
                    staging_slug=f"vwap-{contract.lower()}-{tf}-historical-sample-20260520",
                    sync_approval=f"GO_REPLACE_PUBLIC_REPORT_{contract}_{tf.upper()}_CERTIFIED_20260520",
                )
            )
    return targets


def load_state() -> dict[str, Any]:
    if STATE_FILE.is_file():
        return json.loads(STATE_FILE.read_text(encoding="utf-8"))
    return {"version": 1, "targets": {}, "protected_baselines": {}}


def save_state(state: dict[str, Any]) -> None:
    AUDIT_DIR.mkdir(parents=True, exist_ok=True)
    state["updated_at"] = datetime.now(timezone.utc).isoformat()
    STATE_FILE.write_text(json.dumps(state, indent=2), encoding="utf-8")


def _inventory(root: Path) -> list[str]:
    if not root.is_dir():
        return []
    return sorted(
        str(p.relative_to(root)).replace("\\", "/")
        for p in root.rglob("*")
        if p.is_file()
    )


def _sha256_inventory(files: list[str]) -> str:
    return hashlib.sha256("\n".join(files).encode()).hexdigest()


def validate_batch_approval(approval: str) -> None:
    if not approval.startswith(BATCH_APPROVAL_PREFIX) or len(approval) <= len(BATCH_APPROVAL_PREFIX):
        raise ValueError(
            f"Invalid batch approval. Required prefix: {BATCH_APPROVAL_PREFIX}<tag>"
        )


def validate_source_bundle(target: Target) -> dict[str, Any]:
    bundle = target.internal_bundle
    failures: list[str] = []
    row: dict[str, Any] = {"bundle": str(bundle), "timeframe": target.timeframe}

    if not bundle.is_dir():
        failures.append("bundle_missing")
        row["gate"] = "SOURCE_BLOCKED"
        row["failures"] = failures
        return row

    man_path = bundle / "parquet_edgeful_bridge_manifest.json"
    if not man_path.is_file():
        failures.append("missing_bridge_manifest")
        row["gate"] = "SOURCE_BLOCKED"
        row["failures"] = failures
        return row

    man = json.loads(man_path.read_text(encoding="utf-8"))
    rp_path = bundle / "report_params.json"
    rp = json.loads(rp_path.read_text(encoding="utf-8")) if rp_path.is_file() else {}

    row["manifest_timeframe"] = man.get("timeframe")
    row["manifest_sessions"] = man.get("sessions")
    row["public_export"] = rp.get("public_export")
    row["machine_readable_exports"] = rp.get("machine_readable_exports")
    row["db_writes"] = man.get("db_writes")
    sp = man.get("source_parquet", {}).get("bars_features", "")
    row["bars_parquet"] = sp

    if man.get("timeframe") != target.timeframe:
        failures.append("timeframe_mismatch")
    if man.get("sessions") != target.sessions:
        failures.append(f"sessions_{man.get('sessions')}_expected_{target.sessions}")
    if rp.get("public_export") is True:
        failures.append("public_export_true")
    if rp.get("machine_readable_exports") not in ("internal_only", None, False, ""):
        failures.append("machine_readable_not_internal")
    if man.get("db_writes") is True:
        failures.append("db_writes_true")
    if "mnq_2025_all_tf_canonicalization_20260518_170931" not in sp.replace("\\", "/"):
        failures.append("canonical_lineage_not_170931")

    canon_ds = CANON_ROOT / target.contract / f"research_dataset_{target.timeframe}"
    row["canonical_dataset"] = str(canon_ds)
    if not canon_ds.is_dir():
        failures.append("canonical_dataset_missing")

    row["gate"] = "SOURCE_OK" if not failures else "SOURCE_BLOCKED"
    row["failures"] = failures
    return row


def find_legacy_candidates(target: Target) -> list[str]:
    """Folders that would be deleted on replace (same contract+tf, not certified target)."""
    sys.path.insert(0, str(REPO_ROOT / "tools"))
    from sync_public_report_bundle import _find_replace_candidates  # noqa: WPS433

    candidates = _find_replace_candidates(
        target.contract, target.timeframe, target.target_folder
    )
    names = [p.name for p in candidates]
    expected = target.legacy_folder
    if expected not in names and (REPORTS_DIR / expected).is_dir():
        names.append(expected)
    return sorted(set(names))


def scan_public_dashboards(dashboards: Path) -> dict[str, Any]:
    sys.path.insert(0, str(REPO_ROOT / "tools"))
    from sync_public_report_bundle import _scan_public_safety  # noqa: WPS433

    scan = _scan_public_safety(dashboards)
    errors = list(scan["errors"])
    index = dashboards / "index.html"
    if not index.is_file():
        errors.append("missing_index_html")
    else:
        tx = index.read_text(encoding="utf-8", errors="replace")
        cards = len(re.findall(r'class="dashboard-card"', tx))
        imgs = len(re.findall(r"<img", tx, re.I))
        placeholders = len(re.findall(r"no preview available", tx, re.I))
        if cards != 9:
            errors.append(f"gallery_cards_{cards}_expected_9")
        if imgs < 9:
            errors.append(f"png_previews_{imgs}_expected_9")
        if placeholders:
            errors.append(f"placeholders_{placeholders}")
        if "vwap_events.html" in tx:
            errors.append("vwap_events_in_index")
        if "dashboard_all_events" not in tx:
            errors.append("missing_all_events_in_index")
        if "dashboard_crosses" not in tx:
            errors.append("missing_crosses_in_index")
        for stem in CORE_PUBLIC_STEMS:
            matches = list(dashboards.glob(f"*{stem}*.html"))
            if not matches:
                errors.append(f"missing_dashboard_{stem}")
        hf = next((p for p in dashboards.glob("*hold_fail_rates*.html")), None)
        if hf:
            htx = hf.read_text(encoding="utf-8", errors="replace")
            if "Generic dashboard" in htx:
                errors.append("hold_fail_generic")
            if "Hold / Fail Rates" not in htx:
                errors.append("hold_fail_not_themed")
        else:
            errors.append("missing_hold_fail_html")

    return {
        "files": scan["files"],
        "errors": errors,
        "passed": len(errors) == 0,
        "file_count": len(scan["files"]),
    }


def capture_protected_baselines() -> dict[str, str]:
    baselines: dict[str, str] = {}
    for contract, tfs in (
        ("MNQZ25", ("5m",)),
        ("MNQH25", TIMEFRAMES),
    ):
        for tf in tfs:
            if contract == "MNQZ25":
                folder = f"MNQZ25_20250914-20251212_{tf}"
            else:
                folder = f"MNQH25_20241216-20250314_{tf}"
            ix = REPORTS_DIR / folder / "dashboards" / "index.html"
            if ix.is_file():
                baselines[f"{contract}|{tf}"] = hashlib.sha256(ix.read_bytes()).hexdigest()
    return baselines


def verify_protected_unchanged(state: dict[str, Any]) -> list[str]:
    failures: list[str] = []
    baselines = state.get("protected_baselines") or capture_protected_baselines()
    for key, expected in baselines.items():
        contract, tf = key.split("|")
        if contract == "MNQZ25":
            folder = f"MNQZ25_20250914-20251212_{tf}"
        else:
            folder = f"MNQH25_20241216-20250314_{tf}"
        ix = REPORTS_DIR / folder / "dashboards" / "index.html"
        if not ix.is_file():
            failures.append(f"protected_missing:{key}")
            continue
        actual = hashlib.sha256(ix.read_bytes()).hexdigest()
        if actual != expected:
            failures.append(f"protected_changed:{key}")
    return failures


def run_packager(target: Target, *, dry_run: bool) -> dict[str, Any]:
    if dry_run:
        inv = _inventory(target.internal_bundle / "dashboards") if (target.internal_bundle / "dashboards").is_dir() else []
        return {"dry_run": True, "would_package_to": str(target.staging_dir), "source_dashboard_files": len(inv)}

    if not PACKAGER.is_file():
        raise FileNotFoundError(f"Packager missing: {PACKAGER}")

    meta = CONTRACT_META[target.contract]
    cmd = [
        sys.executable,
        str(PACKAGER),
        "--source-bundle",
        str(target.internal_bundle),
        "--target-dir",
        str(target.staging_dir),
        "--contract",
        target.contract,
        "--timeframe",
        target.timeframe,
        "--start",
        meta["iso_start"],
        "--end",
        meta["iso_end"],
        "--sample-slug",
        f"{target.contract.lower()}_{target.timeframe}_20260520",
        "--complete-sessions",
        str(target.sessions),
        "--bars-per-session",
        str(target.bars_per_session),
        "--generate-screenshots",
        "--force-clean-target",
        "--canonical-parquet-lineage",
        str(CANON_ROOT / target.contract / f"research_dataset_{target.timeframe}"),
        "--internal-bundle-lineage",
        str(target.internal_bundle),
        "--one-minute-gate-status",
        "ONE_MINUTE_OPEN_LATTICE_FIXED_CONFIRMED",
    ]
    proc = subprocess.run(cmd, cwd=SUPABASE_ROOT, capture_output=True, text=True)
    if proc.returncode != 0:
        raise RuntimeError(f"packager_failed:{proc.stderr or proc.stdout}")

    inv = _inventory(target.staging_dir / "dashboards")
    scan = scan_public_dashboards(target.staging_dir / "dashboards")
    if not scan["passed"]:
        raise RuntimeError(f"staging_public_safety_failed:{scan['errors']}")

    return {
        "packager_stdout": proc.stdout.strip().splitlines()[-3:] if proc.stdout else [],
        "staging_inventory": inv,
        "inventory_sha256": _sha256_inventory(inv),
        "scan": scan,
    }


def run_sync(target: Target, *, dry_run: bool) -> dict[str, Any]:
    legacy = find_legacy_candidates(target)
    if dry_run:
        staging_inv = _inventory(target.staging_dir / "dashboards") if (target.staging_dir / "dashboards").is_dir() else []
        return {
            "dry_run": True,
            "would_sync_from": str(target.staging_dir),
            "target_folder": target.target_folder,
            "legacy_folders_to_delete": legacy,
            "would_copy_files": staging_inv,
            "sync_approval": target.sync_approval,
        }

    cmd = [
        sys.executable,
        str(SYNC_TOOL),
        "--source",
        str(target.staging_dir),
        "--contract",
        target.contract,
        "--timeframe",
        target.timeframe,
        "--start",
        target.start,
        "--end",
        target.end,
        "--target-folder",
        target.target_folder,
        "--replace-same-contract-timeframe",
        "--approval",
        target.sync_approval,
    ]
    proc = subprocess.run(cmd, cwd=REPO_ROOT, capture_output=True, text=True)
    if proc.returncode != 0:
        raise RuntimeError(f"sync_failed:{proc.stderr or proc.stdout}")

    scan = scan_public_dashboards(target.public_dashboards)
    if not scan["passed"]:
        raise RuntimeError(f"deployed_public_safety_failed:{scan['errors']}")

    inv = _inventory(target.public_dashboards)
    return {
        "sync_stdout": proc.stdout.strip().splitlines()[-4:] if proc.stdout else [],
        "deleted_folders": legacy,
        "deployed_inventory": inv,
        "inventory_sha256": _sha256_inventory(inv),
        "scan": scan,
    }


def manifest_entry_for(target: Target) -> dict[str, Any] | None:
    if not MANIFEST_FILE.is_file():
        return None
    manifest = json.loads(MANIFEST_FILE.read_text(encoding="utf-8"))
    dr = f"{target.start}-{target.end}"
    return manifest.get(target.contract, {}).get(target.timeframe, {}).get(dr)


def process_target(
    target: Target,
    *,
    dry_run: bool,
    state: dict[str, Any],
    force: bool,
) -> dict[str, Any]:
    prev = state["targets"].get(target.key, {})
    if prev.get("status") == "completed" and not force and not dry_run:
        scan = scan_public_dashboards(target.public_dashboards)
        return {
            "key": target.key,
            "status": "skipped_completed",
            "revalidated": scan["passed"],
            "inventory_sha256": prev.get("inventory_sha256"),
        }

    result: dict[str, Any] = {
        "key": target.key,
        "contract": target.contract,
        "timeframe": target.timeframe,
        "target_folder": target.target_folder,
        "legacy_folder": target.legacy_folder,
        "bundle": str(target.internal_bundle),
    }

    src = validate_source_bundle(target)
    result["source_validation"] = src
    if src["gate"] != "SOURCE_OK":
        result["status"] = "blocked_source"
        return result

    result["legacy_candidates"] = find_legacy_candidates(target)

    if dry_run:
        pkg = run_packager(target, dry_run=True)
        sync = run_sync(target, dry_run=True)
        me = manifest_entry_for(target)
        result.update(
            {
                "status": "dry_run_ok",
                "package": pkg,
                "sync": sync,
                "manifest_would_be": {
                    "dashboard_index": f"reports/{target.target_folder}/dashboards/index.html",
                    "public_safe": True,
                    "active": True,
                    "canonical": True,
                    "status": "CURRENT_CERTIFIED_PUBLIC",
                    "csv": [],
                },
                "current_manifest": me,
            }
        )
        return result

    pkg = run_packager(target, dry_run=False)
    result["package"] = pkg
    sync = run_sync(target, dry_run=False)
    result["sync"] = sync
    scan = scan_public_dashboards(target.public_dashboards)
    result["deploy_scan"] = scan
    me = manifest_entry_for(target)
    result["manifest_entry"] = me

    if not scan["passed"]:
        result["status"] = "blocked_public_safety"
        return result
    if not me or me.get("status") != "CURRENT_CERTIFIED_PUBLIC":
        result["status"] = "blocked_manifest"
        result["failures"] = ["manifest_not_certified"]
        return result

    result["status"] = "completed"
    result["inventory_sha256"] = sync["inventory_sha256"]
    result["completed_at"] = datetime.now(timezone.utc).isoformat()
    return result


def git_diff_guard(allowed_contracts: list[str]) -> dict[str, Any]:
    proc = subprocess.run(
        ["git", "status", "--short"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=True,
    )
    lines = [ln.strip() for ln in proc.stdout.splitlines() if ln.strip()]
    blocked: list[str] = []
    allowed_prefixes = [
        "docs/manifest.json",
        "tools/rollout_public_reports_batch.py",
        "out/audits/vwap_report_rollout_20260520/",
    ]
    for contract in allowed_contracts:
        allowed_prefixes.append(f"docs/reports/{contract}_")
        meta = CONTRACT_META[contract]
        allowed_prefixes.append(f"docs/reports/{contract}_{meta['legacy_start']}-")

    for line in lines:
        parts = line.split(maxsplit=1)
        rel = parts[-1] if parts else line
        if any(rel.startswith(p) or rel.replace("/", "\\").startswith(p) for p in allowed_prefixes):
            continue
        if rel.startswith("docs/reports/MNQZ25") or rel.startswith("docs/reports/MNQH25"):
            blocked.append(f"protected_contract_touched:{rel}")
            continue
        if rel.startswith("docs/reports/") and not any(
            rel.startswith(f"docs/reports/{c}") for c in allowed_contracts
        ):
            if "MNQZ25" in rel or "MNQH25" in rel:
                blocked.append(f"unrelated_report_change:{rel}")
            elif rel.startswith("docs/reports/MNQ"):
                blocked.append(f"ambiguous_report_change:{rel}")
        elif not any(rel.startswith(p) for p in allowed_prefixes):
            if rel and not rel.startswith("out/audits/"):
                blocked.append(f"unrelated_change:{rel}")

    return {"lines": lines, "blocked": blocked, "passed": len(blocked) == 0}


def run_local_http_checks(contracts: list[str]) -> dict[str, Any]:
    base = "http://127.0.0.1:8770"
    rows: list[dict[str, Any]] = []
    for contract in contracts:
        meta = CONTRACT_META[contract]
        for tf in TIMEFRAMES:
            url = f"{base}/reports/{contract}_{meta['start']}-{meta['end']}_{tf}/dashboards/index.html"
            try:
                import urllib.request

                with urllib.request.urlopen(url, timeout=15) as resp:
                    body = resp.read().decode("utf-8", errors="replace")
                rows.append(
                    {
                        "url": url,
                        "status": resp.status,
                        "cards": len(re.findall(r'class="dashboard-card"', body)),
                        "imgs": len(re.findall(r"<img", body, re.I)),
                    }
                )
            except Exception as exc:
                rows.append({"url": url, "error": str(exc)})
    return {"checks": rows}


def live_verify_urls(urls: list[str], *, retries: int = 3) -> list[dict[str, Any]]:
    import time
    import urllib.error
    import urllib.request

    rows: list[dict[str, Any]] = []
    for url in urls:
        last_err = ""
        ok = False
        for attempt in range(retries):
            try:
                with urllib.request.urlopen(url, timeout=90) as resp:
                    body = resp.read().decode("utf-8", errors="replace")
                rows.append(
                    {
                        "url": url,
                        "status": resp.status,
                        "cards": len(re.findall(r'class="dashboard-card"', body)),
                        "imgs": len(re.findall(r"<img", body, re.I)),
                        "placeholders": len(re.findall(r"no preview available", body, re.I)),
                        "vwap_events_href": "vwap_events.html" in body,
                        "ok": resp.status == 200,
                    }
                )
                ok = True
                break
            except urllib.error.HTTPError as exc:
                last_err = f"HTTP {exc.code}"
                if exc.code == 404 and attempt < retries - 1:
                    time.sleep(30)
                    continue
                rows.append({"url": url, "error": last_err, "ok": False})
                ok = True
                break
            except Exception as exc:
                last_err = str(exc)
                if attempt < retries - 1:
                    time.sleep(20)
        if not ok:
            rows.append({"url": url, "error": last_err or "unknown", "ok": False})
    return rows


def commit_contract(contract: str, message: str) -> dict[str, Any]:
    guard = git_diff_guard([contract])
    if not guard["passed"]:
        raise RuntimeError(f"git_diff_guard_failed:{guard['blocked']}")

    meta = CONTRACT_META[contract]
    paths = [
        "docs/manifest.json",
        f"docs/reports/{contract}_{meta['start']}-{meta['end']}_1m/",
        f"docs/reports/{contract}_{meta['start']}-{meta['end']}_5m/",
        f"docs/reports/{contract}_{meta['start']}-{meta['end']}_15m/",
        f"docs/reports/{contract}_{meta['start']}-{meta['end']}_30m/",
        f"docs/reports/{contract}_{meta['legacy_start']}-{meta['end']}_1m/",
        f"docs/reports/{contract}_{meta['legacy_start']}-{meta['end']}_5m/",
        f"docs/reports/{contract}_{meta['legacy_start']}-{meta['end']}_15m/",
        f"docs/reports/{contract}_{meta['legacy_start']}-{meta['end']}_30m/",
    ]
    for p in paths:
        full = REPO_ROOT / p
        if full.exists() or p.endswith("/"):
            subprocess.run(["git", "add", p], cwd=REPO_ROOT, check=True)

    subprocess.run(["git", "commit", "-m", message], cwd=REPO_ROOT, check=True)
    log = subprocess.run(
        ["git", "log", "-1", "--oneline"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=True,
    )
    push = subprocess.run(
        ["git", "push", "origin", "main"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
    )
    if push.returncode != 0:
        raise RuntimeError(f"push_failed:{push.stderr}")
    return {"commit": log.stdout.strip(), "push": "ok"}


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Batch MNQ H/M/U public report rollout")
    p.add_argument("--contract", action="append", dest="contracts")
    p.add_argument("--all-remaining", action="store_true")
    p.add_argument("--dry-run", action="store_true")
    p.add_argument("--resume", action="store_true")
    p.add_argument("--stop-on-failure", action="store_true")
    p.add_argument("--force", action="store_true", help="Re-run completed targets")
    p.add_argument("--approval", required=True)
    p.add_argument("--commit", action="store_true")
    p.add_argument("--commit-message", default=None)
    p.add_argument("--push", action="store_true")
    p.add_argument("--live-verify", action="store_true")
    p.add_argument("--skip-packaging", action="store_true", help="Sync only from existing staging")
    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    validate_batch_approval(args.approval)

    if args.all_remaining:
        contracts = ["MNQM25", "MNQU25"]
    elif args.contracts:
        contracts = [c.upper() for c in args.contracts]
    else:
        print("Specify --contract and/or --all-remaining", file=sys.stderr)
        return 2

    for c in contracts:
        if c in PROTECTED_CONTRACTS:
            print(f"Refusing to rollout protected contract: {c}", file=sys.stderr)
            return 2

    targets: list[Target] = []
    for contract in contracts:
        targets.extend(build_targets([contract]))

    state = load_state()
    if not state.get("protected_baselines"):
        state["protected_baselines"] = capture_protected_baselines()
    state["batch_approval"] = args.approval

    mode = "dry_run" if args.dry_run else "execute"
    summary: dict[str, Any] = {
        "mode": mode,
        "contracts": contracts,
        "target_count": len(targets),
        "results": [],
    }

    exit_code = 0
    for target in targets:
        if args.resume and not args.force:
            prev = state["targets"].get(target.key, {})
            if prev.get("status") == "completed" and not args.dry_run:
                summary["results"].append({"key": target.key, "status": "resume_skip"})
                continue

        try:
            res = process_target(target, dry_run=args.dry_run, state=state, force=args.force)
        except Exception as exc:
            res = {"key": target.key, "status": "error", "error": str(exc)}
            exit_code = 1
            if args.stop_on_failure:
                summary["results"].append(res)
                break

        state["targets"][target.key] = res
        summary["results"].append(res)

        if res.get("status") in (
            "blocked_source",
            "blocked_public_safety",
            "blocked_manifest",
            "error",
        ):
            exit_code = 1
            if args.stop_on_failure:
                break

    if not args.dry_run:
        prot_fail = verify_protected_unchanged(state)
        summary["protected_regression"] = prot_fail
        if prot_fail:
            exit_code = 1

    save_state(state)
    report_path = AUDIT_DIR / f"rollout_summary_{mode}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    report_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")

    print(f"ROLLOUT_{mode.upper()}_DONE targets={len(targets)} exit={exit_code}")
    for r in summary["results"]:
        print(f"  {r.get('key')}: {r.get('status')}")
    if prot_fail := summary.get("protected_regression"):
        print(f"  PROTECTED_REGRESSION: {prot_fail}")
    print(f"state: {STATE_FILE}")
    print(f"report: {report_path}")

    if args.commit and not args.dry_run and exit_code == 0:
        for contract in contracts:
            msg = args.commit_message or f"docs(vwap): add certified {contract} public reports"
            try:
                cr = commit_contract(contract, msg)
                print(f"COMMIT {contract}: {cr['commit']}")
            except Exception as exc:
                print(f"COMMIT_FAIL {contract}: {exc}", file=sys.stderr)
                exit_code = 1

    if args.live_verify and args.push and exit_code == 0:
        urls = []
        for contract in contracts:
            meta = CONTRACT_META[contract]
            for tf in TIMEFRAMES:
                urls.append(
                    f"https://agentad25.github.io/VWAP-REPORT/reports/"
                    f"{contract}_{meta['start']}-{meta['end']}_{tf}/dashboards/index.html"
                )
        lv = live_verify_urls(urls)
        summary["live_verify"] = lv
        save_state(state)
        for row in lv:
            if not row.get("ok") or row.get("cards") != 9:
                exit_code = 1
        print("LIVE_VERIFY", "PASS" if exit_code == 0 else "FAIL")

    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
