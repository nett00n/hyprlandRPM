"""Gitmodules parsing and submodule utilities."""

import configparser
import subprocess
import sys
from pathlib import Path


def parse_gitmodules(path: Path) -> list[dict]:
    """Parse .gitmodules and return list of {name, path, url} dicts."""
    parser = configparser.ConfigParser(strict=False)
    parser.read(path)
    modules = []
    for section in parser.sections():
        name = section.removeprefix('submodule "').removesuffix('"')
        modules.append(
            {
                "name": name,
                "path": parser[section].get("path", ""),
                "url": parser[section].get("url", ""),
            }
        )
    return modules


def fetch_tags(url: str) -> list[str]:
    """Fetch all tags from a remote git URL."""
    try:
        result = subprocess.run(
            ["git", "ls-remote", "--tags", url],
            capture_output=True,
            text=True,
            timeout=30,
        )
        if result.returncode != 0:
            print(f"  warning: failed to fetch tags from {url}", file=sys.stderr)
            return []
        tags = []
        for line in result.stdout.splitlines():
            parts = line.split("\t", 1)
            if len(parts) != 2:
                continue
            ref = parts[1]
            if ref.endswith("^{}"):
                continue
            tags.append(ref.removeprefix("refs/tags/"))
        return tags
    except subprocess.TimeoutExpired:
        print(f"  warning: timeout fetching tags from {url}", file=sys.stderr)
        return []


def resolve_module(modules: list[dict], name: str) -> dict | None:
    """Find a module whose path's last component matches name (case-insensitive)."""
    name_lower = name.lower()
    for mod in modules:
        if Path(mod["path"]).name.lower() == name_lower:
            return mod
    return None


def get_tag_info(repo: Path, version: str) -> dict | None:
    """Return {published_at, body} for a version tag in the submodule.

    Tries annotated tag message first (git cat-file tag), then falls back to
    the commit log message. Returns None if the tag does not exist.
    """
    import datetime

    tag = f"v{version}"

    check = subprocess.run(
        ["git", "-C", str(repo), "tag", "-l", tag],
        capture_output=True,
        text=True,
    )
    if not check.stdout.strip():
        return None

    published_at = None
    body = None

    # Try annotated tag first
    cat = subprocess.run(
        ["git", "-C", str(repo), "cat-file", "tag", tag],
        capture_output=True,
        text=True,
    )
    if cat.returncode == 0 and cat.stdout:
        lines = cat.stdout.splitlines()
        blank = next((i for i, line in enumerate(lines) if line == ""), len(lines))
        header_lines = lines[:blank]
        message_lines = lines[blank + 1 :]
        for line in header_lines:
            if line.startswith("tagger "):
                parts = line.split()
                try:
                    ts = int(parts[-2])
                    published_at = datetime.datetime.fromtimestamp(
                        ts, tz=datetime.timezone.utc
                    ).isoformat()
                except (ValueError, IndexError):
                    pass
                break
        body = "\n".join(message_lines).strip() or None

    # Fall back to commit log for missing date or body
    if not published_at or not body:
        log = subprocess.run(
            ["git", "-C", str(repo), "log", "-1", "--format=%aI%n%B", tag],
            capture_output=True,
            text=True,
        )
        if log.returncode == 0 and log.stdout:
            log_lines = log.stdout.splitlines()
            if not published_at and log_lines:
                published_at = log_lines[0].strip()
            if not body:
                body = "\n".join(log_lines[1:]).strip() or None

    if not published_at:
        return None
    return {"published_at": published_at, "body": body}


def get_commit_info(repo: Path, ref: str = "HEAD") -> dict | None:
    """Return {published_at, body} from a commit's log message.

    published_at is the author ISO timestamp; body is the commit message body.
    """
    import datetime

    log = subprocess.run(
        ["git", "-C", str(repo), "log", "-1", "--format=%aI%n%B", ref],
        capture_output=True,
        text=True,
    )
    if log.returncode != 0 or not log.stdout:
        return None
    lines = log.stdout.splitlines()
    published_at = lines[0].strip() if lines else None
    body = "\n".join(lines[1:]).strip() or None
    if not published_at:
        return None
    # Validate it looks like a date
    try:
        datetime.datetime.fromisoformat(published_at)
    except ValueError:
        return None
    return {"published_at": published_at, "body": body}


def get_changelog_info(
    repo: Path, version: str, commit_hash: str | None = None
) -> dict | None:
    """Return {published_at, body} for changelog generation.

    Tries the version tag first (annotated or lightweight).
    Falls back to the commit log — using commit_hash if given, else HEAD.
    """
    tag_info = get_tag_info(repo, version)
    if tag_info:
        return tag_info
    ref = commit_hash or "HEAD"
    return get_commit_info(repo, ref)


def get_submodule_commit(repo: Path) -> tuple[str, str, str] | None:
    """Return (full_hash, short_hash, date_YYYYMMDD) for HEAD of the submodule."""
    try:
        result = subprocess.run(
            [
                "git",
                "-C",
                str(repo),
                "log",
                "-1",
                "--format=%H %cd",
                "--date=format:%Y%m%d",
            ],
            capture_output=True,
            text=True,
            check=True,
        )
        parts = result.stdout.strip().split()
        if len(parts) < 2:
            return None
        full_hash, date_str = parts[0], parts[1]
        return full_hash, full_hash[:7], date_str
    except Exception:
        return None
