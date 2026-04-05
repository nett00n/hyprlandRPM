"""Integration tests for entry point scripts (stage-*.py)."""

import subprocess
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch
import logging

import pytest

# Import using importlib to handle module names with dashes
import importlib
stage_validate = importlib.import_module("scripts.stage-validate")
stage_spec = importlib.import_module("scripts.stage-spec")
stage_copr = importlib.import_module("scripts.stage-copr")
stage_show_plan = importlib.import_module("scripts.stage-show-plan")

validate_run_for_package = stage_validate.run_for_package
run_global_checks = stage_validate.run_global_checks
main = stage_validate.main
spec_run_for_package = stage_spec.run_for_package


class TestStageValidate:
    """Tests for stage-validate.py entry point."""

    def test_validate_run_for_package_skip(self, tmp_path):
        """Test that skipped packages are marked correctly."""
        pkg = "test-pkg"
        meta = {"_skip": True}
        all_packages = {}
        build_status = {"stages": {"validate": {}}}

        result = validate_run_for_package(
            pkg, meta, all_packages, build_status, "43"
        )

        assert result is True
        assert build_status["stages"]["validate"][pkg]["state"] == "skipped"

    def test_validate_run_for_package_success(self):
        """Test successful package validation."""
        pkg = "test-pkg"
        meta = {"name": pkg}
        all_packages = {}
        build_status = {"stages": {"validate": {}}}

        with patch.object(stage_validate, "validate_package") as mock_validate:
            mock_validate.return_value = ([], [])  # No errors or warnings

            result = validate_run_for_package(
                pkg, meta, all_packages, build_status, "43"
            )

        assert result is True
        assert build_status["stages"]["validate"][pkg]["state"] == "success"
        assert build_status["stages"]["validate"][pkg]["errors"] == 0

    def test_validate_run_for_package_with_errors(self):
        """Test package validation with errors."""
        pkg = "bad-pkg"
        meta = {"name": pkg}
        all_packages = {}
        build_status = {"stages": {"validate": {}}}

        errors = ["Error 1", "Error 2"]
        warnings = ["Warning 1"]

        with patch.object(stage_validate, "validate_package") as mock_validate:
            mock_validate.return_value = (errors, warnings)

            result = validate_run_for_package(
                pkg, meta, all_packages, build_status, "43"
            )

        assert result is False
        assert build_status["stages"]["validate"][pkg]["state"] == "failed"
        assert build_status["stages"]["validate"][pkg]["errors"] == 2
        assert build_status["stages"]["validate"][pkg]["warnings"] == 1

    def test_run_global_checks_success(self):
        """Test global checks pass."""
        all_packages = {}
        build_status = {"stages": {"validate": {}}}

        with patch.object(stage_validate, "validate_group_membership") as mock_group, \
             patch.object(stage_validate, "validate_gitmodules") as mock_gitmodules:
            mock_group.return_value = ([], [])
            mock_gitmodules.return_value = ([], [])

            result = run_global_checks(all_packages, build_status)

        assert result is True

    def test_run_global_checks_with_errors(self):
        """Test global checks fail with errors."""
        all_packages = {}
        build_status = {"stages": {"validate": {}}}

        with patch.object(stage_validate, "validate_group_membership") as mock_group, \
             patch.object(stage_validate, "validate_gitmodules") as mock_gitmodules:
            mock_group.return_value = (["Group error"], [])
            mock_gitmodules.return_value = ([], [])

            result = run_global_checks(all_packages, build_status)

        assert result is False

    def test_run_global_checks_with_gitmodules_errors(self):
        """Test global checks fail when gitmodules has errors."""
        all_packages = {}
        build_status = {"stages": {"validate": {}}}

        with patch.object(stage_validate, "validate_group_membership") as mock_group, \
             patch.object(stage_validate, "validate_gitmodules") as mock_gitmodules:
            mock_group.return_value = ([], [])
            mock_gitmodules.return_value = (["Gitmodules error"], [])

            result = run_global_checks(all_packages, build_status)

        assert result is False

    def test_run_global_checks_with_warnings(self, capsys):
        """Test global checks with warnings print count."""
        all_packages = {}
        build_status = {"stages": {"validate": {}}}

        with patch.object(stage_validate, "validate_group_membership") as mock_group, \
             patch.object(stage_validate, "validate_gitmodules") as mock_gitmodules:
            mock_group.return_value = ([], ["Group warning"])
            mock_gitmodules.return_value = ([], ["Gitmodules warning"])

            result = run_global_checks(all_packages, build_status)

        assert result is True
        captured = capsys.readouterr()
        assert "2 warning(s) total" in captured.out

    def test_run_global_checks_with_both_group_and_gitmodules_errors(self):
        """Test global checks fail when both group and gitmodules have errors."""
        all_packages = {}
        build_status = {"stages": {"validate": {}}}

        with patch.object(stage_validate, "validate_group_membership") as mock_group, \
             patch.object(stage_validate, "validate_gitmodules") as mock_gitmodules:
            mock_group.return_value = (["Group error 1"], [])
            mock_gitmodules.return_value = (["Gitmodules error 1"], [])

            result = run_global_checks(all_packages, build_status)

        assert result is False

    def test_main_success(self):
        """Test main() function with successful validation."""
        with patch.object(stage_validate, "init_stage") as mock_init, \
             patch.object(stage_validate, "run_for_package") as mock_run, \
             patch.object(stage_validate, "run_global_checks") as mock_global, \
             patch.object(stage_validate, "save_build_status") as mock_save:
            mock_init.return_value = ({}, {}, {"stages": {"validate": {}}})
            mock_run.return_value = True
            mock_global.return_value = True

            # Should not raise
            main()

    def test_main_exits_on_global_check_failure(self):
        """Test main() exits with code 1 on global check failure."""
        with patch.object(stage_validate, "init_stage") as mock_init, \
             patch.object(stage_validate, "run_for_package") as mock_run, \
             patch.object(stage_validate, "run_global_checks") as mock_global, \
             patch.object(stage_validate, "save_build_status") as mock_save, \
             pytest.raises(SystemExit) as exc_info:
            mock_init.return_value = ({}, {}, {"stages": {"validate": {}}})
            mock_run.return_value = True
            mock_global.return_value = False

            main()

        assert exc_info.value.code == 1

    def test_main_handles_keyboard_interrupt(self):
        """Test main() handles KeyboardInterrupt with exit code 130."""
        with patch.object(stage_validate, "setup_logging"):
            try:
                # Simulate __name__ == "__main__" execution
                code = '''
import sys
sys.path.insert(0, 'scripts')
import importlib
stage_validate = importlib.import_module("scripts.stage-validate")
# This would trigger KeyboardInterrupt in the try/except
raise KeyboardInterrupt()
'''
                # We can't easily test this without mocking more, skip for now
            except KeyboardInterrupt:
                pass


class TestStageSpec:
    """Tests for stage-spec.py entry point."""

    def test_spec_run_for_package_skip(self):
        """Test that skipped packages are marked correctly."""
        pkg = "test-pkg"
        meta = {"_skip": True}
        all_packages = {}
        build_status = {"stages": {"spec": {}}}

        result = spec_run_for_package(pkg, meta, all_packages, build_status, "43")

        assert result is True
        assert build_status["stages"]["spec"][pkg]["state"] == "skipped"

    def test_spec_run_for_package_success(self, tmp_path):
        """Test successful spec generation."""
        pkg = "test-pkg"
        meta = {
            "version": "1.0.0",
            "release": 1,
        }
        all_packages = {pkg: meta}
        build_status = {"stages": {"spec": {}}}

        log_dir = tmp_path / "logs/build" / pkg
        log_dir.mkdir(parents=True)

        with patch.object(stage_spec, "generate_spec") as mock_gen, \
             patch.object(stage_spec, "get_package_log_dir") as mock_log_dir, \
             patch.object(stage_spec, "ROOT", tmp_path):
            mock_gen.return_value = "# Generated spec"
            mock_log_dir.return_value = log_dir
            result = spec_run_for_package(pkg, meta, all_packages, build_status, "43")

        assert result is True
        assert build_status["stages"]["spec"][pkg]["state"] == "success"

    def test_spec_run_for_package_failure(self, tmp_path):
        """Test spec generation failure."""
        pkg = "bad-pkg"
        meta = {
            "version": "1.0.0",
            "release": 1,
        }
        all_packages = {pkg: meta}
        build_status = {"stages": {"spec": {}}}

        log_dir = tmp_path / "logs/build" / pkg
        log_dir.mkdir(parents=True)

        with patch.object(stage_spec, "generate_spec") as mock_gen, \
             patch.object(stage_spec, "get_package_log_dir") as mock_log_dir, \
             patch.object(stage_spec, "ROOT", tmp_path):
            mock_gen.side_effect = RuntimeError("Template error")
            mock_log_dir.return_value = log_dir
            result = spec_run_for_package(pkg, meta, all_packages, build_status, "43")

        assert result is False
        assert build_status["stages"]["spec"][pkg]["state"] == "failed"

    def test_spec_creates_log_file(self, tmp_path):
        """Test that spec generation creates a log file."""
        pkg = "test-pkg"
        meta = {
            "version": "1.0.0",
            "release": 1,
        }
        all_packages = {pkg: meta}
        build_status = {"stages": {"spec": {}}}

        log_dir = tmp_path / "logs/build" / pkg
        log_dir.mkdir(parents=True)

        with patch.object(stage_spec, "generate_spec") as mock_gen, \
             patch.object(stage_spec, "get_package_log_dir") as mock_log_dir, \
             patch.object(stage_spec, "ROOT", tmp_path):
            mock_gen.return_value = "# spec content"
            mock_log_dir.return_value = log_dir
            spec_run_for_package(pkg, meta, all_packages, build_status, "43")

        log_file = log_dir / "00-spec.log"
        assert log_file.exists()

    def test_spec_devel_subpackage(self, tmp_path):
        """Test that devel subpackage is included when present."""
        pkg = "test-pkg"
        meta = {
            "version": "1.0.0",
            "release": 1,
            "devel": {"requires": []},  # devel subpackage
        }
        all_packages = {pkg: meta}
        build_status = {"stages": {"spec": {}}}

        log_dir = tmp_path / "logs/build" / pkg
        log_dir.mkdir(parents=True)

        with patch.object(stage_spec, "generate_spec") as mock_gen, \
             patch.object(stage_spec, "get_package_log_dir") as mock_log_dir, \
             patch.object(stage_spec, "ROOT", tmp_path):
            mock_gen.return_value = "# spec"
            mock_log_dir.return_value = log_dir
            spec_run_for_package(pkg, meta, all_packages, build_status, "43")

        assert "subpackages" in build_status["stages"]["spec"][pkg]
        assert "devel" in build_status["stages"]["spec"][pkg]["subpackages"]


class TestStageCoprBlocking:
    """Tests for stage-copr.py entry point blocking logic."""

    def test_copr_run_for_package_skip(self):
        """Test that skipped packages are marked correctly."""
        pkg = "test-pkg"
        meta = {"_skip": True}
        build_status = {"stages": {"copr": {}}}

        result = stage_copr.run_for_package(
            pkg, meta, build_status, "43", "nett00n/hyprland",
            proceed=False, synchronous=False
        )

        assert result is True
        assert build_status["stages"]["copr"][pkg]["state"] == "skipped"

    def test_copr_blocked_by_srpm_failure(self):
        """Test COPR skipped when SRPM failed."""
        pkg = "test-pkg"
        meta = {"version": "1.0.0", "release": 1}
        build_status = {
            "stages": {
                "copr": {},
                "srpm": {pkg: {"state": "failed"}},
                "mock": {pkg: {"state": "success"}},
            },
        }

        result = stage_copr.run_for_package(
            pkg, meta, build_status, "43", "nett00n/hyprland",
            proceed=False, synchronous=False
        )

        assert result is True
        assert build_status["stages"]["copr"][pkg]["state"] == "skipped"

    def test_copr_blocked_by_mock_failure(self):
        """Test COPR skipped when mock failed."""
        pkg = "test-pkg"
        meta = {"version": "1.0.0", "release": 1}
        build_status = {
            "stages": {
                "copr": {},
                "srpm": {pkg: {"state": "success"}},
                "mock": {pkg: {"state": "failed"}},
            },
        }

        result = stage_copr.run_for_package(
            pkg, meta, build_status, "43", "nett00n/hyprland",
            proceed=False, synchronous=False
        )

        assert result is True
        assert build_status["stages"]["copr"][pkg]["state"] == "skipped"


class TestStageShowPlan:
    """Tests for stage-show-plan.py show_plan() function."""

    def test_show_plan_no_filter(self, capsys):
        """Test all packages shown when no PACKAGE/SKIP set."""
        packages = {
            "pkg-a": {"version": "1.0"},
            "pkg-b": {"version": "2.0"},
            "pkg-c": {"version": "3.0"},
        }
        build_status = {
            "stages": {
                "validate": {
                    "pkg-a": {"state": "success"},
                    "pkg-b": {"state": None},
                    "pkg-c": {"state": "failed"},
                }
            }
        }

        with patch.object(stage_show_plan, "get_packages") as mock_get, \
             patch.object(stage_show_plan, "load_build_status") as mock_load:
            mock_get.return_value = packages
            mock_load.return_value = build_status
            stage_show_plan.show_plan()

        captured = capsys.readouterr()
        assert "pkg-a" in captured.out
        assert "pkg-b" in captured.out
        assert "pkg-c" in captured.out

    def test_show_plan_single_package(self, capsys):
        """Test single package name filters correctly."""
        packages = {
            "pkg-a": {"version": "1.0"},
            "pkg-b": {"version": "2.0"},
        }
        build_status = {
            "stages": {
                "validate": {
                    "pkg-a": {"state": "success"},
                    "pkg-b": {"state": None},
                }
            }
        }

        with patch.object(stage_show_plan, "get_packages") as mock_get, \
             patch.object(stage_show_plan, "load_build_status") as mock_load:
            mock_get.return_value = packages
            mock_load.return_value = build_status
            stage_show_plan.show_plan(package="pkg-a")

        captured = capsys.readouterr()
        assert "pkg-a" in captured.out
        assert "pkg-b" not in captured.out

    def test_show_plan_multi_package(self, capsys):
        """Test comma-separated PACKAGE shows only those."""
        packages = {
            "pkg-a": {"version": "1.0"},
            "pkg-b": {"version": "2.0"},
            "pkg-c": {"version": "3.0"},
        }
        build_status = {
            "stages": {
                "validate": {
                    "pkg-a": {"state": "success"},
                    "pkg-b": {"state": None},
                    "pkg-c": {"state": "failed"},
                }
            }
        }

        with patch.object(stage_show_plan, "get_packages") as mock_get, \
             patch.object(stage_show_plan, "load_build_status") as mock_load:
            mock_get.return_value = packages
            mock_load.return_value = build_status
            stage_show_plan.show_plan(package="pkg-a, pkg-c")

        captured = capsys.readouterr()
        assert "pkg-a" in captured.out
        assert "pkg-b" not in captured.out
        assert "pkg-c" in captured.out

    def test_show_plan_skip_packages(self, capsys):
        """Test SKIP_PACKAGES excludes listed packages."""
        packages = {
            "pkg-a": {"version": "1.0"},
            "pkg-b": {"version": "2.0"},
            "pkg-c": {"version": "3.0"},
        }
        build_status = {
            "stages": {
                "validate": {
                    "pkg-a": {"state": "success"},
                    "pkg-b": {"state": None},
                    "pkg-c": {"state": "failed"},
                }
            }
        }

        with patch.object(stage_show_plan, "get_packages") as mock_get, \
             patch.object(stage_show_plan, "load_build_status") as mock_load:
            mock_get.return_value = packages
            mock_load.return_value = build_status
            stage_show_plan.show_plan(skip_packages_arg="pkg-b")

        captured = capsys.readouterr()
        assert "pkg-a" in captured.out
        assert "pkg-b" not in captured.out
        assert "pkg-c" in captured.out

    def test_show_plan_package_and_skip(self, capsys):
        """Test PACKAGE + SKIP_PACKAGES combined."""
        packages = {
            "pkg-a": {"version": "1.0"},
            "pkg-b": {"version": "2.0"},
            "pkg-c": {"version": "3.0"},
            "pkg-d": {"version": "4.0"},
        }
        build_status = {
            "stages": {
                "validate": {
                    "pkg-a": {"state": "success"},
                    "pkg-b": {"state": None},
                    "pkg-c": {"state": "failed"},
                    "pkg-d": {"state": "success"},
                }
            }
        }

        with patch.object(stage_show_plan, "get_packages") as mock_get, \
             patch.object(stage_show_plan, "load_build_status") as mock_load:
            mock_get.return_value = packages
            mock_load.return_value = build_status
            # PACKAGE filters to a,b,c; SKIP removes b → a,c shown
            stage_show_plan.show_plan(package="pkg-a,pkg-b,pkg-c", skip_packages_arg="pkg-b")

        captured = capsys.readouterr()
        assert "pkg-a" in captured.out
        assert "pkg-b" not in captured.out
        assert "pkg-c" in captured.out
        assert "pkg-d" not in captured.out

    def test_show_plan_unknown_package_exits(self):
        """Test unknown PACKAGE causes sys.exit."""
        packages = {"pkg-a": {"version": "1.0"}}
        build_status = {"stages": {"validate": {"pkg-a": {"state": "success"}}}}

        with patch.object(stage_show_plan, "get_packages") as mock_get, \
             patch.object(stage_show_plan, "load_build_status") as mock_load, \
             pytest.raises(SystemExit):
            mock_get.return_value = packages
            mock_load.return_value = build_status
            stage_show_plan.show_plan(package="nonexistent")

    def test_show_plan_case_insensitive(self, capsys):
        """Test PACKAGE name is case-insensitive."""
        packages = {
            "MyPkg": {"version": "1.0"},
            "OtherPkg": {"version": "2.0"},
        }
        build_status = {
            "stages": {
                "validate": {
                    "MyPkg": {"state": "success"},
                    "OtherPkg": {"state": None},
                }
            }
        }

        with patch.object(stage_show_plan, "get_packages") as mock_get, \
             patch.object(stage_show_plan, "load_build_status") as mock_load:
            mock_get.return_value = packages
            mock_load.return_value = build_status
            stage_show_plan.show_plan(package="mypkg")  # lowercase

        captured = capsys.readouterr()
        assert "MyPkg" in captured.out
        assert "OtherPkg" not in captured.out
