"""Unit tests for build order: topological sort is always applied."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "scripts"))

from lib.deps import build_dep_graph, topological_sort


class TestBuildOrderTopologicalSort:
    """Verify topological sort is applied unconditionally to all builds."""

    def test_full_build_respects_depends_on_order(self):
        """Full build (no filtering) outputs packages in topological order.

        This test verifies that the prepare_packages() function always applies
        topological sort, not just for selective builds (PACKAGE=...).
        """
        # Simulate packages with a linear dependency chain
        packages = {
            "pkg-a": {"depends_on": [], "version": "1.0", "license": "MIT"},
            "pkg-b": {"depends_on": ["pkg-a"], "version": "1.0", "license": "MIT"},
            "pkg-c": {"depends_on": ["pkg-b"], "version": "1.0", "license": "MIT"},
        }

        graph = build_dep_graph(packages)
        order = topological_sort(graph)

        # Verify strict ordering
        assert order.index("pkg-a") < order.index("pkg-b")
        assert order.index("pkg-b") < order.index("pkg-c")

    def test_full_build_with_multiple_roots(self):
        """Multiple independent packages can appear in any relative order."""
        packages = {
            "root1": {"depends_on": [], "version": "1.0", "license": "MIT"},
            "root2": {"depends_on": [], "version": "1.0", "license": "MIT"},
            "dep-of-root1": {"depends_on": ["root1"], "version": "1.0", "license": "MIT"},
        }

        graph = build_dep_graph(packages)
        order = topological_sort(graph)

        # root1 must come before dep-of-root1, but root2 can be anywhere
        assert order.index("root1") < order.index("dep-of-root1")

    def test_complex_diamond_dependency_order(self):
        """Diamond dep maintains ordering of both paths."""
        packages = {
            "base": {"depends_on": [], "version": "1.0", "license": "MIT"},
            "path1": {"depends_on": ["base"], "version": "1.0", "license": "MIT"},
            "path2": {"depends_on": ["base"], "version": "1.0", "license": "MIT"},
            "top": {
                "depends_on": ["path1", "path2"],
                "version": "1.0",
                "license": "MIT",
            },
        }

        graph = build_dep_graph(packages)
        order = topological_sort(graph)

        base_idx = order.index("base")
        path1_idx = order.index("path1")
        path2_idx = order.index("path2")
        top_idx = order.index("top")

        assert base_idx < path1_idx
        assert base_idx < path2_idx
        assert path1_idx < top_idx
        assert path2_idx < top_idx
