# pix — Technical Architecture

> A deep-dive into how `pix` works internally: module design, data flow, performance strategy, and cross-platform wallpaper support.

---

## Table of Contents

1. [High-Level Architecture](#high-level-architecture)
2. [Module Map](#module-map)
3. [Entry Point & Startup Flow](#entry-point--startup-flow)
4. [Core Layer](#core-layer)
   - [ImageLoader](#imageloader)
   - [ThumbCache](#thumbcache)
   - [ThumbWorker](#thumbworker)
   - [Wallpaper](#wallpaper)
   - [Fuzzy Search](#fuzzy-search)
5. [Application Layer](#application-layer)
   - [PixApp](#pixapp)
   - [View Switching Strategy](#view-switching-strategy)
6. [Views](#views)
   - [ThumbnailView](#thumbnailview)
   - [ImageView](#imageview)
7. [Overlays](#overlays)
8. [Thumbnail Loading Pipeline](#thumbnail-loading-pipeline)
9. [Cross-Platform Wallpaper](#cross-platform-wallpaper)
10. [Keybinding System](#keybinding-system)
11. [Performance Design Decisions](#performance-design-decisions)
12. [Build System](#build-system)

---

## High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                            main.py                                  │
│  CLI arg parsing → path resolution → ImageLoader → PixApp.run()     │
└────────────────────────────────┬────────────────────────────────────┘
                                 │
                                 ▼
┌─────────────────────────────────────────────────────────────────────┐
│                           app.py  (PixApp)                          │
│                                                                     │
│   ┌──────────────┐        ┌──────────────────────────────────────┐  │
│   │ ThumbnailView│◄──────►│          Tk Root Window              │  │
│   └──────────────┘        │  (fullscreen, black bg, no chrome)   │  │
│   ┌──────────────┐        └──────────────────────────────────────┘  │
│   │  ImageView   │                                                   │
│   └──────────────┘                                                   │
│                                                                      │
│  Shared services: ThumbCache, wallpaper.set_wallpaper, _show_toast  │
└──────────────────────────────────────────────────────────────────────┘
                     │                      │
          ┌──────────┘                      └──────────┐
          ▼                                            ▼
┌──────────────────┐                    ┌──────────────────────────┐
│    core/         │                    │    overlays/             │
│  ImageLoader     │                    │  HelpOverlay             │
│  ThumbCache      │                    │  SearchOverlay           │
│  ThumbWorker ────┼──ThreadPoolExec    │  ConfirmOverlay          │
│  wallpaper       │                    └──────────────────────────┘
│  fuzzy           │
└──────────────────┘
```

---

## Module Map

```
pix/
├── main.py                  # CLI entry point, argparse
├── app.py                   # PixApp: root window, view switching, toast
│
├── core/
│   ├── image_loader.py      # Filesystem scan → sorted list of Paths
│   ├── thumb_cache.py       # Disk cache for WebP thumbnails (~/.cache/pix)
│   ├── thumb_worker.py      # ThreadPoolExecutor thumbnail generator
│   ├── wallpaper.py         # Cross-platform wallpaper setter
│   └── fuzzy.py             # Fuzzy search helper (thefuzz)
│
├── views/
│   ├── thumbnail_view.py    # Grid view: canvas-based thumbnail grid
│   └── image_view.py        # Full image view: pan, zoom, navigate
│
├── overlays/
│   ├── help_overlay.py      # Keybinding cheat-sheet overlay
│   ├── search_overlay.py    # Fuzzy search bar overlay
│   └── confirm_overlay.py   # Delete confirmation overlay
│
├── assets/                  # Screenshots, app icon files
├── build.sh                 # PyInstaller build script
└── pix.spec                 # PyInstaller spec file
```

---

## Entry Point & Startup Flow

```
main.py
  │
  ├─ argparse → parse path, -r (recursive), --clear-cache
  │
  ├─ ImageLoader(target_path, recursive).load_images()
  │     └─ returns sorted list[Path]
  │
  ├─ PixApp(target_path, recursive, clear_cache, images)
  │     ├─ ThumbCache(cache_base)     ← creates ~/.cache/pix/
  │     ├─ tk.Tk() fullscreen window
  │     ├─ if single file  → switch_to_image_view()
  │     └─ if directory    → switch_to_thumbnail_view()
  │
  └─ app.run()  →  root.mainloop()
```

**Single-image mode**: If the user passes a single image file (e.g. `pix photo.jpg`), `PixApp`
sets `is_single_image = True` and opens directly to `ImageView`, bypassing the grid. The `q` key
exits the app rather than going back to the grid.

---

## Core Layer

### ImageLoader

```
core/image_loader.py
```

Scans the filesystem and returns a sorted `list[Path]`.

| Mode        | Method                    | Note                              |
|-------------|---------------------------|-----------------------------------|
| Flat        | `target_path.glob('*')`   | Top-level files only              |
| Recursive   | `target_path.rglob('*')`  | All subdirectories                |
| Single file | Early return `[target]`   | Passes extension check first      |

Supported extensions: `.jpg`, `.jpeg`, `.png`, `.webp`, `.bmp`, `.gif`

---

### ThumbCache

```
core/thumb_cache.py
```

Stores generated thumbnails as WebP files under `~/.cache/pix/`.

**Cache key strategy**:
```
sha1( resolved_absolute_path + "_" + mtime ) → <hash>.webp
```

Using `mtime` in the key means the cache is auto-invalidated whenever the file changes on disk —
no manual expiry needed.

```
get_cache_path(filepath)
  └─ mtime  = filepath.stat().st_mtime
  └─ key    = sha1(f"{filepath.resolve()}_{mtime}")
  └─ return  ~/.cache/pix/<key>.webp
```

Cache operations:

| Method        | Behavior                                   |
|---------------|--------------------------------------------|
| `get_cache_path` | Derive deterministic cache key for path |
| `wipe_all()`  | `shutil.rmtree` the entire cache dir       |
| `clear()`     | Not yet implemented (stub)                 |

---

### ThumbWorker

```
core/thumb_worker.py
```

Generates thumbnails concurrently using a `ThreadPoolExecutor`.

```
ThumbWorker(cache_manager, num_workers=4, thumb_size=(160,160))

request_thumbnail(image_path, callback)
  └─ pool.submit(worker)
        └─ generate_thumbnail(image_path)
             ├─ cache hit?  → Image.open(cache_path).copy()  [instant]
             └─ cache miss? → open → exif_transpose
                               → draft('RGB', size)          [subsample decode]
                               → thumbnail(size)             [fast resize]
                               → convert('RGB')
                               → save as WebP
                               → return copy
        └─ callback(image_path, thumb)
              └─ widget.after(0, lambda: canvas.itemconfig(...))  [thread-safe UI update]
```

**EXIF subsample decode** (`img.draft('RGB', thumb_size)`): For JPEG images, Pillow can request the
JPEG decoder to decode at 1/2, 1/4, or 1/8 resolution. This is dramatically faster for large
source files since far fewer pixels are decoded from disk.

---

### Wallpaper

```
core/wallpaper.py
```

Cross-platform wallpaper setter. See the [Cross-Platform Wallpaper](#cross-platform-wallpaper)
section for the full decision tree.

Public API:
```python
set_wallpaper(image_path: Path) -> tuple[bool, str]
# Returns (success, human-readable message)
```

---

### Fuzzy Search

```
core/fuzzy.py
```

Thin wrapper around `thefuzz` (RapidFuzz-compatible). Takes a query string and a list of
`Path` objects, returns the top matches sorted by similarity score.

---

## Application Layer

### PixApp

```
app.py
```

`PixApp` owns the Tk root window and acts as the **mediator** between views and core services.
Views never talk to each other directly; they only call methods on `self.app`.

```
PixApp
 ├─ root          tk.Tk()              # fullscreen window
 ├─ container     tk.Frame(root)       # fill=BOTH, expand=True
 ├─ active_view   View | None          # currently visible view
 ├─ thumb_cache   ThumbCache
 ├─ loader        ImageLoader
 ├─ images        list[Path]
 │
 ├─ switch_to_thumbnail_view()
 ├─ switch_to_image_view(path, index)
 ├─ set_wallpaper(image_path)          # → core.wallpaper + toast
 ├─ _show_toast(message, ms)           # bottom-right timed label
 └─ quit()
```

### View Switching Strategy

A key performance optimization is **reusing the `ThumbnailView` instance** instead of
destroying and recreating it each time the user navigates between the grid and an image.

```
switch_to_thumbnail_view():
  active_view.pack_forget()           # hide current view — O(1)
  if thumb_view_instance not created:
      ThumbnailView(...)              # create ONCE, first time only
  active_view = thumb_view_instance
  active_view.pack(...)               # show — O(1)
  active_view.focus_set()

switch_to_image_view(path, index):
  active_view.pack_forget()           # hide thumbnail grid
  if image_view_instance exists:
      image_view_instance.destroy()   # ImageView is recreated each time
  ImageView(...)                      # create new one
  active_view.pack(...)
  active_view.focus_set()
```

The `ThumbnailView` is expensive to build (canvas items, thumb requests), so it's preserved.
The `ImageView` is cheap (just one image load) and is recreated for each image.

---

## Views

### ThumbnailView

```
views/thumbnail_view.py
```

Renders all images as a scrollable grid using a **single `tk.Canvas`** (not individual `Frame`
widgets). This is a significant performance choice.

```
ThumbnailView
 ├─ canvas          tk.Canvas                # single canvas for entire grid
 ├─ items[]         list of {rect_id, img_id, text_id, path}
 ├─ selected_index  int                      # focused cell (vim-style cursor)
 ├─ multi_selected  set[int]                 # Space-selected images
 ├─ cols            int                      # recalculated on resize
 └─ tk_images{}     dict[Path → PhotoImage]  # keep refs to prevent GC
```

**Grid layout** (all canvas coords, computed on every resize):

```
item_w = thumb_size + 20   (180px default)
item_h = thumb_size + 34   (194px default)
margin = (canvas_width - cols * item_w) // 2   # center the grid

for each item i:
    col = i % cols
    row = i // cols
    x   = margin + col * item_w + item_w // 2
    y   = row * item_h + item_h // 2

    rect  → (x-w/2, y-h/2, x+w/2, y+h/2)
    image → (x, y-8)            # center image, slightly above
    text  → (x, y + item_h/2 - 6)  # filename beneath image
```

**Selection state colors**:

| State               | Outline Color |
|---------------------|---------------|
| None                | `grey`        |
| Focused only        | `white`       |
| Selected only       | `yellow`      |
| Focused + Selected  | `cyan`        |

**Scroll management**: The canvas `scrollregion` is updated on every `<Configure>` event
(window resize). Keyboard navigation auto-scrolls to keep the selected cell in view.

**`gg` navigation**: A 500ms timer tracks whether two `g` presses occurred consecutively.

---

### ImageView

```
views/image_view.py
```

Full-image viewer with zoom and pan.

```
ImageView
 ├─ canvas      tk.Canvas
 ├─ status      tk.Label         # bottom bar: filename, index, zoom%, dimensions
 ├─ image       PIL.Image        # source image (full resolution)
 ├─ tk_image    ImageTk.PhotoImage
 ├─ zoom        float            # 1.0 = fit to window
 ├─ pan_x/y     int              # pixel offset from center
```

**Render pipeline** (called on every zoom/pan/resize):

```
_render():
  iw, ih = image.size
  cw, ch = canvas size
  ratio  = min(cw/iw, ch/ih)           # fit-to-window scale
  new_size = (iw * ratio * zoom, ih * ratio * zoom)
  render_img = image.resize(new_size, BILINEAR)
  tk_image   = ImageTk.PhotoImage(render_img)
  canvas.create_image(cw//2 + pan_x, ch//2 + pan_y, anchor=CENTER)
```

**Pan clamping**: The pan is bounded so the image never scrolls completely out of view:
```
max_pan_x = max(0, (rendered_width  - canvas_width)  // 2)
max_pan_y = max(0, (rendered_height - canvas_height) // 2)
pan_x = clamp(pan_x, -max_pan_x, max_pan_x)
```

---

## Overlays

All overlays are `tk.Frame` subclasses **placed as children of the active view**, not the root
window. `ov.place(relx=0.5, rely=0.5, anchor=CENTER)` centers them over the canvas.

```
Overlay lifecycle:
  _show_<overlay>()
    └─ overlay = FooOverlay(self)         # self = current view frame
    └─ overlay.place(relx=0.5, rely=0.5)
    └─ overlay.focus_set()
         Esc / q → overlay.destroy()
                    parent.focus_set()   # restore keyboard focus to view
```

| Overlay          | Trigger | Description                           |
|------------------|---------|---------------------------------------|
| `HelpOverlay`    | `?`     | ASCII keybinding cheat-sheet          |
| `SearchOverlay`  | `/`     | Real-time fuzzy search by filename    |
| `ConfirmOverlay` | `d`     | Asks before permanent file deletion   |

---

## Thumbnail Loading Pipeline

This is the most performance-sensitive part of the application. The goal is to display
thumbnails in **milliseconds**, even for 1000+ image directories.

```
Directory opened
      │
      ▼
ImageLoader.load_images()          → sorted list[Path]   [fast: OS glob]
      │
      ▼
ThumbnailView._build_grid()
      │
      ├─ For each path:
      │    canvas.create_rectangle(...)  → rect_id     ╮
      │    canvas.create_text(...)       → text_id     │  All O(1) canvas ops
      │    canvas.create_image(...)      → img_id      ╯  Grid visible instantly
      │    ThumbWorker.request_thumbnail(path, callback)   → submitted to thread pool
      │
      ▼
[UI is immediately responsive — grid layout shown with placeholder slots]
      │
  [Thread pool: 4 workers running concurrently]
      │
      For each image (in parallel):
        ThumbCache.get_cache_path(path)
          │
          ├─ Cache HIT  → Image.open(webp).copy()           [~1ms]
          └─ Cache MISS → decode (draft subsample) → resize → save webp  [~50–200ms]
                │
                ▼
        callback(path, thumb)
          └─ widget.after(0, lambda: canvas.itemconfig(img_id, image=tk_img))
                              ↑
                         Thread-safe: deferred to main event loop
```

**Why canvas items instead of widget frames?**
Creating 1000 `tk.Frame` + `tk.Label` widgets is ~5–10× slower than creating 3 canvas items
(rect, image, text) per thumbnail. Canvas items are lightweight drawing primitives.

---

## Cross-Platform Wallpaper

```
core/wallpaper.py
```

The `set_wallpaper()` function detects the OS at runtime using `sys.platform` and dispatches
to the appropriate backend.

```
set_wallpaper(image_path)
      │
      ├─ sys.platform == "darwin"       → _set_wallpaper_macos()
      │                                      osascript AppleScript
      │                                      ("tell every desktop → set picture")
      │
      ├─ sys.platform == "win32"        → _set_wallpaper_windows()
      │                                      ctypes.windll.user32
      │                                      SystemParametersInfoW(SPI_SETDESKWALLPAPER)
      │
      └─ sys.platform.startswith("linux") → _set_wallpaper_linux()
               │
               ├─ XDG_CURRENT_DESKTOP contains "gnome" / "unity" / "pop" / ...
               │        → gsettings set org.gnome.desktop.background picture-uri
               │
               ├─ XDG_CURRENT_DESKTOP contains "kde" / "plasma"
               │        → qdbus org.kde.plasmashell evaluateScript (JS)
               │
               ├─ XDG_CURRENT_DESKTOP contains "xfce"
               │        → xfconf-query -c xfce4-desktop -p .../last-image -s <path>
               │
               ├─ WAYLAND_DISPLAY set (Sway / Hyprland / generic Wayland)
               │        → swaybg -i <path> -m fill (daemonized)
               │
               └─ fallback (X11)
                        → feh --bg-fill <path>
```

All backends return `(bool, str)` — success flag and a human-readable message. The
`PixApp._show_toast()` method displays this message as a 2.5-second overlay in the
bottom-right corner of the screen.

### Platform Decision Matrix

| Platform        | Tool Used                    | Requirements                          |
|-----------------|------------------------------|---------------------------------------|
| macOS           | `osascript` (AppleScript)    | Built into macOS                      |
| Windows         | `ctypes` (Win32 API)         | Built into Python on Windows          |
| GNOME / Cinnamon| `gsettings`                  | Installed by default                  |
| KDE Plasma      | `qdbus` + PlasmaShell        | `qdbus` (part of kde-cli-tools)       |
| XFCE            | `xfconf-query`               | Part of XFCE settings manager         |
| Sway / Hyprland | `swaybg`                     | Install: `apt install swaybg`         |
| X11 fallback    | `feh`                        | Install: `apt install feh`            |

---

## Keybinding System

Each view calls `_bind_keys()` on itself. Bindings are attached to the **frame widget**, not
the root window. This means focus must be set explicitly via `focus_set()` after view switches.

Bindings are `tkinter` event strings:
- `"<Return>"` — Enter key
- `"<Control-d>"` — Ctrl+D combo
- `"l"` — literal lowercase `l`
- `"L"` — shift+L (capital)

### Wallpaper Shortcut

| View           | Key | Behavior                               |
|----------------|-----|----------------------------------------|
| Grid View      | `w` | Set focused (highlighted) image as wallpaper |
| Image View     | `W` | Set currently-displayed image as wallpaper |

> **Why different keys?** In Image View, lowercase `w` is already bound to "pan up"
> (part of `w/a/s/d` pan cluster). Capital `W` is free and semantically distinct.

---

## Performance Design Decisions

| Decision                          | Why                                                                 |
|-----------------------------------|---------------------------------------------------------------------|
| Canvas items instead of Frames    | 10× less widget overhead for large grids                           |
| ThreadPoolExecutor (4 workers)    | Parallel thumbnail decode without GIL issues (Pillow releases GIL) |
| EXIF subsampled JPEG decode       | `draft()` decodes at ¼ or ⅛ resolution; dramatically faster       |
| WebP thumbnail cache              | WebP ~30% smaller than JPEG at same quality; fast decode           |
| `pack_forget()` not `destroy()`   | Reusing ThumbnailView avoids rebuilding 1000 canvas items          |
| `widget.after(0, callback)`       | Safe cross-thread UI update via main loop scheduling               |
| `ImageOps.exif_transpose()`       | Correct rotation without baking it into source image               |
| `Image.Resampling.BILINEAR`       | Faster than LANCZOS, better quality than NEAREST for zoom          |

---

## Build System

```
build.sh  →  PyInstaller  →  dist/pix  (single-file standalone binary)
```

```bash
pyinstaller \
  --onefile \           # bundle everything into one file
  --windowed \          # no terminal window on macOS/Windows
  --name pix \
  --icon assets/pix.icns \
  main.py
```

The `pix.spec` file captures the same configuration and can be used directly:
```bash
pyinstaller pix.spec
```

**Platform-specific requirements for build**:

| OS      | Requirement                          |
|---------|--------------------------------------|
| macOS   | `brew install python-tk`             |
| Linux   | `sudo apt install python3-tk`        |
| Windows | Ensure "tcl/tk and IDLE" was checked during Python install |
