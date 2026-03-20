import tkinter as tk

HELP_TEXT = """
╔─── keybindings ──────────────────╗
│  GLOBAL                          │
│  ?         help                  │
│  /         search                │
│  c / C     purge thumbnail cache │
│  x         purge entire cache    │
│                                  │
│  GRID VIEW                       │
│  h j k l   navigate              │
│  Enter     open image            │
│  Space     select                │
│  A         select all            │
│  U         deselect all          │
│  y         copy selected         │
│  d         delete selected       │
│  b         set as wallpaper      │
│                                  │
│  IMAGE VIEW                      │
│  q         back to grid          │
│  i o       zoom in/out           │
│  u         reset zoom            │
│  w a s d   pan image (zoom)      │
│  ↑ ↓       pan up/down (zoom)    │
│  h l       prev/next             │
│  y         copy image            │
│  b         set as wallpaper      │
│                                  │
│                   Esc to close   │
╚──────────────────────────────────╝
"""


class HelpOverlay(tk.Frame):
    def __init__(self, parent):
        super().__init__(parent, bg='black', highlightbackground="white", highlightcolor="white", highlightthickness=1)

        lbl = tk.Label(self, text=HELP_TEXT.strip(), bg='black', fg='white', font=("Courier", 12), justify=tk.LEFT)
        lbl.pack(padx=20, pady=20)
        
        self.bind("<Escape>", lambda e: self._close())
        self.bind("q", lambda e: self._close())
        self.focus_set()
        
    def _close(self):
        parent = self.master
        self.destroy()
        parent.focus_set()
