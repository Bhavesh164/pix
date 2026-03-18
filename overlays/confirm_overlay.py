import tkinter as tk
import os

class ConfirmOverlay(tk.Frame):
    def __init__(self, parent_view, app, to_delete_indices):
        super().__init__(parent_view, bg='#1a1a1a', bd=1, relief=tk.SOLID, highlightbackground='#333333', highlightthickness=1)
        self.app = app
        self.parent_view = parent_view
        self.to_delete_indices = sorted(to_delete_indices, reverse=True)
        
        count = len(self.to_delete_indices)
        text = f"Delete {count} image{'s' if count > 1 else ''}? [y/N]"
        
        self.label = tk.Label(self, text=text, fg='white', bg='#1a1a1a', font=('Courier', 14))
        self.label.pack(padx=20, pady=10)
        
        self._bind_keys()
        
    def _bind_keys(self):
        self.focus_set()
        self.bind("y", lambda e: self._confirm())
        self.bind("Y", lambda e: self._confirm())
        self.bind("n", lambda e: self._cancel())
        self.bind("N", lambda e: self._cancel())
        self.bind("<Escape>", lambda e: self._cancel())
        
        # Prevent bindings from leaking to the parent grid view while overlay is active
        for key in ["<Return>", "<space>", "<Left>", "<Right>", "<Up>", "<Down>", "h", "j", "k", "l", "d", "v", "V"]:
            self.bind(key, lambda e: "break")
            
    def _confirm(self):
        # Delete from disk and app tracking array
        for i in self.to_delete_indices:
            img_path = self.app.images[i]
            try:
                os.remove(img_path)
            except Exception as e:
                print(f"Failed to delete {img_path}: {e}")
            del self.app.images[i]
            
        if not self.app.images:
            # If we deleted the very last image, just exit gracefully
            self.app.quit()
            return
            
        # Re-initialize the thumbnail view so the grid is rebuilt without the deleted items
        self.parent_view.destroy()
        if hasattr(self.app, 'thumb_view_instance'):
            delattr(self.app, 'thumb_view_instance')
            
        self.app.switch_to_thumbnail_view()

    def _cancel(self):
        # Restore focus to grid and destroy overlay
        self.parent_view.focus_set()
        self.destroy()
