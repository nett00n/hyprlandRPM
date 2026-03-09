# packages.yaml structure migration plan

## Problem

The current top-level package entry is a flat bag of mixed concerns:

| Field | Concern |
|---|---|
| `version`, `release`, `license`, `summary`, `description`, `url` | RPM metadata |
| `sources`, `source_name`, `commit` | Upstream source |
| `build_system`, `configure_flags`, `build_commands`, `install_commands`, `prep_commands`, `bundled_deps`, `source_subdir`, `no_lto` | Build config |
| `build_requires`, `requires`, `depends_on` | Dependencies |
| `files`, `devel` | File manifests |
| `buildarch`, `no_debug_package` | RPM flags |

---

## Proposed structure

### Core grouping

Group scattered fields into sub-objects: `source`, `build`, and `rpm`.

```yaml
packages:

  mylib:
    # -- RPM identity ----------------------------------------------------------
    version: "1.2.3"
    release: "%autorelease"
    license: MIT
    summary: A short one-line description
    description: |
      Longer description.
    url: https://github.com/myorg/mylib

    # -- source / upstream -----------------------------------------------------
    source:
      # name: set when tarball extracts as MyLib-1.2.3/ not mylib-1.2.3/
      name: ""
      # commit: only for snapshot builds without a version tag
      commit:
        full: 4a3f9c1bde82f1a7c2e3d456789abcdef1234567
        date: "20241015"
      archives:
        - "%{url}/archive/refs/tags/v%{version}.tar.gz#/%{name}-%{version}.tar.gz"
      bundled_deps:
        # cmake FetchContent / offline vendoring
        - name: somedep
          version: "1.5.0"
          url: "https://github.com/vendor/somedep/archive/refs/tags/v1.5.0.tar.gz"
          cmake_var: SOMEDEP
          source_subdir: src   # optional: path inside extracted tarball

    # -- build config ----------------------------------------------------------
    build:
      system: cmake            # cmake | meson | autotools | configure | make | python
      subdir: ""               # build from subdirectory inside the source tree
      no_lto: false
      # configure_flags: only used when system: configure
      configure_flags:
        - --prefix=%{_prefix}
        - --libdir=%{_libdir}
      # lifecycle hook overrides
      prep:     []             # shell lines injected after %autosetup
      commands: []             # replaces the entire %build phase if set
      install:  []             # replaces the entire %install phase if set

    # -- dependencies ----------------------------------------------------------
    build_requires:
      - cmake
      - gcc-c++
      - ninja-build
      - pkgconfig(somedep)
    requires:
      - somedep
    # depends_on: local build-order deps (packages in this same yaml)
    depends_on:
      - mybaselib

    # -- file manifests --------------------------------------------------------
    files:
      - "%license LICENSE"
      - "%doc README.md"
      - "%{_libdir}/libmylib.so.*"
    devel:
      requires:
        - pkgconfig(somedep)
      files:
        - "%{_includedir}/mylib/"
        - "%{_libdir}/libmylib.so"
        - "%{_libdir}/pkgconfig/mylib.pc"

    # -- RPM flags -------------------------------------------------------------
    rpm:
      buildarch: ~             # noarch | x86_64 | etc. (omit = default)
      no_debug_package: false
```

### Fedora version overrides

COPR builds the same `.spec` across multiple Fedora versions. The spec encodes
per-version differences as RPM `%if 0%{?fedora} == N` conditionals. The yaml
mirrors that directly:

```yaml
    # -- per-distro overrides --------------------------------------------------
    # Each key is a Fedora version number (int).
    # The generated spec wraps each block in:
    #   %if 0%{?fedora} == <N>  ...  %endif
    distro:
      42:
        # Extra deps only needed on Fedora 42
        extra_build_requires:
          - compat-foo-devel
        # Patches applied only on this version
        patches:
          - name: fix-wayland-api-fc42.patch
            url: "https://example.com/patches/fix-fc42.patch"
        # Additional build config for this version
        build:
          extra_configure_flags:
            - --disable-new-api
          extra_prep:
            - "sed -i 's/old_symbol/new_symbol/' src/foo.c"

      44:
        extra_build_requires:
          - new-required-dep
        # Override the full version for a backport
        version: "1.2.2-backport"
```

Generated spec output example:

```spec
BuildRequires: cmake
BuildRequires: gcc-c++
%if 0%{?fedora} == 42
BuildRequires: compat-foo-devel
Patch0: fix-wayland-api-fc42.patch
%endif
%if 0%{?fedora} == 44
BuildRequires: new-required-dep
%endif
```

---

## Field migration table

| Old field | New location |
|---|---|
| `source_name` | `source.name` |
| `commit` | `source.commit` |
| `sources[].url` | `source.archives[]` (plain strings, not dicts) |
| `bundled_deps` | `source.bundled_deps` |
| `build_system` | `build.system` |
| `source_subdir` | `build.subdir` |
| `no_lto` | `build.no_lto` |
| `configure_flags` | `build.configure_flags` |
| `prep_commands` | `build.prep` |
| `build_commands` | `build.commands` |
| `install_commands` | `build.install` |
| `buildarch` | `rpm.buildarch` |
| `no_debug_package` | `rpm.no_debug_package` |

`build_requires`, `requires`, `depends_on`, `files`, `devel` stay at the top
level — they are already clear and do not benefit from nesting.

---

## Design notes

- `source.archives` is simplified from `[{url: ...}]` to a plain string list —
  the dict wrapper had only one key.
- `distro:` keys are integers (Fedora version numbers) so YAML needs no quoting
  and iteration is straightforward in Python.
- `distro.N.build` uses `extra_*` prefix to signal additive behaviour, not
  replacement of the base config.
- The `rpm:` grouping is low-priority — `buildarch`/`no_debug_package` are
  infrequent enough that they can be migrated last.
