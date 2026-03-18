import tkinter as tk
from core.fuzzy import fuzzy_search

class SearchOverlay(tk.Frame):
    def __init__(self, parent, app, images):
        super().__init__(parent, bg='black', bd=1, highlightbackground="white", highlightcolor="white", highlightthickness=1)
        self.app = app
        self.images = images
        self.results = []
        self.selected_idx = 0
        
        # UI
        self.entry_frame = tk.Frame(self, bg='black')
        self.entry_frame.pack(fill=tk.X, padx=10, pady=(10, 5))
        
        lbl = tk.Label(self.entry_frame, text="> ", bg='black', fg='white', font=("Courier", 14))
        lbl.pack(side=tk.LEFT)
        
        self.entry_var = tk.StringVar()
        self.entry_var.trace_add("write", self._on_type)
        self.entry = tk.Entry(self.entry_frame, textvariable=self.entry_var, bg='black', fg='white', font=("Courier", 14), insertbackground='white', bd=0, highlightthickness=0)
        self.entry.pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        self.listbox = tk.Listbox(self, bg='black', fg='white', font=("Courier", 12), bd=0, highlightthickness=0, selectbackground='grey', selectforeground='white')
        self.listbox.pack(fill=tk.BOTH, expand=True, padx=10, pady=(0, 10))
        
        self.entry.bind("<Return>", self._on_enter)
        self.entry.bind("<Up>", self._on_up)
        self.entry.bind("<Down>", self._on_down)
        self.entry.bind("<Escape>", lambda e: self._close())
        
        self.entry.focus_set()
        
        # Populate immediately
        self._on_type()
        
    def _close(self):
        parent = self.master
        self.destroy()
        parent.focus_set()
        
    def _on_type(self, *args):
        query = self.entry_var.get()
        if not query:
            self.results = self.images
        else:
            self.results = fuzzy_search(query, self.images)
            
        self.listbox.delete(0, tk.END)
        for r in self.results:
            self.listbox.insert(tk.END, f"  {r.name}")
            
        self.selected_idx = 0
        if self.results:
            self.listbox.selection_set(0)
            
    def _on_up(self, event):
        if self.results and self.selected_idx > 0:
            self.listbox.selection_clear(self.selected_idx)
            self.selected_idx -= 1
            self.listbox.selection_set(self.selected_idx)
            self.listbox.see(self.selected_idx)
        return "break"
        
    def _on_down(self, event):
        if self.results and self.selected_idx < len(self.results) - 1:
            self.listbox.selection_clear(self.selected_idx)
            self.selected_idx += 1
            self.listbox.selection_set(self.selected_idx)
            self.listbox.see(self.selected_idx)
        return "break"
        
    def _on_enter(self, event):
        if self.results:
            target = self.results[self.selected_idx]
            idx = self.images.index(target)
            self.app.switch_to_image_view(target, idx)
            self.destroy()
