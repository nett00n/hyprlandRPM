#!/usr/bin/env python3
"""Migrate packages.yaml from old flat format to the new split nested format.

The old file contains three top-level sections (repo, groups, packages) in a
single file.  The new layout splits them into three separate files:

    repo.yaml      — repository/project metadata
    groups.yaml    — logical package groupings
    packages.yaml  — per-package build definitions (nested format)

Usage:
    python3 scripts/migrate-packages-yaml.py [OPTIONS]

Options:
    --input PATH        Source file  (default: packages.yaml)
    --output-dir DIR    Write repo.yaml / groups.yaml / packages.yaml into DIR
                        (default: alongside the input file, with .new suffix)
    --overwrite         Write output files next to the input without .new suffix,
                        replacing packages.yaml in-place
    --validate-only     Skip migration; validate existing output files against input

Exit codes:
    0  success
    1  validation errors found
    2  file / parse error
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from lib.migration import migrate_data, validate_migration
from lib.paths import PACKAGES_YAML

import yaml

# Make scripts/lib importable when run from repo root or scripts/ dir
_HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(_HERE))

# ---------------------------------------------------------------------------
# YAML serialisation helpers
# ---------------------------------------------------------------------------


class _LiteralStr(str):
    """Marker so block scalars round-trip through PyYAML."""


def _literal_representer(dumper: yaml.Dumper, data: _LiteralStr):
    return dumper.represent_scalar("tag:yaml.org,2002:str", data, style="|")


def _wrap_literals(obj):
    """Recursively convert multi-line strings to LiteralStr for block style."""
    if isinstance(obj, str) and "\n" in obj:
        return _LiteralStr(obj)
    if isinstance(obj, dict):
        return {k: _wrap_literals(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_wrap_literals(v) for v in obj]
    return obj


def _make_dumper() -> type:
    dumper = yaml.Dumper
    dumper.add_representer(_LiteralStr, _literal_representer)
    return dumper


def dump_yaml(data: dict) -> str:
    prepared = _wrap_literals(data)
    return yaml.dump(
        prepared,
        Dumper=_make_dumper(),
        default_flow_style=False,
        sort_keys=False,
        allow_unicode=True,
    )


# ---------------------------------------------------------------------------
# I/O helpers
# ---------------------------------------------------------------------------


def load_yaml(path: Path) -> dict:
    if not path.exists():
        sys.exit(f"error: {path} not found")
    try:
        return yaml.safe_load(path.read_text()) or {}
    except yaml.YAMLError as exc:
        sys.exit(f"error: failed to parse {path}: {exc}")


def save_yaml(path: Path, data: dict) -> None:
    path.write_text(dump_yaml(data))


def output_paths(
    input_path: Path, output_dir: Path | None, overwrite: bool
) -> tuple[Path, Path, Path]:
    """Return (repo_path, groups_path, packages_path) for output files."""
    base = output_dir if output_dir else input_path.parent
    suffix = "" if (output_dir or overwrite) else ".new"
    return (
        base / f"repo.yaml{suffix}",
        base / f"groups.yaml{suffix}",
        base / f"packages.yaml{suffix}",
    )


# ---------------------------------------------------------------------------
# Reporting
# ---------------------------------------------------------------------------


def _print_errors(errors: list[str]) -> None:
    for e in errors:
        print(f"  FAIL  {e}", file=sys.stderr)


def _print_summary(old_pkgs: dict, errors: list[str]) -> None:
    total = len(old_pkgs)
    failing = {e.split(":")[0].strip() for e in errors if ": " in e}
    # subtract non-package errors (repo/groups)
    pkg_failing = {n for n in failing if n in old_pkgs}
    passed = total - len(pkg_failing)

    print(f"\nPackages : {total}")
    print(f"Passed   : {passed}")
    if pkg_failing:
        print(f"Failed   : {len(pkg_failing)}")
    if errors:
        print(f"Errors   : {len(errors)}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="Migrate packages.yaml to the new split nested format."
    )
    p.add_argument(
        "--input",
        type=Path,
        default=PACKAGES_YAML,
        metavar="PATH",
        help="Source file (default: packages.yaml)",
    )
    p.add_argument(
        "--output-dir",
        type=Path,
        default=None,
        metavar="DIR",
        help="Write repo.yaml/groups.yaml/packages.yaml into this directory",
    )
    p.add_argument(
        "--overwrite",
        action="store_true",
        help="Write output files in-place (no .new suffix, overwrites packages.yaml)",
    )
    p.add_argument(
        "--validate-only",
        action="store_true",
        help="Skip migration; validate existing output files against the input",
    )
    return p.parse_args()


def main() -> None:
    args = parse_args()

    input_path: Path = args.input.resolve()
    output_dir = args.output_dir.resolve() if args.output_dir else None

    if output_dir:
        output_dir.mkdir(parents=True, exist_ok=True)

    repo_path, groups_path, packages_path = output_paths(
        input_path, output_dir, args.overwrite
    )

    # --- load original ---
    print(f"Loading  : {input_path}")
    old_data = load_yaml(input_path)
    old_pkgs = old_data.get("packages") or {}

    # Detect if input is already in new format (packages at root, no 'packages:' key).
    # This happens when the migration has already been applied to packages.yaml.
    if not old_pkgs and "repo" not in old_data and "groups" not in old_data:
        print(
            f"\nInput file appears to already be in the new format "  # noqa: F541
            f"(no 'packages:', 'repo:', or 'groups:' top-level keys found).\n"  # noqa: F541
            f"Migration is a no-op — nothing to do."  # noqa: F541
        )
        sys.exit(0)

    print(f"Packages : {len(old_pkgs)} found in source")

    if args.validate_only:
        print(f"Validating existing output files:")  # noqa: F541
        print(f"  {repo_path}")
        print(f"  {groups_path}")
        print(f"  {packages_path}")
        new_repo = load_yaml(repo_path)
        new_groups = load_yaml(groups_path)
        new_packages = load_yaml(packages_path)
    else:
        # --- migrate ---
        print("Migrating...")
        new_repo, new_groups, new_packages = migrate_data(old_data)

        print(f"Writing  :")  # noqa: F541
        print(f"  {repo_path}")
        save_yaml(repo_path, new_repo)
        print(f"  {groups_path}")
        save_yaml(groups_path, new_groups)
        print(f"  {packages_path}")
        save_yaml(packages_path, new_packages)

        # re-read to ensure round-trip integrity
        print("Re-reading output for validation...")
        new_repo = load_yaml(repo_path)
        new_groups = load_yaml(groups_path)
        new_packages = load_yaml(packages_path)

    # --- validate ---
    print("Validating migration...")
    errors = validate_migration(old_data, new_repo, new_groups, new_packages)

    _print_summary(old_pkgs, errors)

    if errors:
        print("\nValidation errors:", file=sys.stderr)
        _print_errors(errors)
        sys.exit(1)

    print("\nValidation passed — all data transferred correctly.")


if __name__ == "__main__":
    main()
