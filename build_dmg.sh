#!/bin/bash
set -euo pipefail

PKG_PATH="dist/pix.pkg"
DMG_PATH="dist/pix.dmg"
VOLUME_NAME="pix"

if [ ! -f "$PKG_PATH" ]; then
    echo "Missing $PKG_PATH, building installer package first..."
    ./build_pkg.sh
fi

STAGING_DIR="$(mktemp -d "${TMPDIR:-/tmp}/pix-dmg.XXXXXX")"

cleanup() {
    rm -rf "$STAGING_DIR"
}

trap cleanup EXIT

cp -R "$PKG_PATH" "$STAGING_DIR/"
ln -s /Applications "$STAGING_DIR/Applications"
rm -f "$DMG_PATH"

hdiutil create \
    -volname "$VOLUME_NAME" \
    -srcfolder "$STAGING_DIR" \
    -ov \
    -format UDZO \
    "$DMG_PATH"

echo "DMG created: $DMG_PATH"
