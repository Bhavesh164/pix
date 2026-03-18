"""
Cross-platform wallpaper setter for pix.

Supported platforms:
  - macOS:   AppleScript via osascript
  - Windows: ctypes win32 SystemParametersInfoW
  - Linux:   auto-detects desktop environment (GNOME, KDE, XFCE, feh fallback)
"""

import sys
import subprocess
from pathlib import Path


def set_wallpaper(image_path: Path) -> tuple[bool, str]:
    """
    Set the desktop wallpaper to `image_path`.

    Returns (success: bool, message: str).
    """
    image_path = Path(image_path).resolve()

    if not image_path.exists():
        return False, f"File not found: {image_path}"

    platform = sys.platform

    if platform == "darwin":
        return _set_wallpaper_macos(image_path)
    elif platform == "win32":
        return _set_wallpaper_windows(image_path)
    elif platform.startswith("linux"):
        return _set_wallpaper_linux(image_path)
    else:
        return False, f"Unsupported platform: {platform}"


# ─── macOS ────────────────────────────────────────────────────────────────────

def _set_wallpaper_macos(image_path: Path) -> tuple[bool, str]:
    """
    Set wallpaper on macOS using an aggressive combination of methods.
    macOS Ventura/Sonoma/Sequoia/Tahoe have various sandbox and Space restrictions.
    We try AppleScript (Finder), AppleScript (System Events), and Swift (NSWorkspace).
    """
    import shutil
    import tempfile
    import os

    success = False
    errors = []

    # Strip PyInstaller's custom library paths. If we don't, osascript and swift
    # will link against python's bundled libraries and silently fail or crash.
    clean_env = os.environ.copy()
    clean_env.pop("DYLD_LIBRARY_PATH", None)
    clean_env.pop("LD_LIBRARY_PATH", None)
    clean_env.pop("TCL_LIBRARY", None)
    clean_env.pop("TK_LIBRARY", None)
    clean_env["PATH"] = "/usr/bin:/bin:/usr/sbin:/sbin:/usr/local/bin"

    # Method 1: AppleScript (System Events) - Best for all spaces
    applescript_sys = f'''
        tell application "System Events"
            tell every desktop
                set picture to "{image_path}"
            end tell
        end tell
    '''
    res_sys = subprocess.run(["/usr/bin/osascript", "-e", applescript_sys], capture_output=True, text=True, timeout=10, env=clean_env)
    if res_sys.returncode == 0:
        success = True
    else:
        errors.append(f"SysEvents: {res_sys.stderr.strip()}")

    # Method 2: AppleScript (Finder) - Fallback
    applescript_finder = f'''
        tell application "Finder"
            set desktop picture to POSIX file "{image_path}"
        end tell
    '''
    res_fin = subprocess.run(["/usr/bin/osascript", "-e", applescript_finder], capture_output=True, text=True, timeout=10, env=clean_env)
    if res_fin.returncode == 0:
        success = True
    else:
        errors.append(f"Finder: {res_fin.stderr.strip()}")

    # Method 3: Swift NSWorkspace - Fallback for newer macOS if AppleScript blocked
    swift_bin = "/usr/bin/swift"
    if not os.path.isfile(swift_bin):
        swift_bin = shutil.which("swift") or "swift"

    safe_path = str(image_path).replace("\\", "\\\\").replace('"', '\\"')
    swift_script = f'''import AppKit
import Foundation
let url = URL(fileURLWithPath: "{safe_path}")
var failed = false
for screen in NSScreen.screens {{
    do {{
        try NSWorkspace.shared.setDesktopImageURL(url, for: screen, options: [:])
    }} catch {{
        failed = true
    }}
}}
exit(failed ? 1 : 0)
'''
    try:
        fd, tmp_path = tempfile.mkstemp(suffix=".swift", prefix="pix_wallpaper_")
        try:
            os.write(fd, swift_script.encode("utf-8"))
            os.close(fd)
            res_swift = subprocess.run(
                [swift_bin, tmp_path],
                capture_output=True, text=True, timeout=30,
                env=clean_env
            )
            if res_swift.returncode == 0:
                success = True
            else:
                errors.append(f"Swift: {res_swift.stderr.strip() or res_swift.stdout.strip()}")
        finally:
            try:
                os.unlink(tmp_path)
            except OSError:
                pass
    except Exception as e:
        errors.append(f"SwiftErr: {e}")

    if success:
        return True, f"Wallpaper set: {image_path.name}"
    else:
        return False, " | ".join(errors) or "Failed to set wallpaper on macOS"


# ─── Windows ──────────────────────────────────────────────────────────────────

def _set_wallpaper_windows(image_path: Path) -> tuple[bool, str]:
    """Use ctypes SystemParametersInfoW to set wallpaper."""
    try:
        import ctypes
        SPI_SETDESKWALLPAPER = 20
        SPIF_UPDATEINIFILE = 0x01
        SPIF_SENDCHANGE = 0x02
        result = ctypes.windll.user32.SystemParametersInfoW(
            SPI_SETDESKWALLPAPER, 0, str(image_path),
            SPIF_UPDATEINIFILE | SPIF_SENDCHANGE
        )
        if result:
            return True, f"Wallpaper set: {image_path.name}"
        else:
            return False, "SystemParametersInfoW returned 0 — check permissions"
    except Exception as e:
        return False, f"Windows wallpaper error: {e}"


# ─── Linux ────────────────────────────────────────────────────────────────────

def _set_wallpaper_linux(image_path: Path) -> tuple[bool, str]:
    """
    Auto-detect desktop environment and use the appropriate method.
    Priority: GNOME → KDE → XFCE → sway/hyprland (swaybg) → feh fallback.
    """
    import os

    desktop = (
        os.environ.get("XDG_CURRENT_DESKTOP", "").lower()
        or os.environ.get("DESKTOP_SESSION", "").lower()
    )

    # ── GNOME / Unity / Pop!_OS ──────────────────────────────────────────────
    if any(d in desktop for d in ("gnome", "unity", "pop", "budgie", "cinnamon")):
        return _linux_gsettings(image_path)

    # ── KDE Plasma ───────────────────────────────────────────────────────────
    if "kde" in desktop or "plasma" in desktop:
        return _linux_kde(image_path)

    # ── XFCE ─────────────────────────────────────────────────────────────────
    if "xfce" in desktop:
        return _linux_xfce(image_path)

    # ── Sway / Hyprland (Wayland compositors) ────────────────────────────────
    wayland_display = os.environ.get("WAYLAND_DISPLAY", "")
    if wayland_display:
        ok, msg = _linux_swaybg(image_path)
        if ok:
            return ok, msg
        # fall through to feh on failure

    # ── feh (generic X11 fallback) ───────────────────────────────────────────
    return _linux_feh(image_path)


def _linux_gsettings(image_path: Path) -> tuple[bool, str]:
    uri = f"file://{image_path}"
    try:
        for schema in (
            "org.gnome.desktop.background",
            "org.cinnamon.desktop.background",
        ):
            r = subprocess.run(
                ["gsettings", "set", schema, "picture-uri", uri],
                capture_output=True, text=True, timeout=10
            )
            # Also set dark variant (GNOME 42+)
            subprocess.run(
                ["gsettings", "set", schema, "picture-uri-dark", uri],
                capture_output=True, text=True, timeout=10
            )
            if r.returncode == 0:
                return True, f"Wallpaper set (gsettings): {image_path.name}"
        return False, "gsettings failed for all known schemas"
    except FileNotFoundError:
        return False, "gsettings not found"
    except subprocess.TimeoutExpired:
        return False, "gsettings timed out"


def _linux_kde(image_path: Path) -> tuple[bool, str]:
    script = f"""
        var allDesktops = desktops();
        for (var i = 0; i < allDesktops.length; i++) {{
            var d = allDesktops[i];
            d.wallpaperPlugin = "org.kde.image";
            d.currentConfigGroup = ["Wallpaper", "org.kde.image", "General"];
            d.writeConfig("Image", "file://{image_path}");
        }}
    """
    try:
        result = subprocess.run(
            ["qdbus", "org.kde.plasmashell", "/PlasmaShell",
             "org.kde.PlasmaShell.evaluateScript", script],
            capture_output=True, text=True, timeout=15
        )
        if result.returncode == 0:
            return True, f"Wallpaper set (KDE): {image_path.name}"
        return False, f"KDE qdbus error: {result.stderr.strip()}"
    except FileNotFoundError:
        return False, "qdbus not found — KDE Plasma tools missing?"
    except subprocess.TimeoutExpired:
        return False, "KDE qdbus timed out"


def _linux_xfce(image_path: Path) -> tuple[bool, str]:
    try:
        result = subprocess.run(
            ["xfconf-query", "-c", "xfce4-desktop",
             "-p", "/backdrop/screen0/monitor0/workspace0/last-image",
             "-s", str(image_path)],
            capture_output=True, text=True, timeout=10
        )
        if result.returncode == 0:
            return True, f"Wallpaper set (XFCE): {image_path.name}"
        return False, f"xfconf-query error: {result.stderr.strip()}"
    except FileNotFoundError:
        return False, "xfconf-query not found"
    except subprocess.TimeoutExpired:
        return False, "xfconf-query timed out"


def _linux_swaybg(image_path: Path) -> tuple[bool, str]:
    """Launch swaybg in daemon mode (kills any previous instance first)."""
    try:
        subprocess.run(["pkill", "swaybg"], capture_output=True)
        subprocess.Popen(
            ["swaybg", "-i", str(image_path), "-m", "fill"],
            start_new_session=True
        )
        return True, f"Wallpaper set (swaybg): {image_path.name}"
    except FileNotFoundError:
        return False, "swaybg not found"


def _linux_feh(image_path: Path) -> tuple[bool, str]:
    try:
        result = subprocess.run(
            ["feh", "--bg-fill", str(image_path)],
            capture_output=True, text=True, timeout=10
        )
        if result.returncode == 0:
            return True, f"Wallpaper set (feh): {image_path.name}"
        return False, f"feh error: {result.stderr.strip()}"
    except FileNotFoundError:
        return False, "feh not found — install it as a fallback: apt install feh"
    except subprocess.TimeoutExpired:
        return False, "feh timed out"
