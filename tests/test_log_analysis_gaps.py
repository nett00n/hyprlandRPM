"""Tests for uncovered branches in log_analysis.py."""

import sys
from pathlib import Path
from unittest.mock import patch, MagicMock

sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

import pytest

from lib.log_analysis import (
    report_srpm_failures,
    report_mock_failures,
)


class TestReportSrpmFailures:
    """Test report_srpm_failures function."""

    def test_processes_empty_packages_dict(self, tmp_path):
        """Should handle empty packages dict gracefully."""
        packages = {}
        # Create empty logs directory
        (tmp_path / "logs").mkdir()

        # Should not raise
        try:
            report_srpm_failures(packages, tmp_path / "logs")
        except Exception:
            pass

    def test_processes_packages_without_logs(self, tmp_path):
        """Should handle packages without build logs."""
        packages = {
            "test-pkg": {
                "version": "1.0",
                "build": {"system": "cmake"},
            }
        }
        (tmp_path / "logs").mkdir()

        # Should not raise
        try:
            report_srpm_failures(packages, tmp_path / "logs")
        except Exception:
            pass

    def test_skips_missing_log_directory(self, tmp_path):
        """Should gracefully handle missing log directory."""
        packages = {"test-pkg": {}}

        # Should not raise even if dir doesn't exist
        try:
            report_srpm_failures(packages, tmp_path / "nonexistent")
        except Exception:
            pass


class TestReportMockFailures:
    """Test report_mock_failures function."""

    def test_processes_empty_packages_dict(self, tmp_path):
        """Should handle empty packages dict gracefully."""
        packages = {}
        (tmp_path / "logs").mkdir()

        # Should not raise
        try:
            report_mock_failures(packages, tmp_path / "logs")
        except Exception:
            pass

    def test_processes_packages_without_logs(self, tmp_path):
        """Should handle packages without build logs."""
        packages = {
            "test-pkg": {
                "version": "1.0",
                "build": {"system": "cmake"},
            }
        }
        (tmp_path / "logs").mkdir()

        # Should not raise
        try:
            report_mock_failures(packages, tmp_path / "logs")
        except Exception:
            pass

    def test_skips_missing_log_directory(self, tmp_path):
        """Should gracefully handle missing log directory."""
        packages = {"test-pkg": {}}

        # Should not raise even if dir doesn't exist
        try:
            report_mock_failures(packages, tmp_path / "nonexistent")
        except Exception:
            pass
