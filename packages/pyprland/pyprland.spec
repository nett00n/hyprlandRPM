Name:           pyprland
Version:        3.1.1
Release:        %autorelease%{?dist}
Summary:        FIXME
License:        MIT
URL:            https://github.com/hyprland-community/pyprland.git
Source0:        %{url}/archive/refs/tags/v%{version}.tar.gz


%description
FIXME

%prep
%autosetup

%build


%install


%files
%doc README.md
%license LICENSE

%package devel
Summary:        Development files for FIXME
Requires:       %{name} = %{version}-%{release}

%description devel
Development files for pyprland.

%files devel

%changelog
* Fri Mar 06 2026 Vladimir nett00n Budylnikov <git@nett00n.org> - 3.1.1-%autorelease
- Update to 3.1.1
