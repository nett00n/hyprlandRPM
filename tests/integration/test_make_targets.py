"""Integration tests for make targets and pipeline components."""

import subprocess
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch, call
import logging

import pytest

# Import using importlib to handle module names with dashes
import importlib

full_cycle = importlib.import_module("scripts.full-cycle")
stage_copr = importlib.import_module("scripts.stage-copr")
stage_vendor = importlib.import_module("scripts.stage-vendor")
stage_srpm = importlib.import_module("scripts.stage-srpm")
stage_mock = importlib.import_module("scripts.stage-mock")
stage_show_plan = importlib.import_module("scripts.stage-show-plan")

ROOT = Path(__file__).parent.parent.parent


def run_make(target: str, env=None, **kwargs) -> subprocess.CompletedProcess:
    """Run 'make <target>' in repo root, capture output."""
    return subprocess.run(
        ["make", target],
        cwd=ROOT,
        capture_output=True,
        text=True,
        env=env,
        **kwargs,
    )


class TestFullCycleFinalize:
    """Test finalize_report() with async/sync COPR builds.

    This is the critical test suite for the pipeline's exit behavior:
    - async COPR (SYNCHRONOUS_COPR_BUILD=false) with 'unknown' state should NOT fail
    - sync COPR (SYNCHRONOUS_COPR_BUILD=true) with 'failed' state SHOULD fail
    - any failed non-copr stage (spec/srpm/mock) should always fail
    - validate failures are ignored
    """

    def test_async_copr_unknown_state_not_failure(self):
        """When SYNCHRONOUS_COPR_BUILD=false, 'unknown' COPR state is valid."""
        packages = {"pkg1": {}, "pkg2": {}}
        build_status = {
            "run": {"timestamp": "2025-01-01T00:00:00+00:00"},
            "stages": {
                "spec": {
                    "pkg1": {"state": "success"},
                    "pkg2": {"state": "success"},
                },
                "copr": {
                    "pkg1": {"state": "unknown"},  # valid in async mode
                    "pkg2": {"state": "unknown"},
                },
            },
        }

        with patch.object(full_cycle, "load_build_status") as mock_load, \
             patch.object(full_cycle, "print_summary"), \
             patch.object(full_cycle, "dump_yaml_pretty"), \
             patch.object(full_cycle, "report_mock_failures"):
            mock_load.return_value = build_status

            with patch.object(Path, "write_text"):
                # Should not raise SystemExit
                full_cycle.finalize_report(
                    packages, build_status, "", synchronous_copr=False
                )

    def test_sync_copr_failed_is_failure(self):
        """When SYNCHRONOUS_COPR_BUILD=true, 'failed' COPR state is failure."""
        packages = {"pkg1": {}}
        build_status = {
            "run": {"timestamp": "2025-01-01T00:00:00+00:00"},
            "stages": {
                "copr": {
                    "pkg1": {"state": "failed"},  # failure in sync mode
                },
            },
        }

        with patch.object(full_cycle, "load_build_status") as mock_load, \
             patch.object(full_cycle, "print_summary"), \
             patch.object(full_cycle, "dump_yaml_pretty"), \
             patch.object(full_cycle, "report_mock_failures"), \
             pytest.raises(SystemExit) as exc:
            mock_load.return_value = build_status

            with patch.object(Path, "write_text"):
                full_cycle.finalize_report(
                    packages, build_status, "", synchronous_copr=True
                )

        assert exc.value.code == 1

    def test_non_copr_failed_always_fails(self):
        """Failed spec/srpm/mock stage always fails, regardless of sync setting."""
        packages = {"pkg1": {}}
        build_status = {
            "run": {"timestamp": "2025-01-01T00:00:00+00:00"},
            "stages": {
                "spec": {
                    "pkg1": {"state": "failed"},
                },
            },
        }

        with patch.object(full_cycle, "load_build_status") as mock_load, \
             patch.object(full_cycle, "print_summary"), \
             patch.object(full_cycle, "dump_yaml_pretty"), \
             patch.object(full_cycle, "report_mock_failures"), \
             pytest.raises(SystemExit) as exc:
            mock_load.return_value = build_status

            with patch.object(Path, "write_text"):
                full_cycle.finalize_report(
                    packages, build_status, "", synchronous_copr=False
                )

        assert exc.value.code == 1

    def test_validation_failure_ignored(self):
        """Validation stage failures do not cause pipeline failure."""
        packages = {"pkg1": {}}
        build_status = {
            "run": {"timestamp": "2025-01-01T00:00:00+00:00"},
            "stages": {
                "validate": {
                    "pkg1": {"state": "failed"},  # validation fails
                },
                "spec": {
                    "pkg1": {"state": "success"},
                },
            },
        }

        with patch.object(full_cycle, "load_build_status") as mock_load, \
             patch.object(full_cycle, "print_summary"), \
             patch.object(full_cycle, "dump_yaml_pretty"), \
             patch.object(full_cycle, "report_mock_failures"):
            mock_load.return_value = build_status

            with patch.object(Path, "write_text"):
                # Should not raise SystemExit
                full_cycle.finalize_report(
                    packages, build_status, "", synchronous_copr=False
                )


class TestInfoTargets:
    """Test informational make targets."""

    def test_help_target_prints_usage(self):
        """make help prints usage and exits 0."""
        result = run_make("help")

        assert result.returncode == 0
        assert "help" in result.stdout.lower() or "usage" in result.stdout.lower()

    def test_check_venv_with_existing_venv(self):
        """make check-venv exits 0 when .venv exists."""
        result = run_make("check-venv")

        # In the test environment, .venv should exist (from setup)
        assert result.returncode == 0


class TestSrpmBlocking:
    """Test SRPM stage blocking by spec failure."""

    def test_srpm_blocked_by_spec_failure(self):
        """SRPM skipped when spec stage failed."""
        pkg = "test-pkg"
        meta = {"version": "1.0.0", "release": 1}
        build_status = {
            "stages": {
                "srpm": {},
                "spec": {
                    pkg: {"state": "failed"}  # spec failed
                },
            },
        }
        fedora_version = "44"

        result = stage_srpm.run_for_package(
            pkg, meta, build_status, fedora_version, proceed=False
        )

        assert result is True
        assert build_status["stages"]["srpm"][pkg]["state"] == "skipped"
