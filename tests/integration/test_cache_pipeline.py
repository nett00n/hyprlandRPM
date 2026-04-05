"""Integration tests for cache invalidation (is_cached / compute_forced_stages)."""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "scripts"))

from lib.cache import hashes_match
from lib.pipeline import is_cached, compute_forced_stages, STAGE_ORDER


class TestCachePipeline:
    """Test cache validation and forced stage computation."""

    def test_second_run_detects_cache_hit(self):
        """is_cached returns True when hashes match and state is success."""
        hashes = {"source_commit": "abc123", "templates": "def456"}
        build_status = {
            "stages": {
                "spec": {
                    "pkg-a": {
                        "state": "success",
                        "version": "1.0-1.fc43",
                        "hashes": hashes,
                    },
                },
            }
        }

        # Same hashes should be cached
        result = is_cached("spec", "pkg-a", build_status, hashes, set())
        assert result is True

    def test_changed_template_invalidates_cache(self):
        """is_cached returns False when templates hash differs."""
        old_hashes = {"source_commit": "abc123", "templates": "old_template"}
        new_hashes = {"source_commit": "abc123", "templates": "new_template"}

        build_status = {
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

        result = is_cached("spec", "pkg-a", build_status, new_hashes, set())
        assert result is False

    def test_force_run_flag_invalidates_cache_even_with_matching_hashes(self):
        """is_cached returns False when stage is in forced_stages."""
        hashes = {"source_commit": "abc123", "templates": "def456"}
        build_status = {
            "stages": {
                "spec": {
                    "pkg-a": {
                        "state": "success",
                        "version": "1.0-1.fc43",
                        "hashes": hashes,
                        "force_run": True,
                    },
                },
            }
        }

        # Even with matching hashes, forced stages are not cached
        forced_stages = {"spec", "vendor", "srpm", "mock", "copr"}
        result = is_cached("spec", "pkg-a", build_status, hashes, forced_stages)
        assert result is False

    def test_rebuilt_dependency_forces_all_stages(self):
        """compute_forced_stages returns all stages when dependency rebuilt."""
        meta = {"depends_on": ["pkg-b"]}
        build_status = {"stages": {s: {"pkg-a": {}} for s in STAGE_ORDER}}
        rebuilt = {"pkg-b"}

        forced = compute_forced_stages("pkg-a", meta, build_status, rebuilt)
        assert forced == set(STAGE_ORDER)

    def test_downstream_cascade_from_srpm_force_run(self):
        """Force run at srpm cascades to mock and copr."""
        meta = {}
        build_status = {
            "stages": {
                "spec": {"pkg-a": {"state": "success", "force_run": False}},
                "vendor": {"pkg-a": {"state": "success", "force_run": False}},
                "srpm": {"pkg-a": {"state": "success", "force_run": True}},
                "mock": {"pkg-a": {"state": "success", "force_run": False}},
                "copr": {"pkg-a": {"state": "success", "force_run": False}},
            }
        }

        forced = compute_forced_stages("pkg-a", meta, build_status, set())
        assert forced == {"srpm", "mock", "copr"}

    def test_no_force_and_matching_hashes_all_cached(self):
        """is_cached returns True for all stages with no force_run and matching hashes."""
        hashes = {"source_commit": "abc123", "templates": "def456"}
        build_status = {
            "stages": {
                "spec": {
                    "pkg-a": {
                        "state": "success",
                        "version": "1.0-1.fc43",
                        "hashes": hashes,
                    },
                },
                "vendor": {
                    "pkg-a": {
                        "state": "success",
                        "version": "1.0-1.fc43",
                        "hashes": hashes,
                    },
                },
                "srpm": {
                    "pkg-a": {
                        "state": "success",
                        "version": "1.0-1.fc43",
                        "hashes": hashes,
                    },
                },
                "mock": {
                    "pkg-a": {
                        "state": "success",
                        "version": "1.0-1.fc43",
                        "hashes": hashes,
                    },
                },
                "copr": {
                    "pkg-a": {
                        "state": "success",
                        "version": "1.0-1.fc43",
                        "hashes": hashes,
                    },
                },
            }
        }

        meta = {}
        forced = compute_forced_stages("pkg-a", meta, build_status, set())
        assert forced == set()

        for stage in STAGE_ORDER:
            result = is_cached(stage, "pkg-a", build_status, hashes, forced)
            assert result is True

    def test_missing_entry_not_cached(self):
        """is_cached returns False when entry missing."""
        build_status = {"stages": {"spec": {}}}

        hashes = {"source_commit": "abc123"}
        result = is_cached("spec", "pkg-a", build_status, hashes, set())
        assert result is False

    def test_failed_state_not_cached(self):
        """is_cached returns False when state is failed."""
        build_status = {
            "stages": {
                "spec": {
                    "pkg-a": {
                        "state": "failed",
                        "hashes": {"source_commit": "abc123"},
                    },
                },
            }
        }

        result = is_cached("spec", "pkg-a", build_status, {"source_commit": "abc123"}, set())
        assert result is False

    def test_early_stage_force_cascades_downstream(self):
        """Force run at spec cascades to vendor, srpm, mock, copr."""
        meta = {}
        build_status = {
            "stages": {
                "spec": {"pkg-a": {"state": "success", "force_run": True}},
                "vendor": {"pkg-a": {"state": "success", "force_run": False}},
                "srpm": {"pkg-a": {"state": "success", "force_run": False}},
                "mock": {"pkg-a": {"state": "success", "force_run": False}},
                "copr": {"pkg-a": {"state": "success", "force_run": False}},
            }
        }

        forced = compute_forced_stages("pkg-a", meta, build_status, set())
        assert forced == set(STAGE_ORDER)

    def test_no_dependencies_returns_empty_forced_set(self):
        """compute_forced_stages returns empty set when no force_run and no rebuilt deps."""
        meta = {}
        build_status = {
            "stages": {s: {"pkg-a": {"state": "success", "force_run": False}} for s in STAGE_ORDER}
        }

        forced = compute_forced_stages("pkg-a", meta, build_status, set())
        assert forced == set()
