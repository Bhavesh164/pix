import os
import hashlib
from pathlib import Path
import shutil
from core.image_loader import ImageLoader

class ThumbCache:
    def __init__(self, master_path: Path):
        self.cache_dir = Path.home() / '.cache' / 'pix'
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.master_path = master_path
        
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
        if self.cache_dir.exists():
            shutil.rmtree(self.cache_dir)
            self.cache_dir.mkdir(parents=True, exist_ok=True)

    def _iter_image_paths(self, recursive=False):
        if self.master_path.is_file():
            loader = ImageLoader(self.master_path, recursive=False)
            return loader.load_images()

        loader = ImageLoader(self.master_path, recursive=recursive)
        return loader.load_images()


def format_clear_message(removed_count: int, location: Path | None = None, cache_dir: Path | None = None) -> str:
    noun = "thumbnail" if removed_count == 1 else "thumbnails"
    message = f"Cleared {removed_count} cached {noun}."
    if location is not None:
        message = f"{message[:-1]} for {_display_location(location)}."
    if cache_dir is not None:
        message = f"{message[:-1]} (cache: {_display_location(cache_dir)})."
    return message


def _display_location(path: Path) -> str:
    path = path.expanduser().resolve()
    home = Path.home().resolve()
    try:
        relative = path.relative_to(home)
        return str(Path("~") / relative)
    except ValueError:
        return str(path)
