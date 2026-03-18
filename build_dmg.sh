#!/bin/bash
set -euo pipefail

APP_PATH="dist/pix.app"
DMG_PATH="dist/pix.dmg"
VOLUME_NAME="pix"

if [ ! -d "$APP_PATH" ]; then
    echo "Missing $APP_PATH, building app bundle first..."
    ./build.sh
fi

STAGING_DIR="$(mktemp -d "${TMPDIR:-/tmp}/pix-dmg.XXXXXX")"

cleanup() {
    rm -rf "$STAGING_DIR"
}

trap cleanup EXIT

cp -R "$APP_PATH" "$STAGING_DIR/"
ln -s /Applications "$STAGING_DIR/Applications"
rm -f "$DMG_PATH"

hdiutil create \
    -volname "$VOLUME_NAME" \
    -srcfolder "$STAGING_DIR" \
    -ov \
    -format UDZO \
    "$DMG_PATH"

echo "DMG created: $DMG_PATH"
