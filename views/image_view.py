import tkinter as tk
from PIL import Image, ImageTk, ImageOps

class ImageView(tk.Frame):
    def __init__(self, parent, app, images, image_path, index):
        super().__init__(parent, bg='black')
        self.app = app
        self.images = images
        self.image_path = image_path
        self.index = index
        
        self.canvas = tk.Canvas(self, bg='black', highlightthickness=0)
        self.canvas.pack(fill=tk.BOTH, expand=True)
        
        self.status = tk.Label(self, bg='black', fg='grey', anchor='w', font=("Courier", 12))
        self.status.pack(side=tk.BOTTOM, fill=tk.X)
        
        self.image = None
        self.tk_image = None
        self.zoom = 1.0
        self.pan_x = 0
        self.pan_y = 0
        
        self._load_image()
        
        self.bind("<Configure>", self._on_resize)
        self._bind_keys()
        
    def _load_image(self):
        self.image_path = self.images[self.index]
        self.image = Image.open(self.image_path)
        self.image = ImageOps.exif_transpose(self.image)
        self.zoom = 1.0
        self.pan_x = 0
        self.pan_y = 0
        self._update_status()
        self._render()
        
    def _on_resize(self, event):
        if event.widget == self:
            self._render()
            
    def _render(self):
        if not self.image:
            return
            
        iw, ih = self.image.size
        cw, ch = self.winfo_width(), self.winfo_height() - self.status.winfo_reqheight()
        
        if cw <= 1 or ch <= 1:
            cw, ch = self.app.root.winfo_screenwidth(), self.app.root.winfo_screenheight()
            
        ratio = min(cw/iw, ch/ih)
        new_size = (int(iw * ratio * self.zoom), int(ih * ratio * self.zoom))
            
        if new_size[0] <= 0 or new_size[1] <= 0:
            return
            
        # For performance during panning/zooming, nearest neighbor is faster but Lanczos looks better
        # The skill says performance is key, so maybe we use NEAREST or BILINEAR when zoomed out, LANCZOS when zoomed in 
        # For our case, BILINEAR is a good compromise for speed vs quality
        render_img = self.image.resize(new_size, Image.Resampling.BILINEAR)
        self.tk_image = ImageTk.PhotoImage(render_img)
        
        self.canvas.delete("all")
        self.canvas.create_image(cw//2 + self.pan_x, ch//2 + self.pan_y, anchor=tk.CENTER, image=self.tk_image)
        
    def _update_status(self):
        txt = f"VIEW  |  {self.image_path.name}  |  {self.index+1}/{len(self.images)}  |  zoom: {int(self.zoom*100)}%  |  {self.image.width}x{self.image.height}"
        self.status.config(text=txt)

    def _bind_keys(self):
        self.focus_set()
        self._bind_shortcut("q", lambda e: self.app.switch_to_thumbnail_view() if not self.app.is_single_image else self.app.quit())
        self._bind_shortcut("<Escape>", lambda e: self.app.switch_to_thumbnail_view() if not self.app.is_single_image else self.app.quit())
        self._bind_shortcut("l", lambda e: self._move(1))
        self._bind_shortcut("h", lambda e: self._move(-1))
        self._bind_shortcut("<Right>", lambda e: self._move(1))
        self._bind_shortcut("<Left>", lambda e: self._move(-1))
        self._bind_shortcut("i", lambda e: self._change_zoom(0.1))
        self._bind_shortcut("o", lambda e: self._change_zoom(-0.1))
        self._bind_shortcut("u", lambda e: self._reset_zoom())
        self._bind_shortcut("w", lambda e: self._pan(0, -50))
        self._bind_shortcut("a", lambda e: self._pan(-50, 0))
        self._bind_shortcut("s", lambda e: self._pan(0, 50))
        self._bind_shortcut("d", lambda e: self._pan(50, 0))
        self._bind_shortcut("<Up>", lambda e: self._pan(0, -50))
        self._bind_shortcut("<Down>", lambda e: self._pan(0, 50))
        self._bind_shortcut("b", lambda e: self.app.set_wallpaper(self.image_path))
        self._bind_shortcut("y", lambda e: self._copy_image())
        self._bind_shortcut("?", lambda e: self._show_help())
        self._bind_shortcut("/", lambda e: self._show_search())
        self._bind_shortcut("c", lambda e: self.app.clear_cache())
        self._bind_shortcut("C", lambda e: self.app.clear_cache())
        self._bind_shortcut("x", lambda e: self.app.clear_entire_cache())

    def _bind_shortcut(self, sequence, handler):
        self.bind(sequence, handler)
        self.canvas.bind(sequence, handler)
        
    def _show_help(self):
        from overlays.help_overlay import HelpOverlay
        ov = HelpOverlay(self)
        ov.place(relx=0.5, rely=0.5, anchor=tk.CENTER)
        
    def _show_search(self):
        from overlays.search_overlay import SearchOverlay
        ov = SearchOverlay(self, self.app, self.images)
        ov.place(relx=0.5, rely=0.5, anchor=tk.CENTER)

    def _copy_image(self):
        self.app.copy_images([self.image_path])
        
    def _move(self, delta):
        new_idx = self.index + delta
        if 0 <= new_idx < len(self.images):
            self.index = new_idx
            self._load_image()
            
    def _change_zoom(self, delta):
        self.zoom = max(0.1, self.zoom + delta)
        self._update_status()
        self._render()
        
    def _reset_zoom(self):
        self.zoom = 1.0
        self.pan_x = 0
        self.pan_y = 0
        self._update_status()
        self._render()
        
    def _pan(self, dx, dy):
        if not self.image or self.zoom <= 1.0:
            return
            
        iw, ih = self.image.size
        cw, ch = self.winfo_width(), self.winfo_height() - self.status.winfo_reqheight()
        ratio = min(cw/iw, ch/ih)
        new_w, new_h = int(iw * ratio * self.zoom), int(ih * ratio * self.zoom)
        
        max_pan_x = max(0, (new_w - cw) // 2)
        max_pan_y = max(0, (new_h - ch) // 2)
        
        self.pan_x -= dx
        self.pan_y -= dy
        
        self.pan_x = max(-max_pan_x, min(max_pan_x, self.pan_x))
        self.pan_y = max(-max_pan_y, min(max_pan_y, self.pan_y))
        
        self._render()
