#!/bin/bash
set -euo pipefail

if [ ! -d "venv" ]; then
    python3 -m venv venv
fi
source venv/bin/activate

pip install -r requirements.txt
pyinstaller -y pix.spec
pyinstaller -y pix_cli.spec

BUILD_CLI_PATH="$(cd dist && pwd -P)/pix_cli/pix_cli"
BUILD_APP_PATH="$(cd dist && pwd -P)/pix.app/Contents/MacOS/pix"

rm -rf dist/pix
{
    echo '#!/bin/bash'
    echo 'set -euo pipefail'
    echo ''
    echo 'resolve_script_dir() {'
    echo '    local src="${BASH_SOURCE[0]}"'
    echo '    while [ -L "$src" ]; do'
    echo '        local dir'
    echo '        dir="$(cd -P "$(dirname "$src")" && pwd)"'
    echo '        src="$(readlink "$src")"'
    echo '        if [[ "$src" != /* ]]; then'
    echo '            src="$dir/$src"'
    echo '        fi'
    echo '    done'
    echo '    cd -P "$(dirname "$src")" && pwd'
    echo '}'
    echo ''
    echo 'SCRIPT_DIR="$(resolve_script_dir)"'
    echo 'CANDIDATES=('
    echo '    "$SCRIPT_DIR/pix_cli/pix_cli"'
    echo '    "$HOME/Library/Application Support/pix/pix_cli/pix_cli"'
    echo '    "/Library/Application Support/pix/pix_cli/pix_cli"'
    printf '    "%s"\n' "$BUILD_CLI_PATH"
    echo '    "$SCRIPT_DIR/pix.app/Contents/MacOS/pix"'
    echo '    "/Applications/pix.app/Contents/MacOS/pix"'
    echo '    "$HOME/Applications/pix.app/Contents/MacOS/pix"'
    printf '    "%s"\n' "$BUILD_APP_PATH"
    echo ')'
    echo ''
    echo 'for candidate in "${CANDIDATES[@]}"; do'
    echo '    if [ -x "$candidate" ]; then'
    echo '        exec "$candidate" "$@"'
    echo '    fi'
    echo 'done'
    echo ''
    echo 'echo "pix launcher could not find pix.app. Checked:" >&2'
    echo 'for candidate in "${CANDIDATES[@]}"; do'
    echo '    echo "  $candidate" >&2'
    echo 'done'
    echo 'echo "Install pix.app in /Applications, ~/Applications, or keep it alongside the pix launcher." >&2'
    echo 'exit 1'
} > dist/pix
chmod +x dist/pix

echo "Build complete: dist/pix (fast launcher) & dist/pix.app"
