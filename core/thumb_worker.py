import concurrent.futures
from PIL import Image, ImageOps
from pathlib import Path

class ThumbWorker:
    def __init__(self, cache_manager, num_workers=4, thumb_size=(160, 160)):
        self.cache_manager = cache_manager
        self.pool = concurrent.futures.ThreadPoolExecutor(max_workers=num_workers)
        self.thumb_size = thumb_size
        
    def generate_thumbnail(self, image_path: Path):
        cache_path = self.cache_manager.get_cache_path(image_path)
        
        # Layer 3: Cache read
        if cache_path.exists():
            try:
                # Return cached image instantly
                return Image.open(cache_path).copy()
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
                img.save(cache_path, format="WEBP")
                
                # Return a copy to avoid passing closed image referencing file
                return img.copy()
        except Exception as e:
            print(f"Error making thumbnail for {image_path}: {e}")
            # return a blank image on failure
            return Image.new('RGB', self.thumb_size, color='gray')
            
    def request_thumbnail(self, image_path: Path, callback):
        def worker():
            thumb = self.generate_thumbnail(image_path)
            callback(image_path, thumb)
        self.pool.submit(worker)
