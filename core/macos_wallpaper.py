"""
macOS Tahoe wallpaper integration backed by the system wallpaper store.
"""

from __future__ import annotations

from datetime import UTC, datetime
import os
import plistlib
import re
import subprocess
import tempfile
import time
from pathlib import Path


WALLPAPER_AGENT_LABEL = "com.apple.wallpaper.agent"


def set_wallpaper(image_path: Path, store_path: Path | None = None) -> tuple[bool, str]:
    store_path = store_path or _default_store_path()
    if not store_path.exists():
        return False, f"Wallpaper store not found: {store_path}"

    try:
        with store_path.open("rb") as handle:
            store = plistlib.load(handle)
    except Exception as exc:
        return False, f"Failed to read Tahoe wallpaper store: {exc}"

    updated = _rewrite_store(store, image_path)
    if updated == 0:
        return False, "Tahoe wallpaper store did not contain any desktop entries to update"

    try:
        _write_plist_atomically(store_path, store)
    except Exception as exc:
        return False, f"Failed to write Tahoe wallpaper store: {exc}"

    try:
        _restart_wallpaper_agent()
    except Exception as exc:
        return False, f"Wallpaper store updated but agent refresh failed: {exc}"

    return True, f"Wallpaper updated: {image_path.name}"


def _default_store_path() -> Path:
    return Path.home() / "Library/Application Support/com.apple.wallpaper/Store/Index.plist"


def _rewrite_store(store: object, image_path: Path) -> int:
    if isinstance(store, dict):
        updated = 0

        desktop = store.get("Desktop")
        if isinstance(desktop, dict):
            _rewrite_desktop_entry(desktop, image_path)
            updated += 1

        for value in store.values():
            updated += _rewrite_store(value, image_path)
        return updated

    if isinstance(store, list):
        return sum(_rewrite_store(item, image_path) for item in store)

    return 0


def _rewrite_desktop_entry(desktop_entry: dict, image_path: Path) -> None:
    content = desktop_entry.setdefault("Content", {})
    content["Choices"] = [_image_choice(image_path)]
    content.setdefault("EncodedOptionValues", "$null")
    content.setdefault("Shuffle", "$null")

    now = datetime.now(UTC).replace(tzinfo=None)
    desktop_entry["LastSet"] = now
    desktop_entry["LastUse"] = now


def _image_choice(image_path: Path) -> dict:
    configuration = {
        "type": "imageFile",
        "url": {
            "relative": image_path.resolve().as_uri(),
        },
    }
    return {
        "Configuration": plistlib.dumps(configuration, fmt=plistlib.FMT_BINARY),
        "Files": [],
        "Provider": "com.apple.wallpaper.choice.image",
    }


def _write_plist_atomically(target_path: Path, payload: object) -> None:
    parent = target_path.parent
    fd, temp_path = tempfile.mkstemp(prefix=f"{target_path.name}.", suffix=".tmp", dir=parent)
    try:
        with os.fdopen(fd, "wb") as handle:
            plistlib.dump(payload, handle, fmt=plistlib.FMT_BINARY, sort_keys=False)
        os.replace(temp_path, target_path)
    except Exception:
        try:
            os.unlink(temp_path)
        except OSError:
            pass
        raise


def _wallpaper_agent_target() -> str:
    return f"gui/{os.getuid()}/{WALLPAPER_AGENT_LABEL}"


def _extract_wallpaper_agent_pid(output: str) -> int | None:
    match = re.search(r"\bpid = (\d+)\b", output)
    return int(match.group(1)) if match else None


def _get_wallpaper_agent_pid() -> int | None:
    result = subprocess.run(
        ["/bin/launchctl", "print", _wallpaper_agent_target()],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        return None
    return _extract_wallpaper_agent_pid(result.stdout)


def _restart_wallpaper_agent(timeout_s: float = 5.0) -> None:
    old_pid = _get_wallpaper_agent_pid()
    if old_pid is None:
        raise RuntimeError(f"Could not locate {WALLPAPER_AGENT_LABEL}")

    result = subprocess.run(
        ["/bin/kill", str(old_pid)],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        detail = result.stderr.strip() or result.stdout.strip() or "kill failed"
        raise RuntimeError(detail)

    deadline = time.monotonic() + timeout_s
    while time.monotonic() < deadline:
        new_pid = _get_wallpaper_agent_pid()
        if new_pid is not None and new_pid != old_pid:
            return
        time.sleep(0.1)

    raise RuntimeError(f"{WALLPAPER_AGENT_LABEL} did not restart in time")
