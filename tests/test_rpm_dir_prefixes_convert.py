"""Tests for scripts/rpm-dir-prefixes-convert.py.

Regression coverage for the fix that replaced apply_replacements()'s raw-text
substitution with in-place mutation of the parsed YAML tree (see
docs/CHANGELOG.md 2026-08-23). The old code did a file-global `str.replace`
per changed `files:` entry, unscoped to `files:` lists -- a path string that
also occurred in `requires:`, `build.install`, a `description`, etc. got
rewritten too, and it also emitted double quotes into a file where every
`files:` entry is single-quoted. Neither is possible once the mutation
happens on the parsed dict via `iter_file_lists()`.
"""

import importlib
import sys
from pathlib import Path

import pytest
import yaml

sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

conv = importlib.import_module("scripts.rpm-dir-prefixes-convert")


@pytest.fixture
def packages_yaml(tmp_path, monkeypatch):
    """Point the converter's own PACKAGES_YAML/ROOT at a fresh tmp dir.

    `from lib.paths import PACKAGES_YAML, ROOT` in rpm-dir-prefixes-convert.py
    is a value import, so monkeypatching lib.paths would not redirect it --
    patch the loaded module's own attributes instead (same gotcha as
    lib.yaml_utils). ROOT must also move so main()'s closing
    `PACKAGES_YAML.relative_to(ROOT)` doesn't raise on an unrelated path.
    """
    monkeypatch.setattr(conv, "ROOT", tmp_path)
    path = tmp_path / "packages.yaml"
    monkeypatch.setattr(conv, "PACKAGES_YAML", path)
    return path


class TestApplyReplacementsScoping:
    """The bug: a raw-text replace isn't scoped to `files:` lists."""

    def test_matching_requires_entry_is_untouched(self):
        """Modelled on the real Hyprshot package: same path in files: and
        requires:. Confirmed to fail under the old raw-text implementation.
        """
        data = {
            "Hyprshot": {
                "files": ["/usr/bin/notify-send"],
                "requires": ["/usr/bin/notify-send", "grim"],
            }
        }

        changed = conv.apply_replacements(data, reverse=False)

        assert changed == 1
        assert data["Hyprshot"]["files"] == ["%{_bindir}/notify-send"]
        assert data["Hyprshot"]["requires"] == ["/usr/bin/notify-send", "grim"]

    def test_matching_description_is_untouched(self):
        """A files: path that also appears inside a description string."""
        data = {
            "pkg": {
                "files": ["/usr/bin/foo"],
                "description": "Installs to /usr/bin/foo by default",
            }
        }

        conv.apply_replacements(data, reverse=False)

        assert data["pkg"]["files"] == ["%{_bindir}/foo"]
        assert data["pkg"]["description"] == "Installs to /usr/bin/foo by default"

    def test_unquoted_list_item_duplicate_is_untouched(self):
        """Exercises the old third (line-anchored regex) pass: an unquoted
        files: entry duplicated as an unquoted build_requires: item."""
        data = {
            "pkg": {
                "files": ["/usr/bin/foo"],
                "build_requires": ["/usr/bin/foo"],
            }
        }

        conv.apply_replacements(data, reverse=False)

        assert data["pkg"]["files"] == ["%{_bindir}/foo"]
        assert data["pkg"]["build_requires"] == ["/usr/bin/foo"]


class TestApplyReplacementsCorrectness:
    def test_duplicate_path_across_packages_converts_in_both(self):
        """Real instance: %{_libdir}/libcava.so.* lives in both libcava and
        libcava-v0's files: lists."""
        data = {
            "libcava": {"files": ["%{_libdir}/libcava.so.*"]},
            "libcava-v0": {"files": ["%{_libdir}/libcava.so.*"]},
        }

        changed = conv.apply_replacements(data, reverse=True)

        assert changed == 2
        assert data["libcava"]["files"] == ["/usr/lib64/libcava.so.*"]
        assert data["libcava-v0"]["files"] == ["/usr/lib64/libcava.so.*"]

    def test_devel_files_are_covered(self):
        data = {"pkg": {"devel": {"files": ["/usr/include/pkg/pkg.h"]}}}

        changed = conv.apply_replacements(data, reverse=False)

        assert changed == 1
        assert data["pkg"]["devel"]["files"] == ["%{_includedir}/pkg/pkg.h"]

    def test_directive_only_entries_never_change(self):
        """%license/%doc entries have no leading `/` or `%{` and are never a
        candidate -- '%license LICENSE' appears 46x, '%doc README.md' 39x in
        the real packages.yaml."""
        data = {
            "pkg": {
                "files": ["%license LICENSE", "%doc README.md", "/usr/bin/pkg"]
            }
        }

        changed = conv.apply_replacements(data, reverse=False)

        assert changed == 1
        assert data["pkg"]["files"] == [
            "%license LICENSE",
            "%doc README.md",
            "%{_bindir}/pkg",
        ]

    def test_non_files_keys_are_never_visited(self):
        data = {
            "pkg": {
                "files": [],
                "requires": ["/usr/bin/foo"],
                "build_requires": ["/usr/bin/bar"],
            }
        }

        changed = conv.apply_replacements(data, reverse=False)

        assert changed == 0
        assert data["pkg"]["requires"] == ["/usr/bin/foo"]
        assert data["pkg"]["build_requires"] == ["/usr/bin/bar"]


class TestMainCli:
    def test_dry_run_writes_nothing(self, packages_yaml, monkeypatch, capsys):
        packages_yaml.write_text("---\npkg:\n  files:\n  - /usr/bin/foo\n")
        before = packages_yaml.read_text()

        monkeypatch.setattr(sys, "argv", ["prog", "--dry-run"])
        conv.main()

        assert packages_yaml.read_text() == before
        assert "[dry-run] No changes written." in capsys.readouterr().out

    def test_write_produces_valid_yaml_and_keeps_document_start(
        self, packages_yaml, monkeypatch
    ):
        packages_yaml.write_text("---\npkg:\n  files:\n  - /usr/bin/foo\n")

        monkeypatch.setattr(sys, "argv", ["prog"])
        conv.main()

        text = packages_yaml.read_text()
        assert text.startswith("---\n")
        data = yaml.safe_load(text)
        assert data["pkg"]["files"] == ["%{_bindir}/foo"]

    def test_write_uses_single_quotes(self, packages_yaml, monkeypatch):
        """The old code's line-53 `quoted_new` emitted double quotes for any
        macro-containing replacement; the shared dumper keeps single quotes,
        matching every existing files: entry in packages.yaml."""
        packages_yaml.write_text("---\npkg:\n  files:\n  - /usr/bin/foo\n")

        monkeypatch.setattr(sys, "argv", ["prog"])
        conv.main()

        assert "'%{_bindir}/foo'" in packages_yaml.read_text()
        assert '"%{_bindir}/foo"' not in packages_yaml.read_text()

    def test_no_matches_reports_nothing_to_normalize(
        self, packages_yaml, monkeypatch, capsys
    ):
        packages_yaml.write_text("---\npkg:\n  files:\n  - '%{_bindir}/foo'\n")
        before = packages_yaml.read_text()

        monkeypatch.setattr(sys, "argv", ["prog"])
        conv.main()

        assert packages_yaml.read_text() == before
        assert "Nothing to normalize" in capsys.readouterr().out
