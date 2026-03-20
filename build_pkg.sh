#!/bin/bash
set -euo pipefail

APP_PATH="dist/pix.app"
CLI_PATH="dist/pix"
RUNTIME_PATH="dist/pix_cli"
PKG_PATH="dist/pix.pkg"
IDENTIFIER="com.kilo.pix"
VERSION="${PIX_VERSION:-1.0}"

if [ ! -d "$APP_PATH" ] || [ ! -x "$CLI_PATH" ] || [ ! -d "$RUNTIME_PATH" ]; then
    echo "Missing build outputs, running ./build.sh first..."
    ./build.sh
fi

STAGING_DIR="$(mktemp -d "${TMPDIR:-/tmp}/pix-pkg.XXXXXX")"
ROOT_DIR="$STAGING_DIR/root"
export COPYFILE_DISABLE=1

cleanup() {
    rm -rf "$STAGING_DIR"
}

trap cleanup EXIT

mkdir -p "$ROOT_DIR/Applications"
mkdir -p "$ROOT_DIR/usr/local/bin"
mkdir -p "$ROOT_DIR/Library/Application Support/pix"

cp -R "$APP_PATH" "$ROOT_DIR/Applications/"
install -m 755 "$CLI_PATH" "$ROOT_DIR/usr/local/bin/pix"
cp -R "$RUNTIME_PATH" "$ROOT_DIR/Library/Application Support/pix/pix_cli"
if command -v xattr >/dev/null 2>&1; then
    xattr -cr "$ROOT_DIR" || true
fi
find "$ROOT_DIR" -name '._*' -delete

rm -f "$PKG_PATH"
/usr/bin/pkgbuild \
    --root "$ROOT_DIR" \
    --identifier "$IDENTIFIER" \
    --version "$VERSION" \
    --install-location "/" \
    "$PKG_PATH"

echo "PKG created: $PKG_PATH"
