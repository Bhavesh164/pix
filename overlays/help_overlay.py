import tkinter as tk

class HelpOverlay(tk.Frame):
    def __init__(self, parent):
        super().__init__(parent, bg='black', highlightbackground="white", highlightcolor="white", highlightthickness=1)
        
        text = """
╔─── keybindings ─────────────╗
│  GRID VIEW                  │
│  h j k l   navigate         │
│  Enter     open image       │
│  Space     select           │
│  d         delete selected  │
│  /         search           │
│                             │
│  IMAGE VIEW                 │
│  q         back to grid     │
│  i o       zoom in/out      │
│  u         reset zoom       │
│  w a s d   pan image (zoom) │
│  h l       prev/next        │
│                             │
│            Esc to close     │
╚─────────────────────────────╝
"""
        lbl = tk.Label(self, text=text.strip(), bg='black', fg='white', font=("Courier", 12), justify=tk.LEFT)
        lbl.pack(padx=20, pady=20)
        
        self.bind("<Escape>", lambda e: self._close())
        self.bind("q", lambda e: self._close())
        self.focus_set()
        
    def _close(self):
        parent = self.master
        self.destroy()
        parent.focus_set()
