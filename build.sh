#!/bin/bash
if [ ! -d "venv" ]; then
    python3 -m venv venv
fi
source venv/bin/activate

pip install -r requirements.txt
pyinstaller -y pix.spec

# Create a fast CLI wrapper since --onefile is extremely slow on macOS
rm -rf dist/pix
echo '#!/bin/bash' > dist/pix_wrapper
echo 'DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"' >> dist/pix_wrapper
echo 'exec "$DIR/pix.app/Contents/MacOS/pix" "$@"' >> dist/pix_wrapper
chmod +x dist/pix_wrapper
mv dist/pix_wrapper dist/pix

echo "Build complete: dist/pix (Wrapper for instant startup) & dist/pix.app"
