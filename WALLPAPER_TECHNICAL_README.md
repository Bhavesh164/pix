# Wallpaper Technical README

This document explains the macOS wallpaper implementation used by `pix`, especially the Tahoe-focused changes.

## Goal

Set the current image as the desktop wallpaper from inside the app without depending on Finder automation, runtime Swift compilation, or crash-prone AppKit bridging from Python.

## Why The Old Approach Broke On Tahoe

The previous macOS path chained together three brittle mechanisms:

- `osascript` with `System Events`
- `osascript` with `Finder`
- a throwaway Swift script that called `NSWorkspace.setDesktopImageURL`

On macOS Tahoe, that combination became unreliable for three different reasons:

- AppleEvent automation can fail unless the app is granted the right automation permissions.
- Runtime Swift execution can fail when the installed compiler and SDK are slightly out of sync.
- Headless helper processes are more likely to miss the same GUI context as the running app.

The supported AppKit wallpaper API itself still exists in the Tahoe SDK. The problem was how `pix` reached it safely from Python.

## Current Design

`pix` now updates Tahoe's wallpaper store directly:

1. `core/wallpaper.py` routes macOS requests into `core/macos_wallpaper.py`.
2. `core/macos_wallpaper.py` loads `~/Library/Application Support/com.apple.wallpaper/Store/Index.plist`.
3. It rewrites every `Desktop` entry to point at the selected file URL using the same `imageFile` configuration shape Tahoe already stores.
4. It preserves placement/shuffle option payloads already present in the store.
5. It writes the plist back atomically so the wallpaper agent never sees a partial file.
6. It restarts the current user's `com.apple.wallpaper.agent`, which forces Tahoe to apply the new wallpaper immediately.
7. Only if the Tahoe store path fails does `pix` fall back to AppleScript.

This keeps `pix` aligned with Tahoe's actual wallpaper runtime state while avoiding the AppKit registration abort shown in the Python crash report.

## Files

- `core/wallpaper.py`
- `core/macos_wallpaper.py`
- `views/thumbnail_view.py`
- `views/image_view.py`
- `overlays/help_overlay.py`

## Shortcut Behavior

Wallpaper stays on `b` in both grid view and image view.

## Testing Strategy

The repo includes unit coverage for:

- macOS backend selection and fallback behavior
- Tahoe wallpaper store rewriting and atomic persistence
- help-overlay shortcut text

Live wallpaper verification still needs access to the user's real wallpaper store, so testing from a sandboxed coding session may require approval to write outside the workspace.
