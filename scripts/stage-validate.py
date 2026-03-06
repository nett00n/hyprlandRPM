#!/usr/bin/env python3
"""Stage 0: Validate packages.yaml entries.

Checks required fields, deprecated sections, file placement, build_system
validity, and .gitmodules conventions.

Must be run inside the rpm toolbox container (invoked via Makefile).

Environment variables:
  PACKAGE         Validate only this package (optional, comma-separated)
"""

import os
import sys

from lib.gitmodules import parse_gitmodules
from lib.paths import GITMODULES, ROOT
from lib.yaml_utils import (
    filter_packages,
    get_packages,
    load_build_status,
    load_packages_yaml,
    save_build_status,
)

REQUIRED_FIELDS = ["version", "license", "summary", "description", "url", "sources"]
VALID_BUILD_SYSTEMS = {"cmake", "meson", "autotools", "make", "python"}
DEVEL_INDICATORS = ["%{_includedir}", "pkgconfig/", "/cmake/"]


def validate_package(
    name: str, meta: dict, all_packages: dict
) -> tuple[list[str], list[str]]:
    """Return (errors, warnings) for a single package entry."""
    errors: list[str] = []
    warnings: list[str] = []

    # Required fields
    for field in REQUIRED_FIELDS:
        if not meta.get(field):
            errors.append(f"missing required field: {field}")

    # Deprecated debuginfo section
    if "debuginfo" in meta:
        errors.append(
            "deprecated 'debuginfo' section present — rely on RPM auto-generation"
        )

    # build_system validity
    bs = meta.get("build_system", "")
    if bs and bs != "FIXME" and bs not in VALID_BUILD_SYSTEMS:
        errors.append(
            f"invalid build_system '{bs}' (must be one of: {', '.join(sorted(VALID_BUILD_SYSTEMS))})"
        )

    # Devel files in wrong place (main files section)
    main_files = meta.get("files", []) or []
    for f in main_files:
        for indicator in DEVEL_INDICATORS:
            if indicator in str(f):
                warnings.append(
                    f"devel path '{f}' found in main files — should be in devel.files"
                )
                break

    # Validate depends_on entries
    pkg_by_lower = {k.lower(): k for k in all_packages}
    depends_on = meta.get("depends_on")
    if depends_on is not None:
        for dep in depends_on:
            if dep.lower() not in pkg_by_lower:
                errors.append(f"depends_on: '{dep}' is not a known package")

    # Warn if build_requires has local refs not covered by depends_on
    depends_on_lower = {d.lower() for d in (depends_on or [])}
    for req in meta.get("build_requires", []) or []:
        if not isinstance(req, str):
            continue
        base: str | None = None
        if req.endswith("-devel"):
            base = req[:-6].lower()
        elif req.startswith("pkgconfig(") and req.endswith(")"):
            base = req[10:-1].lower()
        if base and base in pkg_by_lower and pkg_by_lower[base] != name:
            if base not in depends_on_lower:
                resolved = pkg_by_lower[base]
                warnings.append(
                    f"build_requires '{req}' references local package '{resolved}'"
                    " — add to depends_on"
                )

    return errors, warnings


def validate_group_membership(all_packages: dict) -> tuple[list[str], list[str]]:
    """Check every package appears in at least one group's packages list."""
    errors: list[str] = []
    warnings: list[str] = []

    data = load_packages_yaml()
    groups = data.get("groups") or {}
    grouped: set[str] = set()
    for group_meta in groups.values():
        for pkg in group_meta.get("packages") or []:
            grouped.add(pkg)

    for pkg in all_packages:
        if pkg not in grouped:
            errors.append(f"package '{pkg}' is not listed in any group")

    return errors, warnings


def validate_gitmodules(root_path=ROOT) -> tuple[list[str], list[str]]:
    """Validate .gitmodules: paths under submodules/, URLs use https."""
    errors: list[str] = []
    warnings: list[str] = []
    gitmodules_path = GITMODULES
    if not gitmodules_path.exists():
        return errors, warnings

    modules = parse_gitmodules(gitmodules_path)
    for mod in modules:
        path = mod.get("path", "")
        url = mod.get("url", "")
        if path and not path.startswith("submodules/"):
            errors.append(
                f".gitmodules: submodule '{mod['name']}' path '{path}' does not start with submodules/"
            )
        if url and not url.startswith("https://"):
            errors.append(
                f".gitmodules: submodule '{mod['name']}' URL '{url}' is not https://"
            )

    return errors, warnings


def main() -> None:
    package_filter = os.environ.get("PACKAGE", "")

    all_packages = get_packages()
    packages = filter_packages(all_packages, package_filter)

    build_status = load_build_status()
    build_status.setdefault("stages", {})["validate"] = {}

    total_errors = 0
    total_warnings = 0
    failed = False

    print("\n=== validate ===")

    for pkg, meta in packages.items():
        errors, warnings = validate_package(pkg, meta, all_packages)
        total_errors += len(errors)
        total_warnings += len(warnings)

        if errors:
            failed = True
            state = "failed"
            print(f"  [FAIL] {pkg}")
            for e in errors:
                print(f"    error: {e}")
        elif warnings:
            state = "success"
            print(f"  [ ok ] {pkg} ({len(warnings)} warning(s))")
        else:
            state = "success"
            print(f"  [ ok ] {pkg}")

        for w in warnings:
            print(f"    warn: {w}")

        build_status["stages"]["validate"][pkg] = {
            "state": state,
            "errors": len(errors),
            "warnings": len(warnings),
        }

    # Validate group membership (global, not per-package)
    grp_errors, grp_warnings = validate_group_membership(all_packages)
    if grp_errors:
        failed = True
        print("  [FAIL] groups membership")
        for e in grp_errors:
            print(f"    error: {e}")
    else:
        print("  [ ok ] groups membership")
    total_errors += len(grp_errors)
    total_warnings += len(grp_warnings)

    # Validate .gitmodules (global, not per-package)
    gm_errors, gm_warnings = validate_gitmodules(ROOT)
    if gm_errors:
        failed = True
        print("  [FAIL] .gitmodules")
        for e in gm_errors:
            print(f"    error: {e}")
    elif gm_warnings:
        print(f"  [ ok ] .gitmodules ({len(gm_warnings)} warning(s))")
    else:
        print("  [ ok ] .gitmodules")
    for w in gm_warnings:
        print(f"    warn: {w}")
    total_errors += len(gm_errors)
    total_warnings += len(gm_warnings)

    save_build_status(build_status)

    if total_warnings:
        print(f"\n  {total_warnings} warning(s) total")
    if failed:
        print(f"\n  {total_errors} error(s) found — validation failed", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nUser Interrupted.", file=sys.stderr)
        sys.exit(130)
