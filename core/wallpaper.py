"""
macOS wallpaper setter for pix.

Supported platform:
  - macOS: Tahoe wallpaper store + AppleScript fallback
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

    if sys.platform != "darwin":
        return False, f"Wallpaper setting is only supported on macOS. Current platform: {sys.platform}"

    return _set_wallpaper_macos(image_path)


# ─── macOS ────────────────────────────────────────────────────────────────────

def _set_wallpaper_macos(image_path: Path) -> tuple[bool, str]:
    """
    Set wallpaper on macOS using the Tahoe wallpaper store first.
    AppleScript remains as a best-effort fallback for older or unusual environments.
    """
    native_ok, native_message = _set_wallpaper_macos_store(image_path)
    if native_ok:
        return native_ok, native_message

    fallback_ok, fallback_message = _set_wallpaper_macos_applescript(image_path)
    if fallback_ok:
        return fallback_ok, fallback_message

    errors = [msg for msg in (native_message, fallback_message) if msg]
    return False, " | ".join(errors) or "Failed to set wallpaper on macOS"


def _set_wallpaper_macos_store(image_path: Path) -> tuple[bool, str]:
    try:
        from .macos_wallpaper import set_wallpaper as set_wallpaper_store
    except Exception as exc:
        return False, f"Tahoe wallpaper store unavailable: {exc}"

    try:
        return set_wallpaper_store(image_path)
    except Exception as exc:
        return False, f"Tahoe wallpaper error: {exc}"


def _set_wallpaper_macos_applescript(image_path: Path) -> tuple[bool, str]:
    import os

    clean_env = os.environ.copy()
    clean_env.pop("DYLD_LIBRARY_PATH", None)
    clean_env.pop("LD_LIBRARY_PATH", None)
    clean_env.pop("TCL_LIBRARY", None)
    clean_env.pop("TK_LIBRARY", None)
    clean_env["PATH"] = "/usr/bin:/bin:/usr/sbin:/sbin:/usr/local/bin"

    scripts = [
        (
            "System Events",
            f'''
                tell application "System Events"
                    tell every desktop
                        set picture to "{image_path}"
                    end tell
                end tell
            ''',
        ),
        (
            "Finder",
            f'''
                tell application "Finder"
                    set desktop picture to (POSIX file "{image_path}" as alias)
                end tell
            ''',
        ),
    ]

    errors = []
    for label, script in scripts:
        try:
            result = subprocess.run(
                ["/usr/bin/osascript", "-e", script],
                capture_output=True,
                text=True,
                timeout=10,
                env=clean_env,
            )
        except Exception as exc:
            errors.append(f"{label}: {exc}")
            continue

        if result.returncode == 0:
            return True, f"Wallpaper set: {image_path.name}"

        detail = result.stderr.strip() or result.stdout.strip() or "unknown AppleScript failure"
        errors.append(f"{label}: {detail}")

    return False, " | ".join(errors)
