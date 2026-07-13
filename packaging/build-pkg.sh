#!/usr/bin/env bash
# Build RPM and/or DEB packages for scale-guinstall.
#
# Usage:
#   ./build-pkg.sh          — build both RPM and DEB (skips whichever tools are missing)
#   ./build-pkg.sh --rpm    — RPM only
#   ./build-pkg.sh --deb    — DEB only
#
# Prerequisites:
#   RPM: rpmbuild  (sudo dnf install rpm-build  OR  sudo apt install rpm)
#   DEB: dpkg-deb  (sudo apt install dpkg-dev   OR  brew install dpkg)
#
# Output: dist/scale-guinstall-1.0.0-1.noarch.rpm
#         dist/scale-guinstall_1.0.0-1_all.deb

set -euo pipefail

PKG_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(dirname "$PKG_DIR")"
DIST="$ROOT/dist"
VERSION="1.0.0"
RELEASE="1"

BUILD_RPM=true
BUILD_DEB=true
for arg in "$@"; do
    case "$arg" in
        --rpm) BUILD_DEB=false ;;
        --deb) BUILD_RPM=false ;;
    esac
done

mkdir -p "$DIST"

# ── Shared: assemble staging area ────────────────────────────────────────────
STAGE="$PKG_DIR/.stage"
rm -rf "$STAGE"
mkdir -p "$STAGE"

cp "$ROOT/scale-server.py"        "$STAGE/scale-server.py"
cp "$ROOT/Scale-GUInstall.html"   "$STAGE/Scale-GUInstall.html"
cp "$ROOT/README.md"              "$STAGE/README.md"
cp "$ROOT/CHANGELOG.md"           "$STAGE/CHANGELOG.md"
cp "$PKG_DIR/scale-guinstall-wrapper"  "$STAGE/scale-guinstall"
cp "$PKG_DIR/scale-guinstall.service"  "$STAGE/scale-guinstall.service"
cp "$PKG_DIR/scale-guinstall-mmfs.sh"  "$STAGE/scale-guinstall-mmfs.sh"
gzip -9 -c "$PKG_DIR/scale-guinstall.1" > "$STAGE/scale-guinstall.1.gz"

# ── RPM ───────────────────────────────────────────────────────────────────────
build_rpm() {
    echo "==> Building RPM..."
    if ! command -v rpmbuild &>/dev/null; then
        echo "    SKIP: rpmbuild not found (sudo dnf install rpm-build)"
        return
    fi

    local rpmbuild_root="$PKG_DIR/.rpmbuild"
    mkdir -p "$rpmbuild_root"/{SPECS,SOURCES,BUILD,RPMS,SRPMS}

    cp "$STAGE"/* "$rpmbuild_root/SOURCES/"
    cp "$PKG_DIR/scale-guinstall.spec" "$rpmbuild_root/SPECS/"

    rpmbuild \
        --define "_topdir $rpmbuild_root" \
        --define "_version $VERSION" \
        --define "_release $RELEASE" \
        -bb "$rpmbuild_root/SPECS/scale-guinstall.spec"

    find "$rpmbuild_root/RPMS" -name "*.rpm" -exec cp {} "$DIST/" \;
    echo "    RPM: $(ls "$DIST/"*.rpm 2>/dev/null | tail -1)"
    rm -rf "$rpmbuild_root"
}

# ── DEB ───────────────────────────────────────────────────────────────────────
build_deb() {
    echo "==> Building DEB..."
    if ! command -v dpkg-deb &>/dev/null; then
        echo "    SKIP: dpkg-deb not found (sudo apt install dpkg-dev)"
        return
    fi

    local deb_root="$PKG_DIR/.deb"
    local deb_name="scale-guinstall_${VERSION}-${RELEASE}_all"
    rm -rf "$deb_root"
    mkdir -p "$deb_root/$deb_name/DEBIAN"
    mkdir -p "$deb_root/$deb_name/usr/lib/scale-guinstall"
    mkdir -p "$deb_root/$deb_name/usr/bin"
    mkdir -p "$deb_root/$deb_name/usr/lib/systemd/system"
    mkdir -p "$deb_root/$deb_name/usr/share/doc/scale-guinstall"
    mkdir -p "$deb_root/$deb_name/usr/share/man/man1"
    mkdir -p "$deb_root/$deb_name/etc/profile.d"

    # Copy files
    cp "$STAGE/scale-server.py"          "$deb_root/$deb_name/usr/lib/scale-guinstall/"
    cp "$STAGE/Scale-GUInstall.html"     "$deb_root/$deb_name/usr/lib/scale-guinstall/"
    cp "$STAGE/scale-guinstall"          "$deb_root/$deb_name/usr/bin/scale-guinstall"
    cp "$STAGE/scale-guinstall.service"  "$deb_root/$deb_name/usr/lib/systemd/system/"
    cp "$STAGE/scale-guinstall-mmfs.sh"  "$deb_root/$deb_name/etc/profile.d/"
    cp "$STAGE/README.md"                "$deb_root/$deb_name/usr/share/doc/scale-guinstall/"
    cp "$STAGE/CHANGELOG.md"             "$deb_root/$deb_name/usr/share/doc/scale-guinstall/"
    cp "$STAGE/scale-guinstall.1.gz"     "$deb_root/$deb_name/usr/share/man/man1/"

    # Set permissions
    chmod 0755 "$deb_root/$deb_name/usr/bin/scale-guinstall"
    chmod 0644 "$deb_root/$deb_name/usr/lib/scale-guinstall/scale-server.py"
    chmod 0644 "$deb_root/$deb_name/usr/lib/scale-guinstall/Scale-GUInstall.html"
    chmod 0644 "$deb_root/$deb_name/usr/lib/systemd/system/scale-guinstall.service"
    chmod 0644 "$deb_root/$deb_name/etc/profile.d/scale-guinstall-mmfs.sh"
    chmod 0644 "$deb_root/$deb_name/usr/share/doc/scale-guinstall/README.md"
    chmod 0644 "$deb_root/$deb_name/usr/share/doc/scale-guinstall/CHANGELOG.md"
    chmod 0644 "$deb_root/$deb_name/usr/share/man/man1/scale-guinstall.1.gz"

    # DEBIAN control files
    cp "$PKG_DIR/debian/control"    "$deb_root/$deb_name/DEBIAN/"
    cp "$PKG_DIR/debian/changelog"  "$deb_root/$deb_name/DEBIAN/"
    cp "$PKG_DIR/debian/postinst"   "$deb_root/$deb_name/DEBIAN/"
    cp "$PKG_DIR/debian/prerm"      "$deb_root/$deb_name/DEBIAN/"
    cp "$PKG_DIR/debian/postrm"     "$deb_root/$deb_name/DEBIAN/"
    chmod 0755 "$deb_root/$deb_name/DEBIAN/postinst" \
               "$deb_root/$deb_name/DEBIAN/prerm" \
               "$deb_root/$deb_name/DEBIAN/postrm"

    # Compute installed size (kB)
    local installed_size
    installed_size=$(du -sk "$deb_root/$deb_name" | cut -f1)
    sed -i.bak "s/^Version:.*/Version: ${VERSION}-${RELEASE}/" "$deb_root/$deb_name/DEBIAN/control"
    echo "Installed-Size: $installed_size" >> "$deb_root/$deb_name/DEBIAN/control"

    dpkg-deb --build --root-owner-group "$deb_root/$deb_name" "$DIST/${deb_name}.deb"
    echo "    DEB: $DIST/${deb_name}.deb"
    rm -rf "$deb_root"
}

# ── Run ───────────────────────────────────────────────────────────────────────
[[ "$BUILD_RPM" == "true" ]] && build_rpm
[[ "$BUILD_DEB" == "true" ]] && build_deb

rm -rf "$STAGE"

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  Output:"
ls -1 "$DIST/" 2>/dev/null | sed 's/^/    /'
echo ""
echo "  Install on RHEL/CentOS/Fedora:"
echo "    sudo dnf install dist/scale-guinstall-${VERSION}-${RELEASE}.noarch.rpm"
echo ""
echo "  Install on Debian/Ubuntu:"
echo "    sudo apt install ./dist/scale-guinstall_${VERSION}-${RELEASE}_all.deb"
echo ""
echo "  Start:   scale-guinstall"
echo "  Service: sudo systemctl enable --now scale-guinstall"
echo "  Tunnel:  ssh -L 5001:127.0.0.1:5001 user@installer-node"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
