"""Rust crate vendoring for stage-vendor.py - ABANDONED FOR NOW.

REASON: Rust git dependencies cannot be properly vendored for offline COPR builds.
- cargo vendor downloads git deps into vendor/
- But Cargo cannot locate them in offline mode without complex configuration
- Cargo.lock patching to path dependencies is error-prone
- git+file:// URLs require git repos in vendor (increases size, complexity)

APPROACH: Switch to canonical COPR/Fedora strategy:
- Build all dependencies as separate RPM packages
- Use system-installed crates instead of vendoring
- This follows Fedora packaging guidelines and works reliably

STATUS: vendor_rust.py is kept for reference but NOT USED.
Rust packages are now built using COPR's native dependency system.
"""

import shutil
import subprocess
import tarfile
from pathlib import Path
from typing import Callable


class VendorError(Exception):
    pass


def _log_fn(log_path: Path | None) -> Callable[[str], None]:
    """Return a logging function that writes to stdout and optionally to a file."""

    def _log(msg: str) -> None:
        print(f"  {msg}", flush=True)
        if log_path:
            with open(log_path, "a") as fh:
                fh.write(msg + "\n")

    return _log


def generate(
    pkg_name: str,
    pkg_meta: dict,
    tmpdir: Path,
    src_dir: Path,
    output: Path,
    log_path: Path | None = None,
) -> None:
    """Generate vendor tarball for a Rust package using cargo vendor.

    Raises VendorError on failure.

    TODO: Handle git dependencies properly:
    - Parse Cargo.lock and identify git sources
    - Either patch Cargo.lock to use path dependencies
    - Or configure git+file:// URLs in .cargo/config
    """
    # Check if cargo is available
    try:
        result = subprocess.run(
            ["cargo", "--version"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        if result.returncode != 0:
            raise VendorError(f"cargo check failed: {result.stderr.strip()}")
    except FileNotFoundError:
        raise VendorError("'cargo' not found in PATH (or not executable)")

    _log = _log_fn(log_path)

    rust_subdir = pkg_meta.get("build", {}).get("rust_subdir", "")
    if rust_subdir:
        src_dir = src_dir / rust_subdir

    if not (src_dir / "Cargo.toml").exists():
        raise VendorError(f"no Cargo.toml in extracted source at {src_dir}")

    vendor_dir = src_dir / "vendor"
    if vendor_dir.exists():
        shutil.rmtree(vendor_dir)

    _log("running: cargo vendor")
    result = subprocess.run(
        ["cargo", "vendor", str(vendor_dir)],
        cwd=src_dir,
        capture_output=True,
        text=True,
    )
    if log_path:
        with open(log_path, "a") as fh:
            if result.stdout:
                fh.write(result.stdout)
            if result.stderr:
                fh.write(result.stderr)
            fh.write(f"[exit: {result.returncode}]\n\n")
    if result.returncode != 0:
        raise VendorError(f"cargo vendor failed: {result.stderr.strip()}")

    if not vendor_dir.exists():
        raise VendorError("cargo vendor produced no vendor/ directory")

    cargo_config_dir = src_dir / ".cargo"
    cargo_config_dir.mkdir(exist_ok=True)
    cargo_config = cargo_config_dir / "config.toml"

    # Create basic .cargo/config.toml for vendored dependencies
    # Force offline mode and replace crates-io source with vendored
    config_content = """[source.crates-io]
replace-with = 'vendored-sources'

[source.vendored-sources]
directory = 'vendor'

[net]
offline = true
"""
    cargo_config.write_text(config_content)
    _log(f"created .cargo/config.toml at {cargo_config}")

    _log(f"packing vendor/ -> {output.name}")
    with tarfile.open(output, "w:gz") as tf:
        tf.add(vendor_dir, arcname="vendor")
        _log("added vendor/ directory")
        tf.add(cargo_config, arcname=".cargo/config.toml")
        _log("added .cargo/config.toml")
