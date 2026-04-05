"""Tests for COPR module."""

import sys
from pathlib import Path
from unittest.mock import patch

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

from lib.copr import (
    COPR_BUILD_URL,
    TERMINAL_STATES,
    check_copr_credentials,
    parse_build_id,
    poll_copr_status,
    validate_copr_repo,
)


class TestParseBuildId:
    """Tests for parse_build_id function."""

    def test_parse_build_id_found(self):
        """Test extracting build ID from valid output."""
        output = """
        Submitting build...
        Created builds: 12345
        Build URL: https://copr.example.com/build/12345
        """
        result = parse_build_id(output)
        assert result == 12345

    def test_parse_build_id_multiple_numbers(self):
        """Test that only the last number on the line is extracted."""
        output = "Created builds: 12345 99999"
        result = parse_build_id(output)
        assert result == 99999

    def test_parse_build_id_not_found(self):
        """Test when 'Created builds:' is not in output."""
        output = """
        Submitting build...
        Build submitted successfully
        """
        result = parse_build_id(output)
        assert result is None

    def test_parse_build_id_malformed_line(self):
        """Test when 'Created builds:' line exists but doesn't have a number."""
        output = "Created builds: none"
        result = parse_build_id(output)
        assert result is None

    def test_parse_build_id_empty_output(self):
        """Test with empty output."""
        result = parse_build_id("")
        assert result is None

    def test_parse_build_id_zero(self):
        """Test with zero build ID."""
        output = "Created builds: 0"
        result = parse_build_id(output)
        assert result == 0


class TestValidateCoprRepo:
    """Tests for validate_copr_repo function."""

    def test_valid_repo_slug(self):
        """Test valid repository slug."""
        assert validate_copr_repo("nett00n/hyprland") is True

    def test_valid_repo_with_dashes(self):
        """Test valid repo with dashes."""
        assert validate_copr_repo("my-org/my-repo") is True

    def test_valid_repo_with_dots(self):
        """Test valid repo with dots."""
        assert validate_copr_repo("org/repo.name") is True

    def test_valid_repo_with_underscores(self):
        """Test valid repo with underscores."""
        assert validate_copr_repo("org_name/repo_name") is True

    def test_invalid_missing_slash(self):
        """Test invalid format without slash."""
        assert validate_copr_repo("nohyphrland") is False

    def test_invalid_multiple_slashes(self):
        """Test invalid format with multiple slashes."""
        assert validate_copr_repo("org/repo/sub") is False

    def test_invalid_empty_parts(self):
        """Test invalid format with empty parts."""
        assert validate_copr_repo("/repo") is False
        assert validate_copr_repo("org/") is False
        assert validate_copr_repo("/") is False

    def test_invalid_special_chars(self):
        """Test invalid format with special characters."""
        assert validate_copr_repo("org@/repo") is False
        assert validate_copr_repo("org/repo#") is False

    def test_empty_string(self):
        """Test empty string."""
        assert validate_copr_repo("") is False


class TestCheckCoprCredentials:
    """Tests for check_copr_credentials function."""

    @patch("lib.copr.run_cmd")
    def test_credentials_valid(self, mock_run_cmd):
        """Test when credentials are valid."""
        mock_run_cmd.return_value = (True, "user: testuser\n", "")

        result = check_copr_credentials()

        assert result is True
        mock_run_cmd.assert_called_once_with(["copr-cli", "whoami"])

    @patch("lib.copr.run_cmd")
    def test_credentials_invalid(self, mock_run_cmd, capsys):
        """Test when credentials are invalid."""
        mock_run_cmd.return_value = (False, "", "Error: unauthorized")

        result = check_copr_credentials()

        assert result is False
        captured = capsys.readouterr()
        assert "invalid or missing" in captured.err
        assert "copr.conf" in captured.err
        assert "Error: unauthorized" in captured.err

    @patch("lib.copr.run_cmd")
    def test_credentials_check_no_stderr(self, mock_run_cmd, capsys):
        """Test error handling without stderr output."""
        mock_run_cmd.return_value = (False, "", "")

        result = check_copr_credentials()

        assert result is False
        captured = capsys.readouterr()
        assert "invalid or missing" in captured.err


class TestPollCoprStatus:
    """Tests for poll_copr_status function."""

    @patch("lib.copr.run_cmd")
    def test_poll_no_packages(self, mock_run_cmd):
        """Test polling with empty package list."""
        stages = {"copr": {}}
        result = poll_copr_status(stages, [])
        assert result is False
        mock_run_cmd.assert_not_called()

    @patch("lib.copr.run_cmd")
    def test_poll_no_build_id(self, mock_run_cmd):
        """Test polling when package has no build_id."""
        stages = {
            "copr": {
                "pkg1": {"state": "pending"},
            }
        }
        result = poll_copr_status(stages, ["pkg1"])
        assert result is False
        mock_run_cmd.assert_not_called()

    @patch("lib.copr.run_cmd")
    def test_poll_terminal_state_skip(self, mock_run_cmd):
        """Test that terminal states are skipped."""
        stages = {
            "copr": {
                "pkg1": {"build_id": 123, "state": "success"},
                "pkg2": {"build_id": 456, "state": "failed"},
            }
        }
        result = poll_copr_status(stages, ["pkg1", "pkg2"])
        assert result is False
        mock_run_cmd.assert_not_called()

    @patch("lib.copr.run_cmd")
    def test_poll_status_success(self, mock_run_cmd):
        """Test polling and finding success status."""
        mock_run_cmd.return_value = (True, "Build 123 succeeded", "")

        stages = {
            "copr": {
                "pkg1": {"build_id": 123, "state": "building"},
            }
        }
        result = poll_copr_status(stages, ["pkg1"])

        assert result is True
        assert stages["copr"]["pkg1"]["state"] == "success"
        mock_run_cmd.assert_called_once_with(["copr-cli", "status", "123"])

    @patch("lib.copr.run_cmd")
    def test_poll_status_failed(self, mock_run_cmd):
        """Test polling and finding failed status."""
        mock_run_cmd.return_value = (True, "Build 456 failed", "")

        stages = {
            "copr": {
                "pkg1": {"build_id": 456, "state": "building"},
            }
        }
        result = poll_copr_status(stages, ["pkg1"])

        assert result is True
        assert stages["copr"]["pkg1"]["state"] == "failed"

    @patch("lib.copr.run_cmd")
    def test_poll_status_no_state_change(self, mock_run_cmd):
        """Test polling when status doesn't change."""
        mock_run_cmd.return_value = (True, "Build 789 succeeded", "")

        stages = {
            "copr": {
                "pkg1": {"build_id": 789, "state": "success"},
            }
        }
        result = poll_copr_status(stages, ["pkg1"])

        # Status already terminal, should be skipped
        assert result is False
        mock_run_cmd.assert_not_called()

    @patch("lib.copr.run_cmd")
    def test_poll_status_command_failure(self, mock_run_cmd):
        """Test when copr-cli status command fails."""
        mock_run_cmd.return_value = (False, "", "Command failed")

        stages = {
            "copr": {
                "pkg1": {"build_id": 999, "state": "pending"},
            }
        }
        result = poll_copr_status(stages, ["pkg1"])

        # State should not change on command failure
        assert result is False
        assert stages["copr"]["pkg1"]["state"] == "pending"

    @patch("lib.copr.run_cmd")
    def test_poll_multiple_packages(self, mock_run_cmd):
        """Test polling multiple packages."""
        mock_run_cmd.side_effect = [
            (True, "Build 111 succeeded", ""),
            (True, "Build 222 failed", ""),
        ]

        stages = {
            "copr": {
                "pkg1": {"build_id": 111, "state": "building"},
                "pkg2": {"build_id": 222, "state": "building"},
            }
        }
        result = poll_copr_status(stages, ["pkg1", "pkg2"])

        assert result is True
        assert stages["copr"]["pkg1"]["state"] == "success"
        assert stages["copr"]["pkg2"]["state"] == "failed"

    @patch("lib.copr.run_cmd")
    def test_poll_case_insensitive_status(self, mock_run_cmd):
        """Test that status matching is case-insensitive."""
        mock_run_cmd.return_value = (True, "Build 333 SUCCEEDED", "")

        stages = {
            "copr": {
                "pkg1": {"build_id": 333, "state": "building"},
            }
        }
        result = poll_copr_status(stages, ["pkg1"])

        assert result is True
        assert stages["copr"]["pkg1"]["state"] == "success"

    @patch("lib.copr.run_cmd")
    def test_poll_no_copr_stage(self, mock_run_cmd):
        """Test polling when there is no copr stage."""
        stages = {}
        result = poll_copr_status(stages, ["pkg1"])
        assert result is False
        mock_run_cmd.assert_not_called()
