Name:           hyprshutdown
Version:        0.1.0
Release:        %autorelease%{?dist}
Summary:        A graceful shutdown utility for Hyprland
License:        BSD-3-Clause
URL:            https://github.com/hyprwm/hyprshutdown
Source0:        %{url}/archive/refs/tags/v%{version}.tar.gz

BuildRequires:  cmake
BuildRequires:  gcc-c++
BuildRequires:  ninja-build
BuildRequires:  pkgconfig(hyprtoolkit)
BuildRequires:  pkgconfig(hyprutils)
BuildRequires:  pkgconfig(libdrm)
BuildRequires:  pkgconfig(pixman-1)

%description
A graceful shutdown/logout utility for Hyprland, which prevents apps from crashing / dying unexpectedly.

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

%changelog
* Thu Jan 29 2026 Vladimir nett00n Budylnikov <git@nett00n.org> - 0.1.0-%autorelease
- Initial release of hyprshutdown yay
- **Full Changelog**: https://github.com/hyprwm/hyprshutdown/commits/v0.1.0
