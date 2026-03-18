import tkinter as tk
from pathlib import Path
from core.image_loader import ImageLoader
from core.thumb_cache import ThumbCache, format_clear_message, format_wipe_all_message
from core.wallpaper import set_wallpaper
from views.thumbnail_view import ThumbnailView
from views.image_view import ImageView

class PixApp:
    def __init__(self, target_path, recursive=False, images=None):
        self.target_path = Path(target_path).expanduser().resolve()
        self.recursive = recursive
        cache_base = self.target_path if self.target_path.is_dir() else self.target_path.parent
        self.thumb_cache = ThumbCache(cache_base)

        self.root = tk.Tk()
        self.root.configure(bg='black')
        self.root.attributes('-fullscreen', True)
        # self.root.overrideredirect(True) on mac can still leave remnants, fullscreen completely hides decorations.
        
        # We need a way to track the active view so we can bind/unbind keys cleanly
        self.active_view = None
        self.loader = ImageLoader(self.target_path, recursive)
        
        # Load images
        self.images = images if images is not None else self.loader.load_images()
        if not self.images:
            print(f"No images found in {self.target_path}")
            sys.exit(1)
            
        self.is_single_image = self.target_path.is_file()
        
        # Setup container frame so views can pack
        self.container = tk.Frame(self.root, bg='black')
        self.container.pack(fill=tk.BOTH, expand=True)

        if self.is_single_image:
            self.switch_to_image_view(self.images[0], 0)
        else:
            self.switch_to_thumbnail_view()

    def run(self):
        self.root.mainloop()

    def switch_to_thumbnail_view(self):
        if self.active_view:
            # Hide rather than destroy for INSTANT switching
            self.active_view.pack_forget()
            
        if not hasattr(self, 'thumb_view_instance'):
            self.thumb_view_instance = ThumbnailView(self.container, self, self.images, self.thumb_cache)
            
        self.active_view = self.thumb_view_instance
        self.active_view.pack(fill=tk.BOTH, expand=True)
        self.active_view.focus_set()
        
    def switch_to_image_view(self, image_path, index):
        if self.active_view:
            self.active_view.pack_forget()
            
        if hasattr(self, 'image_view_instance') and self.image_view_instance:
            self.image_view_instance.destroy()
            
        self.image_view_instance = ImageView(self.container, self, self.images, image_path, index)
        self.active_view = self.image_view_instance
        self.active_view.pack(fill=tk.BOTH, expand=True)
        self.active_view.focus_set()
        
    def set_wallpaper(self, image_path):
        """Set the desktop wallpaper on macOS and show a brief toast."""
        success, message = set_wallpaper(image_path)
        self._show_toast(message)

    def clear_cache(self):
        removed = self.thumb_cache.clear(recursive=self.recursive)
        self._show_toast(
            format_clear_message(
                removed,
                self.thumb_cache.master_path,
                self.thumb_cache.cache_dir,
            ),
            duration_ms=3500,
        )

    def clear_entire_cache(self):
        self.thumb_cache.wipe_all()
        self._show_toast(
            format_wipe_all_message(self.thumb_cache.cache_dir),
            duration_ms=3500,
        )

    def _show_toast(self, message, duration_ms=2500):
        """Show a transient status message in the bottom-right corner."""
        toast = tk.Label(
            self.root,
            text=f"  {message}  ",
            bg='#1a1a1a', fg='white',
            font=("Courier", 12),
            relief='flat',
            padx=8, pady=6,
            highlightbackground='#444',
            highlightthickness=1,
        )
        sw = self.root.winfo_screenwidth()
        sh = self.root.winfo_screenheight()
        toast.place(x=sw - 20, y=sh - 40, anchor='se') # Moved up slightly to avoid status bar overlap
        toast.lift()
        self.root.after(duration_ms, toast.destroy)

    def quit(self):
        self.root.quit()
