from __future__ import annotations

import ctypes
import sys
from ctypes import c_bool, c_char_p, c_long, c_ulong, c_void_p
from pathlib import Path
from typing import Iterable


def copy_paths(paths: Iterable[Path], clipboard_owner=None) -> tuple[bool, str]:
    resolved_paths = [Path(path).expanduser().resolve() for path in paths]
    if not resolved_paths:
        return False, "No images selected to copy."

    detail = ""
    if sys.platform == "darwin":
        success, detail = _copy_paths_macos(resolved_paths)
        if success:
            return True, format_copy_message(len(resolved_paths))

    if clipboard_owner is not None:
        success, detail = _copy_paths_as_text(clipboard_owner, resolved_paths)
        if success:
            return True, format_copy_message(len(resolved_paths), copied_as_paths=True)

    if not detail:
        detail = "Clipboard is unavailable."
    return False, f"Failed to copy images: {detail}"


def format_copy_message(count: int, copied_as_paths: bool = False) -> str:
    if copied_as_paths:
        return f"Copied {count} image path{'s' if count != 1 else ''} to clipboard."
    noun = "image" if count == 1 else "images"
    return f"Copied {count} {noun} to clipboard."


def _copy_paths_as_text(clipboard_owner, paths: list[Path]) -> tuple[bool, str]:
    try:
        clipboard_owner.clipboard_clear()
        clipboard_owner.clipboard_append("\n".join(str(path) for path in paths))
        clipboard_owner.update_idletasks()
    except Exception as exc:
        return False, str(exc)
    return True, ""


def _copy_paths_macos(paths: list[Path]) -> tuple[bool, str]:
    try:
        return _copy_paths_macos_native(paths)
    except Exception as exc:
        return False, str(exc)


def _copy_paths_macos_native(paths: list[Path]) -> tuple[bool, str]:
    objc = ctypes.cdll.LoadLibrary("/usr/lib/libobjc.A.dylib")
    ctypes.cdll.LoadLibrary("/System/Library/Frameworks/Foundation.framework/Foundation")
    ctypes.cdll.LoadLibrary("/System/Library/Frameworks/AppKit.framework/AppKit")

    objc.objc_getClass.argtypes = [c_char_p]
    objc.objc_getClass.restype = c_void_p
    objc.sel_registerName.argtypes = [c_char_p]
    objc.sel_registerName.restype = c_void_p
    objc.objc_autoreleasePoolPush.restype = c_void_p
    objc.objc_autoreleasePoolPop.argtypes = [c_void_p]

    def cls(name: str) -> int:
        value = objc.objc_getClass(name.encode("utf-8"))
        if not value:
            raise RuntimeError(f"Objective-C class not found: {name}")
        return value

    def msg(restype, argtypes, receiver, selector: str, *args):
        func = ctypes.CFUNCTYPE(restype, c_void_p, c_void_p, *argtypes)(("objc_msgSend", objc))
        return func(receiver, objc.sel_registerName(selector.encode("utf-8")), *args)

    pool = objc.objc_autoreleasePoolPush()
    try:
        ns_string = cls("NSString")
        ns_url = cls("NSURL")
        ns_mutable_array = cls("NSMutableArray")
        ns_pasteboard = cls("NSPasteboard")

        objects = msg(c_void_p, [c_ulong], ns_mutable_array, "arrayWithCapacity:", len(paths))
        for path in paths:
            path_string = msg(c_void_p, [c_char_p], ns_string, "stringWithUTF8String:", str(path).encode("utf-8"))
            file_url = msg(c_void_p, [c_void_p, c_bool], ns_url, "fileURLWithPath:isDirectory:", path_string, False)
            msg(None, [c_void_p], objects, "addObject:", file_url)

        pasteboard = msg(c_void_p, [], ns_pasteboard, "generalPasteboard")
        msg(c_long, [], pasteboard, "clearContents")
        copied = bool(msg(c_bool, [c_void_p], pasteboard, "writeObjects:", objects))
        if not copied:
            return False, "macOS pasteboard rejected the copy request."
        return True, ""
    finally:
        objc.objc_autoreleasePoolPop(pool)
