# Features

- Add ARM64 local build support. We did not encounter arch-tangled errors. Yet.
- Implement incremental build caching to speed up repeated builds.
- Add cross-version build matrix visualization.
- **THINK**: reduce rebuilds count, checking if this commit with this j2 template and this depens_on versions is already built
- Separate prod builds and local debug ones
- #2.0 split management system and hyprland repo content. Make automations repo a submodule of content repo (?)
