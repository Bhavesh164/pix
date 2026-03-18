import argparse
import sys
from pathlib import Path
from core.image_loader import ImageLoader

def main():
    parser = argparse.ArgumentParser(description="pix — Minimal Vim-style Image Viewer")
    parser.add_argument("path", nargs="?", default=".", help="Directory or single image to open")
    parser.add_argument("-r", "--recursive", action="store_true", help="Scan directory recursively")
    parser.add_argument("--clear-cache", action="store_true", help="Purge cache for the specified path, then exit")
    
    args = parser.parse_args()
    
    target_path = Path(args.path).expanduser().resolve()
    if not target_path.exists():
        print(f"Error: path '{args.path}' does not exist.")
        sys.exit(1)

    loader = ImageLoader(target_path, args.recursive)
    images = loader.load_images()
    
    if not images and not args.clear_cache:
        print(f"No images found in {target_path}")
        sys.exit(1)
        
    from app import PixApp
    app = PixApp(target_path, recursive=args.recursive, clear_cache=args.clear_cache, images=images)
    if not args.clear_cache:
        app.run()

if __name__ == "__main__":
    main()
