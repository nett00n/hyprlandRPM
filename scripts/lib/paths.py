"""Canonical path constants for the hyprland-copr repository."""

from pathlib import Path

# scripts/lib/ -> scripts/ -> repo root
ROOT = Path(__file__).resolve().parent.parent.parent
PACKAGES_YAML = ROOT / "packages.yaml"
REPO_YAML = ROOT / "repo.yaml"
GROUPS_YAML = ROOT / "groups.yaml"
GITMODULES = ROOT / ".gitmodules"
LOG_DIR = ROOT / "logs"
BUILD_LOG_DIR = LOG_DIR / "build"
LOCAL_REPO = ROOT / "local-repo"
TEMPLATE_DIR = ROOT / "templates"
GITHUB_RELEASE_CACHE = ROOT / "cache" / "github-releases.json"


def get_package_log_dir(pkg_name: str) -> Path:
    """Return the build log directory for a package."""
    return BUILD_LOG_DIR / pkg_name
