#!/usr/bin/env python3
"""Stage: Show build plan - display what will run, cache, or skip.

Prints a table showing per-package per-stage status: run, cached, or skipped.

Must be run inside the rpm toolbox container (invoked via Makefile).

Environment variables:
  PACKAGE         If set, show only these packages (comma-separated, optional)
  SKIP_PACKAGES   If set, exclude these packages (comma-separated, optional)
  COPR_REPO       If set, include copr stage in plan (optional)
"""

import os
import sys

from lib.yaml_utils import (
    STAGES,
    filter_packages,
    get_packages,
    load_build_status,
    skip_packages,
)


def show_plan(
    package: str = "", skip_packages_arg: str = "", copr_repo: str = ""
) -> None:
    """Display build plan as a table.

    Args:
        package: If set, show only these package(s). Comma-separated. If empty, show all.
        skip_packages_arg: If set, exclude these package(s). Comma-separated.
        copr_repo: If set, include copr stage in plan (optional)
    """
    try:
        build_status = load_build_status()
    except FileNotFoundError:
        print(
            "error: build-report.yaml not found (run after validate stage)",
            file=sys.stderr,
        )
        sys.exit(1)

    all_packages = get_packages()
    all_packages = filter_packages(all_packages, package)
    all_packages = skip_packages(all_packages, skip_packages_arg)

    stages = STAGES if copr_repo else [s for s in STAGES if s != "copr"]

    # Status labels for display
    status_label = {
        "success": "cache",
        "failed": "retry",
        "skipped": "skip",
        None: "run",
    }

    print("\n=== Build Plan ===")
    print(f"  {'package':<30} " + "  ".join(f"{s:<8}" for s in stages))
    print("  " + "-" * (30 + 10 * len(stages)))

    for pkg in all_packages:
        if pkg not in build_status.get("stages", {}).get("validate", {}):
            continue

        row = []
        for stage in stages:
            state = (
                build_status.get("stages", {}).get(stage, {}).get(pkg, {}).get("state")
            )
            label = status_label.get(state, state or "run")
            row.append(f"{label:<8}")

        print(f"  {pkg:<30} " + "  ".join(row))

    print()


if __name__ == "__main__":
    package = os.environ.get("PACKAGE", "")
    skip_packages_arg = os.environ.get("SKIP_PACKAGES", "")
    copr_repo = os.environ.get("COPR_REPO", "")
    show_plan(package, skip_packages_arg, copr_repo)
