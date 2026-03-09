"""Migration helpers: old packages.yaml flat format -> new nested format.

Field mapping (from docs/packages-yaml-migration.md):

  Old flat field        -> New location
  ---------------------    --------------------------------
  source_name           -> source.name
  commit                -> source.commit
  sources[].url         -> source.archives[]  (plain strings)
  bundled_deps          -> source.bundled_deps
  build_system          -> build.system
  source_subdir         -> build.subdir
  no_lto                -> build.no_lto
  configure_flags       -> build.configure_flags
  prep_commands         -> build.prep
  build_commands        -> build.commands
  install_commands      -> build.install
  buildarch             -> rpm.buildarch
  no_debug_package      -> rpm.no_debug_package

  version, release, license, summary, description, url  -> stay at top level
  build_requires, requires, depends_on                  -> stay at top level
  files, devel                                          -> stay at top level
"""

from __future__ import annotations

# ---------------------------------------------------------------------------
# Mapping tables
# ---------------------------------------------------------------------------

# Fields that move into the `source:` sub-object.
# old_key -> new_key_within_source (None = same name)
SOURCE_FIELDS: dict[str, str | None] = {
    "source_name": "name",
    "commit": None,  # stays as "commit"
    "sources": None,  # special: converted from [{url:...}] to [str]
    "bundled_deps": None,
}

# Fields that move into the `build:` sub-object.
BUILD_FIELDS: dict[str, str] = {
    "build_system": "system",
    "source_subdir": "subdir",
    "go_subdir": "go_subdir",
    "no_lto": "no_lto",
    "configure_flags": "configure_flags",
    "prep_commands": "prep",
    "build_commands": "commands",
    "install_commands": "install",
}

# Fields that move into the `rpm:` sub-object.
RPM_FIELDS: dict[str, str | None] = {
    "buildarch": None,
    "no_debug_package": None,
}

# Fields that stay at the top level of each package entry.
TOP_LEVEL_FIELDS = (
    "version",
    "release",
    "license",
    "summary",
    "description",
    "url",
    "build_requires",
    "requires",
    "depends_on",
    "files",
    "devel",
)

# All known old-format fields (used to detect unknowns during validation).
ALL_OLD_FIELDS: frozenset[str] = frozenset(
    list(TOP_LEVEL_FIELDS) + list(SOURCE_FIELDS) + list(BUILD_FIELDS) + list(RPM_FIELDS)
)


# ---------------------------------------------------------------------------
# Migration
# ---------------------------------------------------------------------------


def migrate_package(old: dict) -> dict:
    """Convert a single old-format package dict to the new nested format."""
    new: dict = {}

    # --- top-level identity + dependency fields ---
    for field in TOP_LEVEL_FIELDS:
        if field in old:
            new[field] = old[field]

    # --- source: sub-object ---
    source: dict = {}
    for old_key, new_key in SOURCE_FIELDS.items():
        if old_key not in old:
            continue
        dest = new_key if new_key is not None else old_key

        if old_key == "sources":
            # [{url: "..."}, ...] -> ["...", ...]
            source["archives"] = [
                entry["url"] if isinstance(entry, dict) else entry
                for entry in old["sources"]
            ]
        else:
            source[dest] = old[old_key]

    if source:
        new["source"] = source

    # --- build: sub-object ---
    build: dict = {}
    for old_key, new_key in BUILD_FIELDS.items():
        if old_key in old:
            build[new_key] = old[old_key]
    if build:
        new["build"] = build

    # --- rpm: sub-object ---
    rpm: dict = {}
    for old_key, new_key in RPM_FIELDS.items():
        if old_key in old:
            dest = new_key if new_key is not None else old_key
            rpm[dest] = old[old_key]
    if rpm:
        new["rpm"] = rpm

    return new


def migrate_data(old_data: dict) -> tuple[dict, dict, dict]:
    """Migrate the full packages.yaml dict.

    Returns (repo, groups, packages) — three separate dicts to be written
    to repo.yaml, groups.yaml, and packages.yaml respectively.
    """
    repo = old_data.get("repo") or {}
    groups = old_data.get("groups") or {}
    packages = {
        name: migrate_package(pkg)
        for name, pkg in (old_data.get("packages") or {}).items()
    }
    return repo, groups, packages


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------


class ValidationError(Exception):
    pass


def _get_nested(d: dict, *keys: str):
    """Walk a nested dict by keys; return (value, True) or (None, False)."""
    cur = d
    for k in keys:
        if not isinstance(cur, dict) or k not in cur:
            return None, False
        cur = cur[k]
    return cur, True


def validate_package(name: str, old: dict, new: dict) -> list[str]:
    """Return a list of discrepancy messages for one package."""
    errors: list[str] = []

    def check(label: str, old_val, new_path: tuple[str, ...]):
        new_val, found = _get_nested(new, *new_path)
        if not found:
            errors.append(f"{name}: missing {'.'.join(new_path)} (old: {old_key!r})")
            return
        if old_val != new_val:
            errors.append(
                f"{name}: mismatch at {'.'.join(new_path)}: "
                f"old={old_val!r} new={new_val!r}"
            )

    for old_key, value in old.items():
        # --- top-level fields ---
        if old_key in TOP_LEVEL_FIELDS:
            check(old_key, value, (old_key,))

        # --- source fields ---
        elif old_key == "sources":
            expected = [
                entry["url"] if isinstance(entry, dict) else entry for entry in value
            ]
            check(old_key, expected, ("source", "archives"))

        elif old_key == "source_name":
            check(old_key, value, ("source", "name"))

        elif old_key == "commit":
            check(old_key, value, ("source", "commit"))

        elif old_key == "bundled_deps":
            check(old_key, value, ("source", "bundled_deps"))

        # --- build fields ---
        elif old_key in BUILD_FIELDS:
            new_key = BUILD_FIELDS[old_key]
            check(old_key, value, ("build", new_key))

        # --- rpm fields ---
        elif old_key in RPM_FIELDS:
            new_key = RPM_FIELDS[old_key] or old_key
            check(old_key, value, ("rpm", new_key))

        else:
            errors.append(f"{name}: unrecognised old field {old_key!r} — not migrated")

    # check for stray fields in the new package that have no old counterpart
    all_new_top = set(new.keys()) - {"source", "build", "rpm"}
    expected_top = set(TOP_LEVEL_FIELDS) & set(old.keys())
    stray = all_new_top - expected_top
    if stray:
        errors.append(f"{name}: unexpected top-level fields in migrated entry: {stray}")

    return errors


def validate_migration(
    old_data: dict,
    new_repo: dict,
    new_groups: dict,
    new_packages: dict,
) -> list[str]:
    """Validate the full migration; return all error messages."""
    errors: list[str] = []

    # repo and groups must be identical to the originals
    if old_data.get("repo") != new_repo:
        errors.append("repo: content differs from source")

    if old_data.get("groups") != new_groups:
        errors.append("groups: content differs from source")

    old_pkgs = old_data.get("packages") or {}

    missing = set(old_pkgs) - set(new_packages)
    for name in sorted(missing):
        errors.append(f"{name}: package missing from migrated data")

    extra = set(new_packages) - set(old_pkgs)
    for name in sorted(extra):
        errors.append(f"{name}: unexpected package in migrated data")

    for name in sorted(set(old_pkgs) & set(new_packages)):
        errors.extend(validate_package(name, old_pkgs[name], new_packages[name]))

    return errors
