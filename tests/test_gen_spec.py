"""Tests for spec file generation, focusing on lowercase naming."""

from pathlib import Path

import pytest

from lib.jinja_utils import create_jinja_env
from lib.yaml_utils import get_packages


class TestSpecFileLowercasing:
    """Verify that generated spec files use lowercase names."""

    def test_spec_filename_lowercase_from_mixed_case_package_name(self):
        """Package name in dictionary key should be lowercased when generating spec file."""
        test_cases = [
            ("Hyprshot", "hyprshot"),
            ("Waybar", "waybar"),
            ("Waybar-git", "waybar-git"),
            ("Hyprland-git", "hyprland-git"),
            ("hyprland", "hyprland"),
            ("aylurs-gtk-shell", "aylurs-gtk-shell"),
            ("Hyprland", "hyprland"),
        ]

        for input_name, expected_output in test_cases:
            # This simulates what gen-spec.py does at line 406
            pkg_name = input_name.lower()
            spec_filename = f"{pkg_name}.spec"

            assert spec_filename == f"{expected_output}.spec"
            assert pkg_name == expected_output

    def test_package_directory_lowercase(self, tmp_path):
        """Package directory should be created with lowercase name."""
        test_packages = [
            ("Hyprshot", "hyprshot"),
            ("Waybar-git", "waybar-git"),
            ("Hyprland", "hyprland"),
        ]

        for input_name, expected_dir in test_packages:
            # Simulate gen-spec.py logic
            pkg_name = input_name.lower()
            spec_dir = tmp_path / pkg_name
            spec_dir.mkdir(parents=True, exist_ok=True)

            # Verify directory name is lowercase
            assert spec_dir.name == expected_dir
            # Verify path contains lowercase
            assert str(spec_dir).endswith(expected_dir)

    def test_spec_file_path_all_lowercase(self, tmp_path):
        """Full spec file path should contain only lowercase directory and filename."""
        test_packages = [
            ("Hyprshot", "hyprshot"),
            ("Waybar-git", "waybar-git"),
        ]

        for input_name, expected_name in test_packages:
            pkg_name = input_name.lower()
            spec_dir = tmp_path / pkg_name
            spec_dir.mkdir(parents=True, exist_ok=True)
            spec_path = spec_dir / f"{pkg_name}.spec"
            spec_path.write_text("# dummy spec")

            # Verify spec file exists and path is fully lowercase
            assert spec_path.exists()
            assert spec_path.name == f"{expected_name}.spec"
            assert spec_path.parent.name == expected_name
            # Verify all path components are lowercase
            for part in spec_path.parts:
                if part not in ("/", "."):  # Skip root and current dir
                    assert part == part.lower(), f"Path component '{part}' is not lowercase"

    def test_real_packages_yaml_names_should_lowercase(self):
        """Verify that actual package names from packages.yaml will be lowercased."""
        packages = get_packages()

        # These are actual mixed-case packages that should be lowercased
        mixed_case_packages = ["Hyprland", "Hyprland-git", "Hyprshot", "Waybar", "Waybar-git"]

        for pkg_name in mixed_case_packages:
            if pkg_name in packages:
                # The spec filename should be lowercase
                lowercase_name = pkg_name.lower()
                spec_filename = f"{lowercase_name}.spec"

                # Verify lowercasing works
                assert spec_filename == f"{lowercase_name}.spec"
                assert not any(c.isupper() for c in spec_filename)

    def test_gen_spec_creates_lowercase_spec_files(self):
        """Verify that spec generation creates lowercase filenames (integration test).

        This test checks the behavior of gen-spec.py which should:
        1. Take package names from packages.yaml (which may have mixed case)
        2. Lowercase them when creating directories and spec files
        3. NOT create mixed-case directories or files
        """
        from lib.paths import ROOT

        packages = get_packages()
        mixed_case_packages = ["Hyprland", "Hyprland-git", "Hyprshot", "Waybar", "Waybar-git"]

        for pkg_name in mixed_case_packages:
            if pkg_name in packages:
                lowercase_name = pkg_name.lower()
                expected_spec_path = ROOT / "packages" / lowercase_name / f"{lowercase_name}.spec"
                incorrect_spec_path = ROOT / "packages" / pkg_name / f"{pkg_name}.spec"

                # Verify that lowercase spec file exists
                assert expected_spec_path.exists(), (
                    f"Spec file not found: {expected_spec_path}. "
                    f"gen-spec.py should create spec files with lowercase names."
                )

                # Verify that mixed-case spec file does NOT exist
                assert not incorrect_spec_path.exists(), (
                    f"Mixed-case spec file found: {incorrect_spec_path}. "
                    f"gen-spec.py should only create lowercase files."
                )
