#!/bin/bash
set -euo pipefail

needs_sudo=false

SYSTEM_PATHS=(
    "/Applications/pix.app"
    "/usr/local/bin/pix"
    "/Library/Application Support/pix"
)

USER_PATHS=(
    "$HOME/Applications/pix.app"
    "$HOME/Library/Application Support/pix"
    "$HOME/.local/bin/pix"
    "/opt/homebrew/bin/pix"
)

remove_path() {
    local target="$1"
    if [ -e "$target" ] || [ -L "$target" ]; then
        if rm -rf "$target" 2>/dev/null; then
            echo "Removed $target"
        else
            echo "Skipped $target (try again with sudo if this path should be removed)"
            needs_sudo=true
        fi
    fi
}

forget_receipt() {
    if command -v pkgutil >/dev/null 2>&1; then
        pkgutil --forget com.kilo.pix >/dev/null 2>&1 || true
    fi
}

for target in "${SYSTEM_PATHS[@]}"; do
    remove_path "$target"
done

for target in "${USER_PATHS[@]}"; do
    remove_path "$target"
done

forget_receipt
if [ "$needs_sudo" = true ]; then
    echo "pix uninstall partially completed. Re-run with sudo to remove protected system paths."
else
    echo "pix uninstall completed."
fi
