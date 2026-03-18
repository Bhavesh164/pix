import os
import hashlib
from pathlib import Path
import shutil

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
        # We need to list cache and check if original path starts with master_path
        # But our key only has the hash. So we should probably store a metadata file or name it differently.
        # Alternatively, a simple wipe of the entire cache is what most users mean if they run --clear-cache.
        # Let's purge files that are old or just wipe the dir. The plan says "Purge cache only for this folder".
        # This implies we need the path in the filename, e.g. base64_path_timestamp.webp or similar.
        # For simplicity and speed, let's just wipe everything if we can't tell,
        # OR let's change our key strategy: include sha1 of path, but maybe keep a map.
        pass
        
    def wipe_all(self):
        if self.cache_dir.exists():
            shutil.rmtree(self.cache_dir)
            self.cache_dir.mkdir(parents=True, exist_ok=True)
