import hashlib
from pathlib import Path
import shutil
from uuid import uuid4
from core.image_loader import ImageLoader


class ThumbCache:
    def __init__(self, master_path: Path):
        self.cache_dir = Path.home() / '.cache' / 'pix'
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.master_path = Path(master_path).expanduser().resolve()
        
    def get_cache_path(self, filepath: Path) -> Path:
        mtime = filepath.stat().st_mtime
        key_string = f"{filepath.resolve()}_{mtime}"
        key_hash = hashlib.sha1(key_string.encode('utf-8')).hexdigest()
        return self.cache_dir / f"{key_hash}.webp"
        
    def clear(self, recursive=False):
        removed = 0
        for image_path in self._iter_image_paths(recursive=recursive):
            cache_path = self.get_cache_path(image_path)
            try:
                cache_path.unlink()
                removed += 1
            except FileNotFoundError:
                continue
        return removed
        
    def wipe_all(self):
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        detached_cache_dir = self.cache_dir.with_name(f"{self.cache_dir.name}.purge-{uuid4().hex}")

        try:
            # Move the active cache out of the way first so concurrent thumbnail
            # writers immediately target a fresh directory instead of racing rmtree.
            self.cache_dir.replace(detached_cache_dir)
        except FileNotFoundError:
            self.cache_dir.mkdir(parents=True, exist_ok=True)
            return
        except OSError:
            self._wipe_in_place()
            return

        self.cache_dir.mkdir(parents=True, exist_ok=True)
        shutil.rmtree(detached_cache_dir, ignore_errors=True)

    def _iter_image_paths(self, recursive=False):
        if self.master_path.is_file():
            loader = ImageLoader(self.master_path, recursive=False)
            return loader.load_images()

        loader = ImageLoader(self.master_path, recursive=recursive)
        return loader.load_images()

    def _wipe_in_place(self):
        for child in list(self.cache_dir.iterdir()):
            try:
                if child.is_dir():
                    shutil.rmtree(child, ignore_errors=True)
                else:
                    child.unlink()
            except FileNotFoundError:
                continue

        self.cache_dir.mkdir(parents=True, exist_ok=True)


def format_clear_message(removed_count: int, location: Path | None = None, cache_dir: Path | None = None) -> str:
    noun = "thumbnail" if removed_count == 1 else "thumbnails"
    message = f"Cleared {removed_count} cached {noun}."
    if location is not None:
        message = f"{message[:-1]} for {_display_location(location)}."
    if cache_dir is not None:
        message = f"{message[:-1]} (cache: {_display_location(cache_dir)})."
    return message


def format_wipe_all_message(cache_dir: Path) -> str:
    return f"Cleared entire thumbnail cache (cache: {_display_location(cache_dir)})."


def _display_location(path: Path) -> str:
    path = path.expanduser().resolve()
    home = Path.home().resolve()
    try:
        relative = path.relative_to(home)
        return str(Path("~") / relative)
    except ValueError:
        return str(path)
