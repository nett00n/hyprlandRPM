"""Stage pipeline utilities.

Provides helpers for building stage entry dicts with consistent structure.
"""

from typing import Any


def make_stage_entry(
    state: str,
    version: str,
    has_devel: bool = False,
    **extras: Any,
) -> dict[str, Any]:
    """Build a stage entry dict with consistent structure.

    Each stage (srpm, mock, copr, etc.) records per-package results with
    common fields (state, version, force_run) and stage-specific extras.

    Args:
        state: State string ("success", "failed", "skipped", "unknown")
        version: NVR (name-version-release) string
        has_devel: Whether to include devel subpackage entry
        **extras: Additional stage-specific fields (log, path, build_id, etc.)

    Returns:
        Dictionary with stage entry structure

    Example:
        >>> entry = make_stage_entry("success", "pkg-1.0-1.fc43", has_devel=True, path="/path")
        >>> entry["state"]
        'success'
        >>> entry["subpackages"]["devel"]["state"]
        'success'
    """
    entry: dict[str, Any] = {
        "state": state,
        "version": version,
        "force_run": False,
        **extras,
    }

    if has_devel:
        entry["subpackages"] = {
            "devel": {
                "state": state,
                "version": version,
            }
        }

    return entry
