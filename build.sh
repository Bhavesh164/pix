#!/bin/bash
pip install -r requirements.txt
pyinstaller --onefile --windowed --name pix main.py
echo "Build complete: dist/pix"
