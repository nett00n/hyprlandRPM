# Features

- Options for update script: latest release, latest tag, pinned tag, pinned commit, latest commit
- Add ARM64 local build support
- Implement incremental build caching to speed up repeated builds
- Add cross-version build matrix visualization
- Auto-bump submodule versions on upstream releases
- **THINK**: reduce rebuilds count, checking if this commit with this j2 template and this depens_on versions is already built
- Separate prod builds and local debug ones
