#!/usr/bin/env python3
"""Stage 2: Download sources and build SRPMs (spectool + rpmbuild -bs).

Reads packages.yaml and build-report.yaml for spec stage results.
Skips packages where spec stage failed. Records SRPM paths in build-report.yaml.

Must be run inside the rpm toolbox container (invoked via Makefile).

Environment variables:
  PACKAGE         Build only this package (optional, comma-separated)
  FEDORA_VERSION  Fedora version to target (default: 43)
  SKIP_PACKAGES   Skip these packages (optional, comma-separated)
  PROCEED_BUILD   Skip packages where mock stage already succeeded
  LOG_LEVEL       Logging level: DEBUG, INFO (default), WARNING, ERROR
"""

import logging
import os
import shutil
import sys
from pathlib import Path
from typing import Any

from lib.config import setup_logging
from lib.paths import ROOT, SOURCES_DIR, get_package_log_dir
from lib.reporting import status, verbose_proceed_check
from lib.subprocess_utils import run_cmd
from lib.version import nvr
from lib.yaml_utils import (
    apply_os_overrides,
    init_stage,
    save_build_status,
)


def copy_local_patches(pkg: str, meta: dict) -> None:
    patches = meta.get("source", {}).get("patches", [])
    if not patches:
        return
    SOURCES_DIR.mkdir(parents=True, exist_ok=True)
    pkg_dir = ROOT / "packages" / pkg.lower()
    for patch in patches:
        src = pkg_dir / patch
        if src.exists():
            shutil.copy2(src, SOURCES_DIR / patch)


def find_srpm(pkg: str) -> str | None:
    srpm_dir = Path.home() / "rpmbuild" / "SRPMS"
    matches = sorted(
        srpm_dir.glob(f"{pkg.lower()}-*.src.rpm"),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )
    return str(matches[0]) if matches else None


def run_for_package(
    pkg: str,
    meta: dict,
    build_status: dict,
    fedora_version: str,
    proceed: bool,
) -> bool:
    """Run SRPM build for a single package. Return True on success/skip, False on failure.

    Updates build_status["stages"]["srpm"][pkg] in-place.
    Does not call save_build_status().
    """
    meta = apply_os_overrides(meta, fedora_version)
    if meta.get("_skip"):
        print(f"  [skip] {pkg} (fedora:{fedora_version} skip)")
        build_status["stages"]["srpm"][pkg] = {
            "state": "skipped",
            "version": None,
            "path": None,
            "log": None,
            "force_run": False,
        }
        return True

    ver = nvr(str(meta["version"]), meta.get("release", 1), fedora_version)
    has_devel = "devel" in meta
    spec = ROOT / "packages" / pkg.lower() / f"{pkg.lower()}.spec"
    pkg_log_dir = get_package_log_dir(pkg)
    pkg_log_dir.mkdir(parents=True, exist_ok=True)
    log = pkg_log_dir / "10-srpm.log"
    log.unlink(missing_ok=True)

    # Skip if mock stage already succeeded AND SRPM file exists
    prior_mock_state = (
        build_status.get("stages", {}).get("mock", {}).get(pkg, {}).get("state")
    )
    prior_srpm_path = (
        build_status.get("stages", {}).get("srpm", {}).get(pkg, {}).get("path")
    )
    srpm_exists = prior_srpm_path and Path(prior_srpm_path).exists()
    if proceed and verbose_proceed_check("mock", pkg, prior_mock_state) and srpm_exists:
        status("srpm", pkg, "skip", "mock already succeeded")
        return True  # preserve existing srpm entry untouched

    # Skip if spec stage failed
    spec_stage = build_status.get("stages", {}).get("spec", {})
    spec_state = spec_stage.get(pkg, {}).get("state", "")
    if spec_state == "failed" or (spec_stage and pkg not in spec_stage):
        status("srpm", pkg, "skip", "spec failed")
        entry: dict[str, Any] = {
            "state": "skipped",
            "version": ver,
            "path": None,
            "log": None,
            "force_run": False,
        }
        if has_devel:
            entry["subpackages"] = {"devel": {"state": "skipped", "version": ver}}
        build_status["stages"]["srpm"][pkg] = entry
        return True

    ok, _, _ = run_cmd(["spectool", "-g", "-R", str(spec)], log)
    if not ok:
        status("srpm", pkg, "fail")
        entry = {
            "state": "failed",
            "version": ver,
            "path": None,
            "log": str(log.relative_to(ROOT)),
            "force_run": False,
        }
        if has_devel:
            entry["subpackages"] = {"devel": {"state": "failed", "version": ver}}
        build_status["stages"]["srpm"][pkg] = entry
        return False

    copy_local_patches(pkg, meta)
    print(f"  [RUN]  srpm: {pkg}", flush=True)
    ok, _, _ = run_cmd(["rpmbuild", "-bs", str(spec)], log)
    if not ok:
        status("srpm", pkg, "fail")
        entry = {
            "state": "failed",
            "version": ver,
            "path": None,
            "log": str(log.relative_to(ROOT)),
            "force_run": False,
        }
        if has_devel:
            entry["subpackages"] = {"devel": {"state": "failed", "version": ver}}
        build_status["stages"]["srpm"][pkg] = entry
        return False

    path = find_srpm(pkg)
    status("srpm", pkg, "ok")
    entry = {
        "state": "success",
        "version": ver,
        "path": path,
        "log": str(log.relative_to(ROOT)),
        "force_run": False,
    }
    if has_devel:
        entry["subpackages"] = {"devel": {"state": "success", "version": ver}}
    build_status["stages"]["srpm"][pkg] = entry
    return True


def main() -> None:
    fedora_version = os.environ.get("FEDORA_VERSION", "43")

    packages, build_status = init_stage("srpm")

    proceed = os.environ.get("PROCEED_BUILD", "").lower() == "true"

    failed = False
    print("\n=== srpm ===")
    for pkg, meta in packages.items():
        if not run_for_package(pkg, meta, build_status, fedora_version, proceed):
            failed = True

    save_build_status(build_status)
    if failed:
        sys.exit(1)


if __name__ == "__main__":
    try:
        setup_logging()
        main()
    except KeyboardInterrupt:
        logging.warning("User Interrupted.")
        sys.exit(130)
