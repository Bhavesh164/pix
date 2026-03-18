import argparse
import sys
from pathlib import Path
from core.image_loader import ImageLoader
from core.thumb_cache import ThumbCache, format_clear_message
from core.wallpaper import set_wallpaper

def main():
    parser = argparse.ArgumentParser(prog="pix", description="pix — Minimal Vim-style Image Viewer")
    parser.add_argument("path", nargs="?", default=".", help="Directory or single image to open")
    parser.add_argument("-r", "--recursive", action="store_true", help="Scan directory recursively")
    parser.add_argument("--clear-cache", action="store_true", help="Purge cache for the specified path, then exit")
    parser.add_argument("--set-wallpaper", action="store_true", help="Set the specified image as wallpaper, then exit")
    
    args = parser.parse_args()
    
    target_path = Path(args.path).expanduser().resolve()
    if not target_path.exists():
        print(f"Error: path '{args.path}' does not exist.")
        sys.exit(1)

    if args.clear_cache:
        cache_base = target_path if target_path.is_dir() else target_path.parent
        cache = ThumbCache(cache_base)
        removed = cache.clear(recursive=args.recursive)
        print(format_clear_message(removed, cache_base, cache.cache_dir))
        sys.exit(0)

    if args.set_wallpaper:
        if not target_path.is_file():
            print("Error: --set-wallpaper requires a single image file path.")
            sys.exit(1)

        success, message = set_wallpaper(target_path)
        print(message)
        sys.exit(0 if success else 1)

    loader = ImageLoader(target_path, args.recursive)
    images = loader.load_images()
    
    if not images and not args.clear_cache:
        print(f"No images found in {target_path}")
        sys.exit(1)
        
    from app import PixApp
    app = PixApp(target_path, recursive=args.recursive, images=images)
    app.run()

if __name__ == "__main__":
    main()
