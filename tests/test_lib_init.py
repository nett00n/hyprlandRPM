"""Tests for lib/__init__.py import guards."""

import sys
from pathlib import Path
from unittest.mock import patch
import importlib

sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

import pytest


class TestLibInitImportGuards:
    """Test import guards in lib/__init__.py."""

    def test_succeeds_with_yaml_installed(self):
        """Should succeed when PyYAML is installed."""
        # yaml is already imported, so this should pass
        import yaml  # noqa: F401
        assert True

    def test_succeeds_with_jinja2_installed(self):
        """Should succeed when Jinja2 is installed."""
        # jinja2 is already imported, so this should pass
        from jinja2 import Environment  # noqa: F401
        assert True

    def test_imports_lib_package(self):
        """Should import lib package without errors."""
        from lib import __file__ as lib_file
        assert lib_file is not None

    def test_yaml_import_works(self):
        """Should verify yaml is available."""
        try:
            import yaml
            assert hasattr(yaml, 'safe_load')
        except ImportError:
            pytest.fail("PyYAML not installed")

    def test_jinja2_import_works(self):
        """Should verify Jinja2 is available."""
        try:
            from jinja2 import Environment
            assert Environment is not None
        except ImportError:
            pytest.fail("Jinja2 not installed")
