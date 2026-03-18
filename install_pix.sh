#!/bin/bash
set -euo pipefail

SOURCE_BIN="dist/pix"
SOURCE_RUNTIME="dist/pix_cli"
SUPPORT_DIR="$HOME/Library/Application Support/pix"

if [ ! -x "$SOURCE_BIN" ]; then
    echo "Missing standalone binary at $SOURCE_BIN, building first..."
    ./build.sh
fi

if [ ! -d "$SOURCE_RUNTIME" ]; then
    echo "Missing CLI runtime at $SOURCE_RUNTIME, building first..."
    ./build.sh
fi

if [ "${1:-}" != "" ]; then
    TARGET_DIR="$1"
elif [ -d "/opt/homebrew/bin" ] && [ -w "/opt/homebrew/bin" ]; then
    TARGET_DIR="/opt/homebrew/bin"
elif [ -d "/usr/local/bin" ] && [ -w "/usr/local/bin" ]; then
    TARGET_DIR="/usr/local/bin"
else
    TARGET_DIR="$HOME/.local/bin"
    mkdir -p "$TARGET_DIR"
fi

mkdir -p "$SUPPORT_DIR"
rm -rf "$SUPPORT_DIR/pix_cli"
cp -R "$SOURCE_RUNTIME" "$SUPPORT_DIR/pix_cli"
install -m 755 "$SOURCE_BIN" "$TARGET_DIR/pix"

echo "Installed pix runtime to $SUPPORT_DIR/pix_cli"
echo "Installed pix to $TARGET_DIR/pix"
echo "Run it from anywhere with: pix"
