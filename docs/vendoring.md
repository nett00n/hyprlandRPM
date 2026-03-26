# Vendoring Strategy: Go vs Rust

## Go Vendoring ✓ (Works Well)

**Why Go vendoring works simply:**

1. `go mod vendor` downloads all dependencies (including git sources) into `vendor/`
2. Go **automatically** checks `vendor/` first during builds
3. No special configuration needed - it "just works"
4. The `vendor/` directory is self-contained and portable
5. Git dependencies are handled transparently - no special config required

**How it works in COPR builds:**
```bash
go mod vendor
# vendor/ now contains all dependencies
go build  # automatically finds everything in vendor/
```

## Rust Vendoring ✗ (Complex with Git Dependencies)

**Why Rust vendoring has issues:**

1. `cargo vendor` downloads dependencies into `vendor/`
2. Cargo does **NOT** automatically find git sources in `vendor/`
3. Requires explicit `.cargo/config.toml` configuration
4. Git source replacement syntax is complex and error-prone
5. `[net] offline = true` + git sources = unsolved problem in Cargo

**The Problem:**
```toml
# This doesn't work for git sources:
[source."https://github.com/org/repo"]
directory = "vendor/repo"  # ✗ Invalid for git sources
```

Cargo expects git sources to either:
- Still use the network (defeats offline purpose)
- Use `git = "file://..."` URLs (requires actual git repos in vendor)
- Be converted to path dependencies in Cargo.lock (requires post-processing)

## Current Approach in This Repo

**Go:** Use `go mod vendor` directly
**Rust:** Generate vendor tarball with `cargo vendor` + basic `.cargo/config.toml`
**Note:** Rust git dependencies are **not fully resolved** - requires either:
- Patching Cargo.lock to use path dependencies, OR
- Converting upstream to use releases instead of git dependencies

## References

- [Cargo vendor documentation](https://doc.rust-lang.org/cargo/commands/cargo-vendor.html)
- [Fedora Packaging Guidelines - Vendoring](https://bugzilla.redhat.com/show_bug.cgi?id=1920959)
