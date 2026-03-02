# Error: commit-based pkg FETCHCONTENT_SOURCE_DIR uses %{version} instead of %{commit}

`2026-03-02` | `hyprtavern` | stage: mock | fc43

## Error

```
CMake Error at /usr/share/cmake/Modules/FetchContent.cmake:2057 (message):
  Manually specified source directory is missing:
    FETCHCONTENT_SOURCE_DIR_GLAZE -->
      /builddir/build/BUILD/hyprtavern-0_20260131git946aa84-build/hyprtavern-0^20260131git946aa84/glaze-src
```

## Meaning

`gen-spec.py` generates the cmake flag:

```
-DFETCHCONTENT_SOURCE_DIR_GLAZE=%{_builddir}/%{name}-%{version}/glaze-src
```

For a commit-based package `%autosetup -n %{name}-%{commit}` extracts the tarball into
`hyprtavern-<full_hash>/`, not `hyprtavern-<version>/`. The cmake flag pointed at the
wrong (non-existent) directory.

The `^` in `0^20260131git946aa84` is also sanitised to `_` by RPM for the outer build
directory name (`hyprtavern-0_20260131git946aa84-build`), making the path doubly wrong.

## Fix

In `scripts/gen-spec.py`, detect whether `commit` is set and pick the correct subdirectory:

```python
src_subdir = "%{name}-%{commit}" if pkg.get("commit") else "%{name}-%{version}"
flags = ["-DFETCHCONTENT_FULLY_DISCONNECTED=ON"] + [
    f"-DFETCHCONTENT_SOURCE_DIR_{d['cmake_var']}="
    f"%{{_builddir}}/{src_subdir}/{d['name']}-src"
    for d in bundled_deps
]
```

## Notes

- Only affects packages that have **both** `commit:` and `bundled_deps:` in `packages.yaml`.
- `%{name}-%{commit}` matches exactly the directory `%autosetup -n %{name}-%{commit}` creates.
- The `^` → `_` RPM normalisation only affects the outer `<pkg>-<ver>-build/` wrapper, not the
  inner source dir, so `%{name}-%{commit}` with the literal `^` in `%{version}` would still
  resolve correctly for the inner path.
