"""Build pipeline orchestration utilities.

Provides helpers for:
- Computing which stages must be forced to run
- Determining if stages are cached and can be skipped
- Injecting metadata into stage entries
"""

from lib.cache import hashes_match

# Stage order for cascading force_run
STAGE_ORDER = ["spec", "vendor", "srpm", "mock", "copr"]


def compute_forced_stages(
    pkg: str, meta: dict, build_status: dict, rebuilt_packages: set[str]
) -> set[str]:
    """Compute set of stages that must run due to force_run or dependency cascade.

    Rules:
    1. If any dependency was rebuilt this run, force all stages
    2. If any stage has force_run=true, that stage and all downstream stages are forced

    Args:
        pkg: Package name
        meta: Package metadata dict
        build_status: Current build status dict
        rebuilt_packages: Set of packages that were rebuilt this run

    Returns:
        Set of stage names that must run
    """
    forced: set[str] = set()
    cascade = False

    # If any dependency was rebuilt this run, force all stages
    if any(dep in rebuilt_packages for dep in meta.get("depends_on", [])):
        return set(STAGE_ORDER)

    # Check each stage for force_run flag; once found, cascade to remaining stages
    for stage in STAGE_ORDER:
        entry = build_status.get("stages", {}).get(stage, {}).get(pkg, {})
        if cascade or entry.get("force_run", False):
            forced.add(stage)
            cascade = True
    return forced


def is_cached(
    stage: str, pkg: str, build_status: dict, new_hashes: dict, forced_stages: set[str]
) -> bool:
    """Check if a stage result is cached and can be skipped.

    A stage is cached if:
    - Its state is "success"
    - Its stored hashes match current input hashes
    - It's not in the forced_stages set

    Args:
        stage: Stage name
        pkg: Package name
        build_status: Current build status dict
        new_hashes: Newly computed input hashes for this stage
        forced_stages: Set of stages that must run (cannot be skipped)

    Returns:
        True if stage can be skipped (is cached), False if it must run
    """
    if stage in forced_stages:
        return False
    entry = build_status.get("stages", {}).get(stage, {}).get(pkg, {})
    return entry.get("state") == "success" and hashes_match(entry, new_hashes)


def inject_stage_meta(
    stage: str,
    pkg: str,
    build_status: dict,
    started_at: int,
    new_hashes: dict,
    update_hashes: bool = True,
) -> None:
    """Inject metadata into a stage entry after execution.

    Updates:
    - started_at: timestamp when stage execution started
    - hashes: input hashes (only if update_hashes=True and state is "success")
    - Clears force_run flag (one-shot, must be re-set to force again)

    Args:
        stage: Stage name
        pkg: Package name
        build_status: Build status dict (modified in-place)
        started_at: Unix timestamp when stage started
        new_hashes: Input hashes computed for this stage
        update_hashes: If False, preserve stored hashes (for proceed-skip cases)
    """
    entry = build_status.get("stages", {}).get(stage, {}).get(pkg)
    if entry is None:
        return
    entry["started_at"] = started_at
    entry.pop(
        "force_run", None
    )  # cleared after every run; operator must re-set to force again
    if update_hashes and entry.get("state") == "success":
        entry["hashes"] = new_hashes
