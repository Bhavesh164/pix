#!/bin/bash
rm -rf assets/logo.iconset
mkdir -p assets/logo.iconset
sips -z 16 16     -s format png assets/logo.jpg --out assets/logo.iconset/icon_16x16.png
sips -z 32 32     -s format png assets/logo.jpg --out assets/logo.iconset/icon_16x16@2x.png
sips -z 32 32     -s format png assets/logo.jpg --out assets/logo.iconset/icon_32x32.png
sips -z 64 64     -s format png assets/logo.jpg --out assets/logo.iconset/icon_32x32@2x.png
sips -z 128 128   -s format png assets/logo.jpg --out assets/logo.iconset/icon_128x128.png
sips -z 256 256   -s format png assets/logo.jpg --out assets/logo.iconset/icon_128x128@2x.png
sips -z 256 256   -s format png assets/logo.jpg --out assets/logo.iconset/icon_256x256.png
sips -z 512 512   -s format png assets/logo.jpg --out assets/logo.iconset/icon_256x256@2x.png
sips -z 512 512   -s format png assets/logo.jpg --out assets/logo.iconset/icon_512x512.png
sips -z 1024 1024 -s format png assets/logo.jpg --out assets/logo.iconset/icon_512x512@2x.png

iconutil -c icns assets/logo.iconset -o assets/logo.icns
rm -R assets/logo.iconset
