%global commit 83ce4b2a70d3c1a6ed8dc6db7f1fac17db2215b1
%global shortcommit %(c=%{commit}; echo ${c:0:7})
%global commitdate 20260818

Name:           hyprland-plugins
Version:        0.56.0^20260818git83ce4b2
Release:        1%{?dist}
Summary:        Official plugins for Hyprland
License:        BSD-3-Clause
URL:            https://github.com/hyprwm/hyprland-plugins
Source0:        https://github.com/hyprwm/hyprland-plugins/archive/83ce4b2a70d3c1a6ed8dc6db7f1fac17db2215b1/hyprland-plugins-83ce4b2.tar.gz
Patch0:         hyprland-0.54-exclude-incompatible-plugins.patch

BuildRequires:  cmake
BuildRequires:  gcc-c++
BuildRequires:  hyprland-devel
BuildRequires:  ninja-build
BuildRequires:  pkgconfig(libdrm)
BuildRequires:  pkgconfig(libinput)
BuildRequires:  pkgconfig(libudev)
BuildRequires:  pkgconfig(pangocairo)
BuildRequires:  pkgconfig(pixman-1)
BuildRequires:  pkgconfig(wayland-server)
BuildRequires:  pkgconfig(xkbcommon)



%description
hyprland-plugins

This repo houses official plugins for Hyprland.
Plugin list

- borders-plus-plus -> adds one or two additional borders to windows
- csgo-vulkan-fix -> fixes custom resolutions on CS:GO with -vulkan
- hyprbars -> adds title bars to windows
- hyprexpo -> adds an expo-like workspace overview
- hyprfocus -> flashfocus for hyprland
- hyprtrails -> adds smooth trails behind moving windows
- hyprwinwrap -> clone of xwinwrap, allows you to put any app as a wallpaper
- xtra-dispatchers -> adds some new dispatchers

Note: hyprscrolling and hyprtrails are temporarily excluded (incompatible with hyprland 0.54)

Maintainer info:

Source repository: https://github.com/nett00n/hyprland-copr

COPR repository:   https://copr.fedorainfracloud.org/coprs/nett00n/hyprland/

Package info:
Commit:            83ce4b2a70d3c1a6ed8dc6db7f1fac17db2215b1

%prep
%autosetup -p1 -n %{name}-%{commit}

%build
%cmake
%cmake_build

%install
%cmake_install

%files
%doc README.md
%license LICENSE
%{_prefix}/lib/libhypr*.so

%changelog
* Tue Aug 18 2026 nett00n <copr@nett00n.org> - 0.56.0^20260818git83ce4b2-1

- vkfix: chase hyprland
