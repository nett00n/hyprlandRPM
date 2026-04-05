"""Tests for lib.reporting module."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

import pytest

from lib.reporting import badge, badge_short, print_summary, status, verbose_proceed_check


class TestPrintSummary:
    """Test print_summary function."""

    def test_empty_packages_no_crash(self, capsys):
        """print_summary should not crash with empty packages dict."""
        # This previously raised ValueError: max() arg is an empty sequence
        report = {"stages": {}}
        # Should not raise
        print_summary({}, report, copr_repo="")
        captured = capsys.readouterr()
        assert "No packages" in captured.out

    def test_missing_stage_in_report_no_crash(self, capsys):
        """print_summary should handle missing stages in report."""
        report = {"stages": {"spec": {}}}  # missing "mock", "copr", etc.
        packages = {"pkg1": {}}
        # Should not raise KeyError
        print_summary(packages, report, copr_repo="")
        captured = capsys.readouterr()
        # Should have printed something
        assert len(captured.out) > 0

    def test_summary_with_valid_data(self, capsys):
        """print_summary should print valid data."""
        report = {
            "stages": {
                "spec": {"pkg1": {"state": "success"}},
                "vendor": {"pkg1": {"state": "success"}},
                "srpm": {"pkg1": {"state": "success"}},
                "mock": {"pkg1": {"state": "success"}},
                "copr": {"pkg1": {"state": "success", "url": "http://example.com"}},
            }
        }
        packages = {"pkg1": {}}
        print_summary(packages, report, copr_repo="owner/repo")
        captured = capsys.readouterr()
        assert "pkg1" in captured.out or "Summary" in captured.out


class TestStatus:
    """Test status function."""

    def test_status_ok(self, capsys):
        """Should print OK status."""
        status("spec", "mypackage", "ok")
        captured = capsys.readouterr()
        assert "[OK]" in captured.out
        assert "spec" in captured.out
        assert "mypackage" in captured.out

    def test_status_fail(self, capsys):
        """Should print FAIL status."""
        status("mock", "mypackage", "fail")
        captured = capsys.readouterr()
        assert "[FAIL]" in captured.out
        assert "mock" in captured.out

    def test_status_skip(self, capsys):
        """Should print SKIP status."""
        status("vendor", "mypackage", "skip")
        captured = capsys.readouterr()
        assert "[SKIP]" in captured.out
        assert "vendor" in captured.out

    def test_status_with_detail(self, capsys):
        """Should include detail message."""
        status("spec", "pkg", "ok", detail="error message")
        captured = capsys.readouterr()
        assert "error message" in captured.out


class TestVerboseProceedCheck:
    """Test verbose_proceed_check function."""

    def test_skip_on_success(self, capsys):
        """Should return True and print 'skip' for success state."""
        result = verbose_proceed_check("spec", "mypackage", "success")
        assert result is True
        captured = capsys.readouterr()
        assert "skip" in captured.out
        assert "spec" in captured.out
        assert "mypackage" in captured.out

    def test_retry_on_failed(self, capsys):
        """Should return False and print 'retry' for failed state."""
        result = verbose_proceed_check("mock", "mypackage", "failed")
        assert result is False
        captured = capsys.readouterr()
        assert "retry" in captured.out
        assert "failed" in captured.out

    def test_run_on_none(self, capsys):
        """Should return False and print 'run' for None state."""
        result = verbose_proceed_check("spec", "mypackage", None)
        assert result is False
        captured = capsys.readouterr()
        assert "run" in captured.out
        assert "none" in captured.out

    def test_run_on_unknown_state(self, capsys):
        """Should return False and print 'run' for unknown state."""
        result = verbose_proceed_check("spec", "mypackage", "unknown")
        assert result is False
        captured = capsys.readouterr()
        assert "run" in captured.out


class TestBadge:
    """Test badge function."""

    def test_badge_success(self):
        """Should generate success badge."""
        result = badge("spec", "success")
        assert "spec" in result
        assert "success" in result
        assert "brightgreen" in result
        assert "![" in result
        assert "](http" in result

    def test_badge_failed(self):
        """Should generate failed badge."""
        result = badge("mock", "failed")
        assert "mock" in result
        assert "failed" in result
        assert "red" in result

    def test_badge_skipped(self):
        """Should generate skipped badge."""
        result = badge("vendor", "skipped")
        assert "vendor" in result
        assert "skipped" in result
        assert "lightgrey" in result

    def test_badge_unknown(self):
        """Should generate unknown badge with orange color."""
        result = badge("spec", "unknown")
        assert "spec" in result
        assert "unknown" in result
        assert "orange" in result

    def test_badge_none_state(self):
        """Should handle None state as 'unknown'."""
        result = badge("spec", None)
        assert "unknown" in result
        assert "orange" in result

    def test_badge_with_url(self):
        """Should wrap badge in markdown link when URL provided."""
        result = badge("spec", "success", url="http://example.com")
        assert "[" in result
        assert "http://example.com" in result
        assert result.count("[") == 2  # Outer link and image link

    def test_badge_with_style(self):
        """Should add style parameter to shields.io URL."""
        result = badge("spec", "success", style="flat")
        assert "style=flat" in result

    def test_badge_markdown_format(self):
        """Should be valid markdown."""
        result = badge("spec", "success")
        # Should have markdown image syntax ![alt](url)
        assert "![" in result
        assert "](https://img.shields.io" in result


class TestBadgeShort:
    """Test badge_short function."""

    def test_badge_short_success(self):
        """Should generate short success badge with emoji."""
        result = badge_short("spec", "success")
        assert "spec" in result
        assert "brightgreen" in result
        # Emoji is URL-encoded in the shields.io URL
        assert "✔" in result or "%E2%9C%94" in result

    def test_badge_short_failed(self):
        """Should generate short failed badge with emoji."""
        result = badge_short("mock", "failed")
        assert "mock" in result
        assert "red" in result
        # Emoji is URL-encoded in the shields.io URL
        assert "✘" in result or "%E2%9C%98" in result

    def test_badge_short_skipped(self):
        """Should generate short skipped badge with emoji."""
        result = badge_short("vendor", "skipped")
        assert "vendor" in result
        assert "lightgrey" in result
        # Emoji is URL-encoded in the shields.io URL
        assert "○" in result or "%E2%97%8B" in result

    def test_badge_short_unknown(self):
        """Should generate unknown badge with orange."""
        result = badge_short("spec", "unknown")
        assert "spec" in result
        assert "orange" in result

    def test_badge_short_none_state(self):
        """Should handle None as 'unknown'."""
        result = badge_short("spec", None)
        assert "orange" in result

    def test_badge_short_with_url(self):
        """Should wrap in markdown link when URL provided."""
        result = badge_short("spec", "success", url="http://example.com")
        assert "[" in result
        assert "http://example.com" in result

    def test_badge_short_with_style(self):
        """Should add style parameter."""
        result = badge_short("spec", "success", style="flat")
        assert "style=flat" in result
