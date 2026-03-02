Name:           hyprland-guiutils
Version:        0.2.1
Release:        %autorelease%{?dist}
Summary:        Hyprland GUI utilities
License:        BSD-3-Clause
URL:            https://github.com/hyprwm/hyprland-guiutils
Source0:        %{url}/archive/refs/tags/v%{version}.tar.gz

BuildRequires:  aquamarine-devel
BuildRequires:  cmake
BuildRequires:  gcc-c++
BuildRequires:  hyprgraphics-devel
BuildRequires:  ninja-build
BuildRequires:  pkgconfig(cairo)
BuildRequires:  pkgconfig(hyprlang)
BuildRequires:  pkgconfig(hyprtoolkit)
BuildRequires:  pkgconfig(hyprutils)
BuildRequires:  pkgconfig(libdrm)
BuildRequires:  pkgconfig(pixman-1)
BuildRequires:  pkgconfig(xkbcommon)

%description
Hyprland GUI utilities (successor to hyprland-qtutils)

%prep
%autosetup

%build
%cmake
%cmake_build

%install
%cmake_install

%files
%doc README.md
%license LICENSE
%{_prefix}/bin/hyprland-*

%changelog
* Mon Dec 29 2025 Vladimir nett00n Budylnikov <git@nett00n.org> - 0.2.1-%autorelease
- Some minor stuff
- welcome: add ecosystem tab
- welcome: mention launcher keybind
- welcome: add some missing apps to the dropdown menu by @Honkazel in https://github.com/hyprwm/hyprland-guiutils/pull/9
- run: escape closes the window by @Havner in https://github.com/hyprwm/hyprland-guiutils/pull/13
- @Honkazel made their first contribution in https://github.com/hyprwm/hyprland-guiutils/pull/9
- @Havner made their first contribution in https://github.com/hyprwm/hyprland-guiutils/pull/13
- **Full Changelog**: https://github.com/hyprwm/hyprland-guiutils/compare/v0.2.0...v0.2.1
