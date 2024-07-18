import tkinter as tk
from tkinter import font as tkfont
import ctypes

# Disable Windows key and Print Screen key
def disable_windows_key():
    user32 = ctypes.WinDLL('user32', use_last_error=True)
    MOD_NOREPEAT = 0x4000
    user32.RegisterHotKey(None, 1, MOD_NOREPEAT, 0x5B)  # 0x5B is the virtual-key code for the left Windows key
    user32.RegisterHotKey(None, 2, MOD_NOREPEAT, 0x5C)  # 0x5C is the virtual-key code for the right Windows key
    user32.RegisterHotKey(None, 3, MOD_NOREPEAT, 0x2C)  # 0x2C is the virtual-key code for Print Screen key

def enable_windows_key():
    user32 = ctypes.WinDLL('user32', use_last_error=True)
    user32.UnregisterHotKey(None, 1)
    user32.UnregisterHotKey(None, 2)
    user32.UnregisterHotKey(None, 3)

disable_windows_key()

# Define the application class
class App(tk.Tk):
    def __init__(self):
        super().__init__()

        # Set up full screen window
        self.attributes('-fullscreen', True)
        self.configure(bg='black')
        self.bind("<Escape>", self.quit_app)
        self.bind("<Control-q>", self.quit_app)
        
        # Set up text widget
        self.text_widget = tk.Text(self, bg='black', fg='light blue', insertbackground='light blue', font=tkfont.Font(size=120), wrap=tk.WORD)
        self.text_widget.pack(expand=True, fill=tk.BOTH)
        self.text_widget.focus_set()
        self.text_widget.bind("<Key>", self.on_key_press)
        self.text_widget.bind("<Return>", self.on_enter_press)
        self.text_widget.bind("<Delete>", lambda e: "break")
        self.text_widget.bind("<Print>", lambda e: "break")

        # Override some key bindings to prevent default behavior
        self.text_widget.bind("<Control-Key>", self.disable_ctrl_keys)
        self.text_widget.bind("<Alt-Key>", self.disable_alt_keys)
        self.text_widget.bind("<Tab>", lambda e: "break")

    def on_key_press(self, event):
        if event.keysym in ["Shift_L", "Shift_R", "Caps_Lock"]:
            return
        if event.keysym in ["Left", "Right", "Up", "Down"]:
            return
        if event.keysym in ["F1", "F2", "F3", "F4", "F5", "F6", "F7", "F8", "F9", "F10", "F11", "F12", "Insert", "Delete", "Home", "End", "Page_Up", "Page_Down"]:
            self.text_widget.insert(tk.INSERT, event.keysym.upper())
            return "break"

    def on_enter_press(self, event):
        self.text_widget.insert(tk.INSERT, "\n\n")
        return "break"

    def disable_ctrl_keys(self, event):
        return "break"

    def disable_alt_keys(self, event):
        return "break"

    def quit_app(self, event=None):
        enable_windows_key()
        self.destroy()

# Create and run the application
app = App()
app.mainloop()
