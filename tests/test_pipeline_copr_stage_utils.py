"""Unit tests for scripts/lib/pipeline.py, lib/copr.py, lib/stage_utils.py"""

import pytest

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

from lib.pipeline import compute_forced_stages, is_cached
from lib.copr import parse_build_id, validate_copr_repo
from lib.stage_utils import make_stage_entry


class TestComputeForcedStages:
    """Test forced stage computation."""

    def test_no_deps_rebuilt_no_force_flags(self):
        """No forced stages when no deps rebuilt and no force flags."""
        meta = {"depends_on": []}
        build_status = {
            "stages": {
                "spec": {"pkg": {"force_run": False}},
                "vendor": {"pkg": {"force_run": False}},
                "srpm": {"pkg": {"force_run": False}},
                "mock": {"pkg": {"force_run": False}},
                "copr": {"pkg": {"force_run": False}},
            }
        }
        rebuilt = set()
        assert compute_forced_stages("pkg", meta, build_status, rebuilt) == set()

    def test_dep_rebuilt_forces_all_stages(self):
        """Any rebuilt dependency forces all stages."""
        meta = {"depends_on": ["dep1", "dep2"]}
        build_status = {"stages": {}}
        rebuilt = {"dep1"}
        result = compute_forced_stages("pkg", meta, build_status, rebuilt)
        assert result == {"spec", "vendor", "srpm", "mock", "copr"}

    def test_force_run_on_spec_cascades(self):
        """force_run on spec stage cascades to downstream."""
        meta = {"depends_on": []}
        build_status = {
            "stages": {
                "spec": {"pkg": {"force_run": True}},
                "vendor": {"pkg": {"force_run": False}},
                "srpm": {"pkg": {"force_run": False}},
                "mock": {"pkg": {"force_run": False}},
                "copr": {"pkg": {"force_run": False}},
            }
        }
        rebuilt = set()
        result = compute_forced_stages("pkg", meta, build_status, rebuilt)
        assert result == {"spec", "vendor", "srpm", "mock", "copr"}

    def test_force_run_on_srpm_does_not_affect_upstream(self):
        """force_run on srpm does not force spec or vendor."""
        meta = {"depends_on": []}
        build_status = {
            "stages": {
                "spec": {"pkg": {"force_run": False}},
                "vendor": {"pkg": {"force_run": False}},
                "srpm": {"pkg": {"force_run": True}},
                "mock": {"pkg": {"force_run": False}},
                "copr": {"pkg": {"force_run": False}},
            }
        }
        rebuilt = set()
        result = compute_forced_stages("pkg", meta, build_status, rebuilt)
        assert result == {"srpm", "mock", "copr"}
        assert "spec" not in result
        assert "vendor" not in result

    def test_dep_rebuilt_overrides_stage_entries(self):
        """Rebuilt dep forces all stages even if no force_run flags."""
        meta = {"depends_on": ["other"]}
        build_status = {
            "stages": {
                "spec": {"pkg": {"force_run": False}},
            }
        }
        rebuilt = {"other"}
        result = compute_forced_stages("pkg", meta, build_status, rebuilt)
        # All stages forced regardless of stage entries
        assert len(result) == 5

    def test_missing_stage_entry_no_crash(self):
        """Missing stage entry doesn't crash."""
        meta = {"depends_on": []}
        build_status = {"stages": {}}  # empty
        rebuilt = set()
        result = compute_forced_stages("pkg", meta, build_status, rebuilt)
        assert result == set()


class TestIsCached:
    """Test cache hit detection."""

    def test_cached_success_matching_hashes(self):
        """Cache hit: state=success, hashes match, not forced."""
        build_status = {
            "stages": {
                "spec": {
                    "pkg": {
                        "state": "success",
                        "hashes": {"a": "hash1"},
                    }
                }
            }
        }
        new_hashes = {"a": "hash1"}
        forced_stages = set()
        assert is_cached("spec", "pkg", build_status, new_hashes, forced_stages) is True

    def test_not_cached_state_failed(self):
        """Not cached if state != success."""
        build_status = {
            "stages": {
                "spec": {
                    "pkg": {
                        "state": "failed",
                        "hashes": {"a": "hash1"},
                    }
                }
            }
        }
        new_hashes = {"a": "hash1"}
        forced_stages = set()
        assert is_cached("spec", "pkg", build_status, new_hashes, forced_stages) is False

    def test_not_cached_hashes_mismatch(self):
        """Not cached if hashes differ."""
        build_status = {
            "stages": {
                "spec": {
                    "pkg": {
                        "state": "success",
                        "hashes": {"a": "hash1"},
                    }
                }
            }
        }
        new_hashes = {"a": "hash2"}
        forced_stages = set()
        assert is_cached("spec", "pkg", build_status, new_hashes, forced_stages) is False

    def test_not_cached_in_forced_stages(self):
        """Not cached if stage is in forced_stages."""
        build_status = {
            "stages": {
                "spec": {
                    "pkg": {
                        "state": "success",
                        "hashes": {"a": "hash1"},
                    }
                }
            }
        }
        new_hashes = {"a": "hash1"}
        forced_stages = {"spec"}
        assert is_cached("spec", "pkg", build_status, new_hashes, forced_stages) is False

    def test_missing_entry_not_cached(self):
        """Missing entry in build_status is not cached."""
        build_status = {"stages": {}}
        new_hashes = {"a": "hash1"}
        forced_stages = set()
        assert is_cached("spec", "pkg", build_status, new_hashes, forced_stages) is False

    def test_missing_hashes_not_cached(self):
        """Entry with no hashes is not cached."""
        build_status = {
            "stages": {
                "spec": {
                    "pkg": {
                        "state": "success",
                    }
                }
            }
        }
        new_hashes = {"a": "hash1"}
        forced_stages = set()
        assert is_cached("spec", "pkg", build_status, new_hashes, forced_stages) is False


class TestParseBuildId:
    """Test build ID extraction from copr-cli output."""

    def test_extract_build_id(self):
        """Extract build ID from typical output."""
        output = "Created builds: 12345678"
        assert parse_build_id(output) == 12345678

    def test_extract_build_id_multiline(self):
        """Extract build ID from multiline output."""
        output = """Building...
Created builds: 99887766
Done."""
        assert parse_build_id(output) == 99887766

    def test_no_match_returns_none(self):
        """No match returns None."""
        output = "No builds created"
        assert parse_build_id(output) is None

    def test_empty_output_returns_none(self):
        """Empty output returns None."""
        assert parse_build_id("") is None

    def test_invalid_id_number_returns_none(self):
        """Invalid number in output returns None."""
        output = "Created builds: abc"
        assert parse_build_id(output) is None

    def test_build_id_at_end_of_complex_line(self):
        """Build ID extracted even in complex output."""
        output = "  Created builds: 555  "
        assert parse_build_id(output) == 555


class TestValidateCoprRepo:
    """Test COPR repository slug validation."""

    def test_valid_repo_slug(self):
        """Valid owner/repo format."""
        assert validate_copr_repo("user/repo") is True

    def test_valid_with_dashes(self):
        """Valid slug with dashes."""
        assert validate_copr_repo("my-user/my-repo") is True

    def test_valid_with_dots(self):
        """Valid slug with dots in repo name."""
        assert validate_copr_repo("user/repo.name") is True

    def test_valid_with_underscore(self):
        """Valid slug with underscores."""
        assert validate_copr_repo("user_name/repo_name") is True

    def test_invalid_missing_slash(self):
        """Invalid: missing slash."""
        assert validate_copr_repo("userrepo") is False

    def test_invalid_too_many_slashes(self):
        """Invalid: too many slashes."""
        assert validate_copr_repo("user/repo/extra") is False

    def test_invalid_empty_string(self):
        """Invalid: empty string."""
        assert validate_copr_repo("") is False

    def test_invalid_slash_only(self):
        """Invalid: slash only."""
        assert validate_copr_repo("/") is False

    def test_invalid_trailing_slash(self):
        """Invalid: trailing slash."""
        assert validate_copr_repo("user/repo/") is False

    def test_invalid_leading_slash(self):
        """Invalid: leading slash."""
        assert validate_copr_repo("/user/repo") is False

    def test_invalid_special_chars(self):
        """Invalid: special characters."""
        assert validate_copr_repo("user@/repo!") is False

    def test_valid_complex_names(self):
        """Valid with complex alphanumeric names."""
        assert validate_copr_repo("user123/repo-name.v2") is True


class TestMakeStageEntry:
    """Test stage entry dict construction."""

    def test_basic_entry_without_devel(self):
        """Basic entry without devel subpackage."""
        entry = make_stage_entry("success", "pkg-1.0-1.fc43", has_devel=False)
        assert entry["state"] == "success"
        assert entry["version"] == "pkg-1.0-1.fc43"
        assert entry["force_run"] is False
        assert "subpackages" not in entry

    def test_entry_with_devel(self):
        """Entry with devel subpackage."""
        entry = make_stage_entry("success", "pkg-1.0-1.fc43", has_devel=True)
        assert entry["state"] == "success"
        assert "subpackages" in entry
        assert "devel" in entry["subpackages"]
        assert entry["subpackages"]["devel"]["state"] == "success"
        assert entry["subpackages"]["devel"]["version"] == "pkg-1.0-1.fc43"

    def test_entry_with_extras(self):
        """Entry with extra kwargs."""
        entry = make_stage_entry(
            "failed",
            "pkg-1.0-1.fc43",
            has_devel=False,
            path="/path/to/srpm",
            log="error log",
        )
        assert entry["state"] == "failed"
        assert entry["path"] == "/path/to/srpm"
        assert entry["log"] == "error log"
        assert entry["force_run"] is False

    def test_entry_force_run_always_false(self):
        """force_run is always False in new entry."""
        entry = make_stage_entry("success", "1.0-1", has_devel=False)
        assert entry["force_run"] is False

    def test_entry_failed_state(self):
        """Entry with failed state."""
        entry = make_stage_entry("failed", "1.0-1", has_devel=False)
        assert entry["state"] == "failed"

    def test_entry_skipped_state(self):
        """Entry with skipped state."""
        entry = make_stage_entry("skipped", "1.0-1", has_devel=False)
        assert entry["state"] == "skipped"

    def test_entry_unknown_state(self):
        """Entry with unknown state."""
        entry = make_stage_entry("unknown", "1.0-1", has_devel=False)
        assert entry["state"] == "unknown"

    def test_entry_with_devel_and_extras(self):
        """Entry with both devel and extra kwargs."""
        entry = make_stage_entry(
            "success",
            "pkg-1.0-1.fc43",
            has_devel=True,
            build_id=12345,
        )
        assert entry["subpackages"]["devel"]["state"] == "success"
        assert entry["build_id"] == 12345
