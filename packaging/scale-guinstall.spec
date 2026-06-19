Name:           scale-guinstall
Version:        1.0.0
Release:        1%{?dist}
Summary:        IBM Storage Scale Installation Toolkit GUI backend
License:        MIT
URL:            https://github.com/cdmaestas/Scale-GUInstall
BuildArch:      noarch

# Python 3.10+ required; on RHEL 8/9 install python3.11 from AppStream:
#   sudo dnf install python3.11
Requires:       (python3 >= 3.10 or python3.11 or python3.12 or python3.13)

%description
Scale GUInstall provides a web-based GUI for the IBM Storage Scale
Installation Toolkit (spectrumscale). This package installs the Flask
backend server that the GUI connects to for live command execution.

Open Scale-GUInstall.html in a browser on your workstation, establish
an SSH tunnel to this node (ssh -L 5001:127.0.0.1:5001 user@this-node),
and the GUI will connect automatically.

%prep
# Nothing to prep — sources are copied in by build-pkg.sh

%install
install -d %{buildroot}/usr/lib/scale-guinstall
install -d %{buildroot}/usr/bin
install -d %{buildroot}/usr/lib/systemd/system
install -d %{buildroot}/etc/scale-guinstall

install -m 0755 %{_sourcedir}/scale-server.py  %{buildroot}/usr/lib/scale-guinstall/scale-server.py
install -m 0644 %{_sourcedir}/Scale-GUInstall.html %{buildroot}/usr/lib/scale-guinstall/Scale-GUInstall.html
install -m 0755 %{_sourcedir}/scale-guinstall   %{buildroot}/usr/bin/scale-guinstall
install -m 0644 %{_sourcedir}/scale-guinstall.service %{buildroot}/usr/lib/systemd/system/scale-guinstall.service

%post
# Create a virtual environment and install Flask into it
VENV=/usr/lib/scale-guinstall/venv

# Find a compliant Python
PYTHON=""
for candidate in python3.14 python3.13 python3.12 python3.11 python3.10; do
    if command -v "$candidate" &>/dev/null; then
        PYTHON="$candidate"
        break
    fi
done
if [[ -z "$PYTHON" ]]; then
    # Fall back to python3 if it meets the requirement
    if python3 -c "import sys; exit(0 if sys.version_info >= (3,10) else 1)" 2>/dev/null; then
        PYTHON="python3"
    else
        echo "WARNING: Python 3.10+ not found — Flask will not be installed."
        echo "         Install python3.11 and re-run: %post"
        exit 0
    fi
fi

echo "scale-guinstall: creating virtual environment with $PYTHON..."
"$PYTHON" -m venv "$VENV"
"$VENV/bin/pip" install --quiet --upgrade pip
"$VENV/bin/pip" install --quiet "flask>=3.0,<4"
echo "scale-guinstall: Flask installed. Start with: scale-guinstall"

%preun
# Stop and disable the service if it's running before removal
if [ $1 -eq 0 ]; then
    systemctl stop scale-guinstall 2>/dev/null || true
    systemctl disable scale-guinstall 2>/dev/null || true
fi

%postun
if [ $1 -eq 0 ]; then
    rm -rf /usr/lib/scale-guinstall/venv
fi

%files
/usr/lib/scale-guinstall/scale-server.py
/usr/lib/scale-guinstall/Scale-GUInstall.html
/usr/bin/scale-guinstall
/usr/lib/systemd/system/scale-guinstall.service

%changelog
* Thu Jun 19 2026 cdmaestas <cdmaestas@gmail.com> - 1.0.0-1
- Initial package release
