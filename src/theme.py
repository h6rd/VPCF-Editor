import sys
import tkinter as tk
from tkinter import ttk

try:
    import pywinstyles
except ImportError:
    pywinstyles = None


BG = "#141218"
BG_PANEL = "#1d1b20"
BG_CARD = "#211f26"
BG_ELEV = "#2b2930"
BG_ELEV_HOVER = "#36343b"
BORDER = "#49454f"
ACCENT = "#d0bcff"
ACCENT_HOVER = "#c8b0ff"
ACCENT_ACTIVE = "#b190ff"
FG = "#e6e0e9"
FG_MUTED = "#cac4d0"
DANGER = "#ffb4ab"
DANGER_HOVER = "#ffcdc7"
SUCCESS = "#4fd18b"
ON_ACCENT = "#220a32"

FONT_FAMILY = "Segoe UI"
FONT_NORMAL = (FONT_FAMILY, 10)
FONT_BOLD = (FONT_FAMILY, 10, "bold")
FONT_TITLE = (FONT_FAMILY, 12, "bold")
FONT_SMALL = (FONT_FAMILY, 8)

CHANNEL_COLORS = {"R": DANGER, "G": SUCCESS, "B": ACCENT, "A": FG_MUTED}


def applyThemeToTitlebar(root):
    if sys.platform != "win32" or pywinstyles is None:
        return

    version = sys.getwindowsversion()
    is_dark = True

    if version.major == 10 and version.build >= 22000:
        pywinstyles.change_header_color(root, "#1c1d26")
    elif version.major == 10:
        pywinstyles.apply_style(root, "dark" if is_dark else "normal")
        root.wm_attributes("-alpha", 0.99)
        root.wm_attributes("-alpha", 1)


def setupDarkStyle(root: tk.Tk) -> ttk.Style:
    root.configure(bg=BG)
    root.option_add("*Font", FONT_NORMAL)

    style = ttk.Style(root)
    try:
        style.theme_use("clam")
    except tk.TclError:
        pass

    style.configure(".", background=BG, foreground=FG, font=FONT_NORMAL)
    style.configure("TFrame", background=BG)
    style.configure("Panel.TFrame", background=BG_PANEL)
    style.configure("Card.TFrame", background=BG_CARD)
    style.configure("TLabel", background=BG, foreground=FG)
    style.configure("Panel.TLabel", background=BG_PANEL, foreground=FG)
    style.configure("Muted.TLabel", background=BG, foreground=FG_MUTED)
    style.configure("Title.TLabel", background=BG,
                    foreground=FG, font=FONT_TITLE)
    style.configure("SectionTitle.TLabel", background=BG,
                    foreground=FG_MUTED, font=FONT_BOLD)

    style.configure("TButton", background=BG_ELEV, foreground=FG, borderwidth=0,
                    focusthickness=0, focuscolor=BG_ELEV, padding=(12, 7), font=FONT_NORMAL)
    style.map("TButton", background=[("disabled", BG_PANEL), ("active", BG_ELEV_HOVER)],
              foreground=[("disabled", FG_MUTED)])

    style.configure("Accent.TButton", background=ACCENT,
                    foreground=ON_ACCENT, font=FONT_BOLD)
    style.map("Accent.TButton",
              background=[("disabled", BG_PANEL), ("active",
                                                   ACCENT_HOVER), ("pressed", ACCENT_ACTIVE)],
              foreground=[("disabled", FG_MUTED)])

    style.configure("Danger.TButton", background=BG_ELEV, foreground=DANGER)
    style.map("Danger.TButton", background=[("disabled", BG_PANEL), ("active", "#3a2020")],
              foreground=[("disabled", FG_MUTED), ("active", DANGER_HOVER)])

    style.configure("TEntry", fieldbackground=BG_ELEV,
                    foreground=FG, insertcolor=FG, borderwidth=0, padding=6)
    style.map("TEntry", fieldbackground=[
              ("readonly", BG_PANEL)], foreground=[("readonly", FG_MUTED)])

    style.configure("TSpinbox", fieldbackground=BG_ELEV, background=BG_ELEV, foreground=FG,
                    arrowcolor=FG_MUTED, borderwidth=0, padding=4, insertcolor=FG)
    style.map("TSpinbox", fieldbackground=[("readonly", BG_ELEV)])

    style.configure("Treeview", background=BG_PANEL, fieldbackground=BG_PANEL, foreground=FG,
                    borderwidth=0, rowheight=26, font=FONT_NORMAL)
    style.map("Treeview", background=[("selected", ACCENT)], foreground=[
              ("selected", ON_ACCENT)])
    style.configure("Treeview.Heading", background=BG_PANEL,
                    foreground=FG_MUTED, borderwidth=0)

    style.configure("TPanedwindow", background=BG)
    style.configure("Sash", sashthickness=6, background=BG)

    style.configure("Vertical.TScrollbar", background=BG_ELEV, troughcolor=BG_PANEL,
                    bordercolor=BG_PANEL, arrowcolor=FG_MUTED, relief="flat", arrowsize=12)
    style.map("Vertical.TScrollbar", background=[("active", ACCENT)])
    return style
