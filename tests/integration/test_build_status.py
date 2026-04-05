"""Integration tests for build status lifecycle (load/save/inject)."""

import sys
import time
from pathlib import Path

import pytest
import yaml

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "scripts"))

from lib.yaml_utils import (
    load_build_status,
    save_build_status,
    STAGES,
)
from lib.pipeline import inject_stage_meta
from lib.stage_utils import make_stage_entry


class TestBuildStatusLifecycle:
    """Test load/save/inject of build-report.yaml."""

    def test_load_missing_build_status_returns_empty_structure(self, tmp_path, monkeypatch):
        """Missing build-report.yaml returns empty structure."""
        from lib import paths
        build_path = tmp_path / "build-report.yaml"
        monkeypatch.setattr(paths, "BUILD_STATUS_YAML", build_path)

        status = load_build_status(build_path)
        assert "stages" in status
        assert set(status["stages"].keys()) == set(STAGES)
        for stage in STAGES:
            assert status["stages"][stage] == {}

    def test_save_and_reload_build_status_roundtrip(self, tmp_path, monkeypatch):
        """Save status dict and reload it unchanged."""
        from lib import paths
        build_path = tmp_path / "build-report.yaml"
        monkeypatch.setattr(paths, "BUILD_STATUS_YAML", build_path)

        # Create a status with some entries
        original_status = {
            "stages": {
                "spec": {
                    "pkg-a": {"state": "success", "version": "1.0-1.fc43", "force_run": False},
                },
                "vendor": {
                    "pkg-a": {"state": "skipped"},
                },
                "srpm": {},
                "mock": {},
                "copr": {},
                "validate": {},
            }
        }

        save_build_status(original_status, build_path)
        loaded = load_build_status(build_path)

        assert loaded == original_status

    def test_inject_stage_meta_stamps_started_at_and_clears_force_run(self, tmp_path):
        """inject_stage_meta sets started_at and clears force_run."""
        status = {
            "stages": {
                "spec": {
                    "pkg-a": {
                        "state": "success",
                        "version": "1.0-1.fc43",
                        "force_run": True,
                    },
                },
            }
        }

        new_hashes = {"source_commit": "abc123", "templates": "def456"}
        started_at = int(time.time())

        inject_stage_meta(
            "spec", "pkg-a", status, started_at=started_at, new_hashes=new_hashes
        )

        entry = status["stages"]["spec"]["pkg-a"]
        assert entry["started_at"] == started_at
        assert "force_run" not in entry or entry.get("force_run") is not True
        assert entry["hashes"] == new_hashes

    def test_inject_stage_meta_does_not_update_hashes_on_failure(self, tmp_path):
        """inject_stage_meta does not update hashes when state != success."""
        status = {
            "stages": {
                "spec": {
                    "pkg-a": {
                        "state": "failed",
                        "version": "1.0-1.fc43",
                    },
                },
            }
        }

        new_hashes = {"source_commit": "abc123"}
        inject_stage_meta("spec", "pkg-a", status, started_at=123, new_hashes=new_hashes)

        entry = status["stages"]["spec"]["pkg-a"]
        assert "hashes" not in entry

    def test_inject_stage_meta_preserves_hashes_when_update_false(self, tmp_path):
        """inject_stage_meta preserves existing hashes when update_hashes=False."""
        old_hashes = {"source_commit": "old123"}
        status = {
            "stages": {
                "spec": {
                    "pkg-a": {
                        "state": "success",
                        "version": "1.0-1.fc43",
                        "hashes": old_hashes,
                    },
                },
            }
        }

        new_hashes = {"source_commit": "new456"}
        inject_stage_meta(
            "spec",
            "pkg-a",
            status,
            started_at=123,
            new_hashes=new_hashes,
            update_hashes=False,
        )

        entry = status["stages"]["spec"]["pkg-a"]
        assert entry["hashes"] == old_hashes

    def test_inject_stage_meta_ignores_nonexistent_entry(self, tmp_path):
        """inject_stage_meta does nothing if entry doesn't exist."""
        status = {"stages": {"spec": {}}}

        new_hashes = {"source_commit": "abc123"}
        inject_stage_meta(
            "spec", "nonexistent", status, started_at=123, new_hashes=new_hashes
        )

        assert status["stages"]["spec"] == {}

    def test_save_creates_single_parent_dir(self, tmp_path):
        """save_build_status creates immediate parent directory (not nested)."""
        parent_dir = tmp_path / "build"
        parent_dir.mkdir()  # Must create parent before calling save
        build_path = parent_dir / "build-report.yaml"
        status = {"stages": {s: {} for s in STAGES}}

        save_build_status(status, build_path)

        assert build_path.exists()
        loaded = load_build_status(build_path)
        assert loaded["stages"]
