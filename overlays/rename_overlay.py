import tkinter as tk


class RenameOverlay(tk.Frame):
    def __init__(self, parent_view, app, image_index):
        super().__init__(
            parent_view,
            bg='#1a1a1a',
            bd=1,
            relief=tk.SOLID,
            highlightbackground='#333333',
            highlightthickness=1,
        )
        self.app = app
        self.parent_view = parent_view
        self.image_index = image_index
        self.current_path = self.app.images[image_index]

        self.label = tk.Label(
            self,
            text="Rename file",
            fg='white',
            bg='#1a1a1a',
            font=('Courier', 14),
        )
        self.label.pack(padx=20, pady=(14, 8))

        self.entry = tk.Entry(
            self,
            width=48,
            bg='black',
            fg='white',
            insertbackground='white',
            relief='flat',
            font=('Courier', 13),
        )
        self.entry.pack(padx=20, pady=4)
        self.entry.insert(0, self.current_path.name)
        self.entry.select_range(0, tk.END)
        self.entry.icursor(tk.END)

        self.hint = tk.Label(
            self,
            text="Enter to save, Esc to cancel",
            fg='#bbbbbb',
            bg='#1a1a1a',
            font=('Courier', 11),
        )
        self.hint.pack(padx=20, pady=(8, 14))

        self._bind_keys()
        self.after_idle(self._focus_entry)

    def _bind_keys(self):
        self.bind("<Escape>", lambda e: self._cancel())
        self.entry.bind("<Escape>", lambda e: self._cancel())
        self.bind("<Return>", lambda e: self._submit())
        self.entry.bind("<Return>", lambda e: self._submit())

        for key in ["<space>", "<Left>", "<Right>", "<Up>", "<Down>", "h", "j", "k", "l", "d", "r", "y", "b", "q", "/"]:
            self.bind(key, lambda e: "break")

    def _focus_entry(self):
        self.entry.focus_set()
        self.entry.select_range(0, tk.END)

    def _submit(self):
        success, message, renamed_path = self.app.rename_image(self.image_index, self.entry.get())
        self.app._show_toast(message, duration_ms=3000 if success else 3500)
        if not success:
            self._focus_entry()
            return

        if hasattr(self.app, 'thumb_view_instance'):
            self.app.thumb_view_instance.on_image_renamed(self.image_index, renamed_path)
        if hasattr(self.app, 'image_view_instance') and self.app.image_view_instance:
            self.app.image_view_instance.on_image_renamed(self.image_index, renamed_path)

        self._close()

    def _cancel(self):
        self._close()

    def _close(self):
        self.destroy()
        self.parent_view.focus_set()
