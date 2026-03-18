pix — Minimal Vim-style Image Viewer
Inspired by mpv — no titlebar, no buttons, pure keyboard.

Visual Philosophy

Zero chrome — no titlebar, no toolbar, no buttons, no scrollbars
Status bar only — one thin line at bottom (like vim's statusline) showing: mode | filename | index/total | zoom%
Overlays — search, help, confirmations appear as floating overlays on the canvas, not separate windows
? opens a keybinding cheatsheet overlay (dismisses with Esc or ?)
Window is borderless/frameless — overrideredirect(True) in tkinter


Tech Stack
PurposeLibraryGUI & canvastkinter (built-in)Image decode & resizePillowFuzzy searchthefuzz + python-LevenshteinSingle binaryPyInstaller --onefile
No Qt, no Electron, no extra bloat.

Thumbnail Loading Strategy (Fast & Optimized)
This is the most critical optimization. Three-layer approach:
Layer 1 — Embedded EXIF thumbnail (instant)
Most JPEGs have a tiny pre-baked thumbnail (~160px) inside EXIF metadata. Pillow can extract this in microseconds — no need to decode the full image at all.
Layer 2 — Subsampled decode (fast fallback)
For PNGs and JPEGs without EXIF thumbs, use Pillow's draft() mode which tells the JPEG decoder to only decode 1/8th of the image data. Much faster than full decode.
Layer 3 — Disk cache (persistent)
Generated thumbnails are cached to ~/.cache/pix/ as tiny WebP files keyed by filepath + mtime. On second launch, grid loads instantly from cache — no decode at all.
Threading model:

Main thread renders the grid immediately with placeholders (grey boxes)
Background thread pool (4 workers) fills thumbnails as they're ready
Visible viewport prioritized — thumbnails outside scroll area load last


Launch Modes
bashpix ./photos          # flat load
pix -r ./photos       # recursive, all subdirs
pix ./photo.jpg       # single image mode — no grid, no back

Screen 1 — Thumbnail Grid
Appearance: Pure black background, thumbnails in a responsive grid, thin highlight border on selected item, filename in small grey text below. Nothing else.
Keyboard Map:
KeyActionh j k lNavigate grid (vim directions)EnterOpen image in full viewSpaceToggle select imageVSelect alldDelete selected (confirm overlay)Ctrl+d / Ctrl+uScroll grid down / upg gJump to first imageGJump to last image5 gJump to Nth image (vim count prefix)/Open fuzzy search bar?Show keybinding help overlayqQuit

Screen 2 — Full Image View (from grid)
Appearance: Pure black canvas, image centered, status bar at bottom. Nothing else.
Keyboard Map:
KeyActionqBack to thumbnail gridh / lPrevious / Next image+ / -Zoom in / out (10% steps)0Reset zoom — fit to windowWFit to widthHFit to heightMouse scrollZoom in/out at cursor positionMouse dragPan when zoomed inw a s dPan (up/left/down/right) when zoomedvEnter region-select modeEnter (in region)Zoom into selected regionEscCancel region select/Fuzzy search (jump to any image)dDelete current image (confirm overlay)?Show keybinding help overlay
Region Select Mode:

v activates it — a rubberband rectangle appears
h j k l expand/contract the selection box
Mouse drag also draws region
Enter zooms into that region
Status bar shows REGION mode indicator


Screen 2b — Direct Single Image Mode
bashpix cat.jpg
```

- Identical to Screen 2 visually and keyboard-wise
- **No grid exists** — `q` quits the app entirely
- `/` search opens image directly (replaces current)

---

### Universal Overlays (appear on black canvas)

**`/` Fuzzy Search:**
```
╔─────────────────────────────╗
│ > cat_photo_              │  ← input line
│   cat_photo_001.jpg         │  ← results list
│   cat_photo_beach.jpg       │
│   scatter_plot.png          │
╚─────────────────────────────╝
```
- `j/k` navigate results
- `Enter` opens selected
- `Esc` dismisses
- Updates live as you type

**`?` Help Overlay:**
```
╔─── keybindings ─────────────╗
│  GRID VIEW                  │
│  h j k l   navigate         │
│  Enter     open image       │
│  Space     select           │
│  d         delete selected  │
│  ...                        │
│  IMAGE VIEW                 │
│  q         back to grid     │
│  + -       zoom in/out      │
│  ...                        │
│            Esc to close     │
╚─────────────────────────────╝
```

**Confirm Delete:**
```
  delete 3 images? [y/N]
```
Inline, no popup window.

---

### Status Bar (always visible, bottom)
```
GRID  |  ~/photos  |  42 images  |  3 selected
VIEW  |  cat_001.jpg  |  12/42  |  zoom: 87%  |  1920x1080
REGION  |  cat_001.jpg  |  selecting region...
SEARCH  |  /cat_ph█
```

---

### Project Structure
```
pix/
├── main.py                  # arg parsing, launch mode routing
├── app.py                   # root window, frameless setup, mode switching
├── views/
│   ├── thumbnail_view.py    # grid, lazy loading, selection
│   └── image_view.py        # full view, zoom, pan, region
├── overlays/
│   ├── search_overlay.py    # fuzzy search UI
│   ├── help_overlay.py      # ? keybinding sheet
│   └── confirm_overlay.py   # delete confirmation
├── core/
│   ├── image_loader.py      # flat/recursive scan, EXIF thumb extraction
│   ├── thumb_cache.py       # ~/.cache/pix/ disk cache logic
│   ├── thumb_worker.py      # background thread pool for thumb generation
│   └── fuzzy.py             # thefuzz wrapper
├── build.sh                 # PyInstaller build command
└── requirements.txt

Build
bashpip install pillow thefuzz python-Levenshtein pyinstaller
pyinstaller --onefile --windowed --name pix main.py
# → dist/pix  (single binary, no installer needed)

Key Design Decisions Summary
DecisionReasonoverrideredirect(True)Removes OS titlebar completely like mpvEXIF thumbnail first~0ms for most JPEGsdraft() subsampling8x faster than full JPEG decodeWebP disk cacheTiny files, fast load, persistent across launchesThread pool (4 workers)Parallel thumb generation, viewport-first priorityVim count prefix (5g)Power-user navigation without arrow keysAll UI as canvas overlaysTrue mpv-style — no widgets, no native dialogs

Cache Management
CLI flags:
bashpix --clear-cache          # purge entire cache, then exit
pix --clear-cache ./photos # purge cache only for this folder, then exit
pix -r --clear-cache .     # purge cache for recursive scan of current dir, then exit
```

**From inside the app (thumbnail grid):**

| Key | Action |
|---|---|
| `C` | Purge cache for currently loaded folder, regenerate thumbs live |

When `C` is pressed:
- Confirm overlay appears: `clear cache for ~/photos? [y/N]`
- On `y` — deletes cached WebP files for this session's images, then reloads grid with placeholders and regenerates thumbs fresh in background
- Status bar shows `rebuilding cache...` during regeneration

---

### Cache Structure (for reference)
```
~/.cache/pix/
├── abc123def.webp     ← keyed by sha1(filepath + mtime)
├── ff291baac.webp
└── ...
Purging by folder = delete only keys whose source path starts with that folder prefix. Purging all = wipe entire ~/.cache/pix/ directory.

This keeps cache management both scriptable (CI/cron friendly) and keyboard-accessible inside the app.
