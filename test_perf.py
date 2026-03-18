import cProfile
import pstats
from pathlib import Path
from core.image_loader import ImageLoader
from core.thumb_cache import ThumbCache
from core.thumb_worker import ThumbWorker
import time

def run_test():
    target = Path("test_photos").resolve()
    loader = ImageLoader(target)
    images = loader.load_images()
    
    cache = ThumbCache(target)
    worker = ThumbWorker(cache, num_workers=4)
    
    completed = []
    def callback(ipath, img):
        completed.append(ipath)
        
    start = time.time()
    for img in images:
        worker.request_thumbnail(img, callback)
        
    # Wait for completion
    while len(completed) < len(images):
        time.sleep(0.01)
        
    print(f"Loaded {len(images)} thumbnails in {time.time() - start:.3f}s")
    
if __name__ == "__main__":
    profiler = cProfile.Profile()
    profiler.enable()
    run_test()
    profiler.disable()
    stats = pstats.Stats(profiler).sort_stats('cumtime')
    stats.print_stats(20)
