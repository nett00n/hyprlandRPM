"""Tests for uncovered branches in cache.py."""

import sys
from pathlib import Path
from unittest.mock import patch, MagicMock

sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

import pytest

from lib.cache import (
    compute_input_hashes,
    hashes_match,
)


class TestComputeInputHashes:
    """Test compute_input_hashes function."""

    def test_computes_hashes_for_valid_package(self):
        """Should compute hashes for a valid package."""
        meta = {
            "version": "1.0",
            "license": "MIT",
            "summary": "Test",
            "description": "Test pkg",
            "url": "https://example.com",
            "source": {"archives": ["https://example.com/test-1.0.tar.gz"]},
            "build": {"system": "cmake"},
        }
        all_packages = {"test-pkg": meta}

        result = compute_input_hashes("test-pkg", meta, all_packages)
        assert isinstance(result, dict)
        # Should have some hash keys
        assert len(result) > 0

    def test_computes_hashes_with_no_dependencies(self):
        """Should compute hashes when package has no dependencies."""
        meta = {
            "version": "1.0",
            "license": "MIT",
            "summary": "Test",
            "description": "Test pkg",
            "url": "https://example.com",
            "source": {"archives": ["https://example.com/test-1.0.tar.gz"]},
            "build": {"system": "cmake"},
        }
        all_packages = {"test-pkg": meta}

        result = compute_input_hashes("test-pkg", meta, all_packages)
        assert isinstance(result, dict)

    def test_computes_consistent_hashes(self):
        """Should compute consistent hashes for same input."""
        meta = {
            "version": "1.0",
            "license": "MIT",
            "summary": "Test",
            "description": "Test pkg",
            "url": "https://example.com",
            "source": {"archives": ["https://example.com/test-1.0.tar.gz"]},
            "build": {"system": "cmake"},
        }
        all_packages = {"test-pkg": meta}

        hash1 = compute_input_hashes("test-pkg", meta, all_packages)
        hash2 = compute_input_hashes("test-pkg", meta, all_packages)

        assert hash1 == hash2


class TestHashesMatch:
    """Test hashes_match function."""

    def test_matches_identical_hashes(self):
        """Should return True for identical hashes."""
        stored_entry = {
            "hashes": {
                "config": "abc123",
                "version": "def456",
            }
        }
        new = {
            "config": "abc123",
            "version": "def456",
        }

        result = hashes_match(stored_entry, new)
        assert result is True

    def test_detects_mismatched_hashes(self):
        """Should return False for different hashes."""
        stored_entry = {
            "hashes": {
                "config": "abc123",
                "version": "def456",
            }
        }
        new = {
            "config": "different",
            "version": "def456",
        }

        result = hashes_match(stored_entry, new)
        assert result is False

    def test_returns_false_when_no_stored_hashes(self):
        """Should return False when stored entry has no hashes."""
        stored_entry = {
            "config": "abc123",
        }
        new = {
            "config": "abc123",
            "version": "def456",
        }

        result = hashes_match(stored_entry, new)
        assert result is False

    def test_returns_false_when_stored_hashes_empty(self):
        """Should return False when stored hashes is empty."""
        stored_entry = {
            "hashes": {}
        }
        new = {
            "config": "abc123",
        }

        result = hashes_match(stored_entry, new)
        assert result is False
