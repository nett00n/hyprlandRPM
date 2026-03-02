# Error: hyprtavern protocol XML files missing — project unbuildable

`2026-03-02` | `hyprtavern` | stage: mock | fc43

## Error

```
-- Found hyprwire-protocols at
...
cd .../hyprtavern-946aa84... && hyprwire-scanner --client /hyprtavern/hp_hyprtavern_barmaid_v1.xml .../protocols/
Couldn't load proto: File was not found
```

Repeated for all four protocols: `hp_hyprtavern_core_v1`, `hp_hyprtavern_kv_store_v1`,
`hp_hyprtavern_barmaid_v1`, `hp_hyprtavern_permission_authentication_v1`.

## Meaning

`CMakeLists.txt` does:

```cmake
pkg_get_variable(HYPRWIRE_PROTOCOLS_DIR hyprwire-protocols pkgdatadir)
```

then calls `hyprwire-scanner` with paths under `${HYPRWIRE_PROTOCOLS_DIR}/hyprtavern/`.

- `hyprwire-protocols` pkg-config module **does not exist** — not shipped by hyprwire or any
  other package. `pkg_get_variable` returns empty → path collapses to `/hyprtavern/<name>.xml`.
- The protocol XML files (`hp_hyprtavern_*.xml`) have **never been committed** to the hyprtavern
  repository at any point in its git history. All `protocols/` subdirectories contain only
  `.gitkeep`.

The project is in early development and the wire protocol definitions simply haven't been written
yet. **hyprtavern is not buildable from source at any existing commit.**

## Fix

No fix possible at current upstream state. Monitor the repository for commits that add:

1. The `hp_hyprtavern_*.xml` protocol definition files
2. A `hyprwire-protocols.pc` (or equivalent) to locate them at build time

Once those land, update the submodule and re-attempt packaging.

## Notes

- Initial packaging attempt used `version: "0.1.0"` but that tag doesn't exist on GitHub
  (404). Switched to commit-based version `0^20260131git946aa84` — correct approach, but
  the build still fails due to the missing protocol files.
- The README explicitly warns: "This project is still in early development. I'm working on
  adding docs and improving the protocol, but it's not set in stone yet."
- `glaze` dependency: the CMakeLists.txt requests `glaze 6.0.0` (not 7.x as in Hyprland).
  Added `bundled_deps` for glaze 7.0.0 in packages.yaml, but this is moot while the protocol
  issue blocks the build.
- Leave the `packages.yaml` entry and submodule in place so the infrastructure work (commit
  version, bundled glaze, correct FETCHCONTENT path) is ready when upstream matures.
