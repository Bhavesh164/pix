import tkinter as tk
from PIL import Image, ImageTk
from core.thumb_worker import ThumbWorker

class ThumbnailView(tk.Frame):
    def __init__(self, parent, app, images, thumb_cache):
        super().__init__(parent, bg='black')
        self.app = app
        self.images = images
        self.thumb_cache = thumb_cache
        self.thumb_size = 160
        
        self.worker = ThumbWorker(self.thumb_cache, num_workers=4, thumb_size=(self.thumb_size, self.thumb_size))
        
        self.canvas = tk.Canvas(self, bg='black', highlightthickness=0)
        self.canvas.pack(fill=tk.BOTH, expand=True)
        
        self.items = []
        self.selected_index = 0
        self.multi_selected = set()
        self.cols = 5
        self.pending_g = False
        self.tk_images = {}
        
        self.bind("<Configure>", self._on_resize)
        self._build_grid()
        self._bind_keys()
        
    def _on_resize(self, event):
        if event.widget == self:
            width = event.width
            new_cols = max(1, width // (self.thumb_size + 20))
            if new_cols != self.cols:
                self.cols = new_cols
            # Always rearrange on resize to keep equal spacing!
            self._rearrange_grid()
            
    def _get_outline_color(self, idx):
        is_focused = (idx == self.selected_index)
        is_selected = (idx in self.multi_selected)
        if is_focused and is_selected:
            return 'cyan'
        elif is_focused:
            return 'white'
        elif is_selected:
            return 'yellow'
        return 'grey'

    def _build_grid(self):
        total = len(self.images)
        for i, img_path in enumerate(self.images):
            # Create rect (background/highlight) using Pure Canvas instead of Frames for MILLISECOND performance
            rect_color = self._get_outline_color(i)
            rect_id = self.canvas.create_rectangle(0, 0, 0, 0, fill='black', outline=rect_color, width=2)
            
            # Create text
            text_id = self.canvas.create_text(0, 0, text=img_path.name[-15:], fill='white', anchor='s')
            
            # Create image placeholder
            img_id = self.canvas.create_image(0, 0, image="", anchor='center')
            
            self.items.append({
                'path': img_path,
                'rect_id': rect_id,
                'text_id': text_id,
                'img_id': img_id
            })
            
            self.worker.request_thumbnail(img_path, self._on_thumb_loaded_callback)
            
    def _on_thumb_loaded_callback(self, image_path, thumb):
        idx = self.images.index(image_path)
        tk_img = ImageTk.PhotoImage(thumb)
        self.tk_images[image_path] = tk_img
        self.after(0, lambda tk_img=tk_img, idx=idx: self.canvas.itemconfig(self.items[idx]['img_id'], image=tk_img))
        
    def _rearrange_grid(self):
        item_w = self.thumb_size + 20
        item_h = self.thumb_size + 34
        
        width = self.winfo_width()
        margin = max(0, (width - (self.cols * item_w)) // 2)
        
        rows = (len(self.images) + self.cols - 1) // self.cols
        self.canvas.configure(scrollregion=(0, 0, self.cols * item_w + margin * 2, rows * item_h))
        
        for i, item in enumerate(self.items):
            row = i // self.cols
            col = i % self.cols
            
            x = margin + col * item_w + item_w // 2
            y = row * item_h + item_h // 2
            
            self.canvas.coords(item['rect_id'], x - item_w//2 + 2, y - item_h//2 + 2, x + item_w//2 - 2, y + item_h//2 - 2)
            self.canvas.coords(item['img_id'], x, y - 8)
            self.canvas.coords(item['text_id'], x, y + item_h//2 - 6)
            
    def _bind_keys(self):
        self.focus_set()
        self.bind("<Right>", lambda e: self._move(1))
        self.bind("<Left>", lambda e: self._move(-1))
        self.bind("<Down>", lambda e: self._move(self.cols))
        self.bind("<Up>", lambda e: self._move(-self.cols))
        self.bind("l", lambda e: self._move(1))
        self.bind("h", lambda e: self._move(-1))
        self.bind("j", lambda e: self._move(self.cols))
        self.bind("k", lambda e: self._move(-self.cols))
        self.bind("<Return>", lambda e: self._open_image())
        self.bind("<space>", lambda e: self._toggle_select())
        self.bind("V", lambda e: self._select_all())
        self.bind("d", lambda e: self._delete_selected())
        self.bind("q", lambda e: self.app.quit())
        self.bind("<Escape>", lambda e: self.app.quit())
        self.bind("?", lambda e: self._show_help())
        self.bind("/", lambda e: self._show_search())
        self.bind("<Control-d>", lambda e: self._move_page(down=True, half=True))
        self.bind("<Control-u>", lambda e: self._move_page(down=False, half=True))
        self.bind("G", lambda e: self._go_extreme(bottom=True))
        self.bind("g", self._on_g)
        self.bind("b", lambda e: self._set_wallpaper())
        self.bind("W", lambda e: self._set_wallpaper())
        
        self.bind("<MouseWheel>", self._on_mousewheel)
        self.bind("<Button-4>", self._on_mousewheel)
        self.bind("<Button-5>", self._on_mousewheel)
        
    def _on_mousewheel(self, event):
        if hasattr(event, "num") and event.num == 4 or hasattr(event, "delta") and event.delta > 0:
            self.canvas.yview_scroll(-1, "units")
        elif hasattr(event, "num") and event.num == 5 or hasattr(event, "delta") and event.delta < 0:
            self.canvas.yview_scroll(1, "units")
            
    def _move_page(self, down=True, half=True):
        visible_rows = max(1, self.canvas.winfo_height() // (self.thumb_size + 34))
        delta_rows = max(1, visible_rows // 2 if half else visible_rows)
        delta = (delta_rows * self.cols) if down else -(delta_rows * self.cols)
        self._move(delta)
        
    def _go_extreme(self, bottom=True):
        if bottom:
            self._move(len(self.images) - 1 - self.selected_index)
        else:
            self._move(-self.selected_index)
            
    def _on_g(self, event):
        if self.pending_g:
            self._go_extreme(bottom=False)
            self.pending_g = False
        else:
            self.pending_g = True
            self.after(500, self._clear_g)
            
    def _clear_g(self):
        self.pending_g = False

    def _set_wallpaper(self):
        image_path = self.images[self.selected_index]
        self.app.set_wallpaper(image_path)

    def _show_help(self):
        from overlays.help_overlay import HelpOverlay
        ov = HelpOverlay(self)
        ov.place(relx=0.5, rely=0.5, anchor=tk.CENTER)
        
    def _show_search(self):
        from overlays.search_overlay import SearchOverlay
        ov = SearchOverlay(self, self.app, self.images)
        ov.place(relx=0.5, rely=0.5, anchor=tk.CENTER)
        
    def _move(self, delta):
        new_idx = self.selected_index + delta
        if 0 <= new_idx < len(self.images):
            # unhighlight old
            old_idx = self.selected_index
            self.selected_index = new_idx
            self.canvas.itemconfig(self.items[old_idx]['rect_id'], outline=self._get_outline_color(old_idx))
            # highlight new
            self.canvas.itemconfig(self.items[self.selected_index]['rect_id'], outline=self._get_outline_color(self.selected_index))
            
            row = self.selected_index // self.cols
            item_h = self.thumb_size + 34
            target_y = row * item_h
            
            bbox = self.canvas.bbox("all")
            if bbox:
                total_h = bbox[3]
                h = self.canvas.winfo_height()
                if total_h > 0:
                    current_top = self.canvas.yview()[0] * total_h
                    current_bottom = self.canvas.yview()[1] * total_h
                    
                    if target_y < current_top:
                        self.canvas.yview_moveto(target_y / total_h)
                    elif target_y + item_h > current_bottom:
                        self.canvas.yview_moveto((target_y + item_h - h) / total_h)
                
    def _open_image(self):
        self.app.switch_to_image_view(self.images[self.selected_index], self.selected_index)

    def _toggle_select(self):
        if self.selected_index in self.multi_selected:
            self.multi_selected.remove(self.selected_index)
        else:
            self.multi_selected.add(self.selected_index)
        self.canvas.itemconfig(self.items[self.selected_index]['rect_id'], outline=self._get_outline_color(self.selected_index))
        
    def _select_all(self):
        if len(self.multi_selected) == len(self.images):
            self.multi_selected.clear()
        else:
            self.multi_selected = set(range(len(self.images)))
        
        for i, item in enumerate(self.items):
            self.canvas.itemconfig(item['rect_id'], outline=self._get_outline_color(i))

    def _delete_selected(self):
        to_delete = list(self.multi_selected)
        if not to_delete:
            to_delete = [self.selected_index]
            
        try:
            from overlays.confirm_overlay import ConfirmOverlay
            ov = ConfirmOverlay(self, self.app, to_delete)
            ov.place(relx=0.5, rely=0.5, anchor=tk.CENTER)
        except ImportError:
            print(f"Skipping delete of {len(to_delete)} images (confirm_overlay.py missing)")
