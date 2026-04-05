"""COPR (Fedora Copr) build service utilities.

Provides functions for:
- Credentials verification
- Build ID parsing from copr-cli output
- Repository slug validation
- Build status polling
"""

import re
import sys

from lib.subprocess_utils import run_cmd

COPR_BUILD_URL = "https://copr.fedorainfracloud.org/coprs/build/{}/"
TERMINAL_STATES = {"success", "failed"}


def parse_build_id(output: str) -> int | None:
    """Extract build ID from copr-cli build output.

    Searches for "Created builds:" line and extracts the integer ID.

    Args:
        output: stdout from 'copr-cli build' command

    Returns:
        Build ID as int, or None if not found
    """
    for line in output.splitlines():
        if "Created builds:" in line:
            try:
                return int(line.split()[-1])
            except (ValueError, IndexError):
                pass
    return None


def check_copr_credentials() -> bool:
    """Verify COPR credentials are valid using copr-cli whoami.

    Prints helpful error messages on failure.

    Returns:
        True if credentials are valid, False otherwise
    """
    ok, stdout, stderr = run_cmd(["copr-cli", "whoami"])
    if not ok:
        print("error: COPR credentials are invalid or missing", file=sys.stderr)
        print(
            "  Set up credentials at: https://copr.fedorainfracloud.org/api/",
            file=sys.stderr,
        )
        print("  Save to: ~/.config/copr/copr.conf", file=sys.stderr)
        if stderr:
            print(f"  Details: {stderr.strip()}", file=sys.stderr)
        return False
    return True


def validate_copr_repo(copr_repo: str) -> bool:
    """Validate COPR repository slug format.

    Expected format: owner/repo (e.g., nett00n/hyprland)

    Args:
        copr_repo: Repository slug to validate

    Returns:
        True if format is valid, False otherwise
    """
    return bool(re.match(r"^[\w-]+/[\w.-]+$", copr_repo))


def poll_copr_status(stages: dict, packages_list: list[str]) -> bool:
    """Poll COPR status for packages with non-terminal states using copr-cli.

    Queries the status of pending builds and updates their state in the
    provided stages dict. Skips packages that don't have a build_id or are
    already in terminal states (success/failed).

    Args:
        stages: build_status["stages"] dict with copr stage entries
        packages_list: List of package names to check

    Returns:
        True if any status was updated, False otherwise
    """
    updated = False
    copr_stage = stages.get("copr") or {}

    for pkg in packages_list:
        entry = copr_stage.get(pkg, {})
        build_id = entry.get("build_id")
        state = entry.get("state")

        # Only poll if we have a build_id and the state is not terminal
        if not build_id or state in TERMINAL_STATES:
            continue

        # Query copr-cli status
        ok, stdout, _ = run_cmd(["copr-cli", "status", str(build_id)])
        if not ok:
            continue

        # Parse output to get state (status command outputs "succeeded" or "failed" etc)
        new_state = None
        for line in stdout.splitlines():
            line_lower = line.lower()
            if "succeeded" in line_lower:
                new_state = "success"
                break
            elif "failed" in line_lower:
                new_state = "failed"
                break

        # Update if status changed
        if new_state and new_state != state:
            entry["state"] = new_state
            updated = True

    return updated
