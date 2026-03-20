from __future__ import annotations

import concurrent.futures
from pathlib import Path
from typing import Any, Callable

from PIL import Image, ImageOps  # pyre-ignore


ThumbnailCallback = Callable[[Path, Any], None]

class ThumbWorker:
    def __init__(
        self,
        cache_manager: Any,
        num_workers: int = 4,
        thumb_size: tuple[int, int] = (160, 160),
    ) -> None:
        self.cache_manager = cache_manager
        self.pool = concurrent.futures.ThreadPoolExecutor(max_workers=num_workers)
        self.thumb_size = thumb_size
        
    def generate_thumbnail(self, image_path: Path) -> Any:
        cache_path = self.cache_manager.get_cache_path(image_path)
        
        # Layer 3: Cache read
        if cache_path.exists():
            try:
                # Return cached image instantly
                with Image.open(cache_path) as cached_image:
                    return cached_image.copy()
            except Exception:
                pass
                
        # Generate new thumbnail
        try:
            with Image.open(image_path) as img:
                # Pillow's EXIF auto-rotation
                img = ImageOps.exif_transpose(img)
                
                # Layer 2: Subsampled decode
                img.draft('RGB', self.thumb_size)
                
                # Resize
                img.thumbnail(self.thumb_size)
                
                # Convert to RGB to ensure webp compatibility
                if img.mode != 'RGB':
                    img = img.convert('RGB')
                    
                # Store in cache
                cache_path.parent.mkdir(parents=True, exist_ok=True)
                img.save(cache_path, format="WEBP")
                
                # Return a copy to avoid passing closed image referencing file
                return img.copy()
        except Exception as e:
            print(f"Error making thumbnail for {image_path}: {e}")
            # return a blank image on failure
            return Image.new('RGB', self.thumb_size, color='gray')

    def _dispatch_thumbnail(self, image_path: Path, callback: ThumbnailCallback) -> None:
        thumb = self.generate_thumbnail(image_path)
        callback(image_path, thumb)

    def request_thumbnail(self, image_path: Path, callback: ThumbnailCallback) -> None:
        self.pool.submit(self._dispatch_thumbnail, image_path, callback)  # pyre-ignore[6]
