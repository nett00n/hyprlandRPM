#!/usr/bin/env python3
"""Validate packages.yaml for configuration issues.

Checks for:
- Self-dependencies (package depends on itself)
- Invalid dependency references (depends_on references non-existent packages)
"""

import sys
import yaml


def main() -> None:
    """Validate packages.yaml."""
    with open("packages.yaml") as f:
        packages = yaml.safe_load(f)

    if not packages:
        print("error: packages.yaml is empty or invalid")
        sys.exit(1)

    errors = []

    for pkg, config in packages.items():
        deps = config.get("depends_on", [])

        # Check for self-dependency
        if pkg in deps:
            errors.append(
                f"  {pkg}: self-dependency detected (remove '{pkg}' from depends_on)"
            )

        # Check for invalid dependencies
        for dep in deps:
            if dep not in packages:
                errors.append(
                    f"  {pkg}: invalid dependency '{dep}' (not found in packages.yaml)"
                )

    if errors:
        print("error: packages.yaml validation failed:", file=sys.stderr)
        for err in errors:
            print(err, file=sys.stderr)
        sys.exit(1)

    print("✓ packages.yaml validation passed")


if __name__ == "__main__":
    main()
