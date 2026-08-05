import os
import sys
import customtkinter as ctk

from src.theme import applyThemeToTitlebar
from src.app import createVpcfColorEditorApp


def get_resource_path(relative_path):
    if hasattr(sys, '_MEIPASS'):
        return os.path.join(sys._MEIPASS, relative_path)
    return os.path.join(os.path.abspath("."), relative_path)


def main():
    start_dir = sys.argv[1] if len(sys.argv) > 1 else os.getcwd()
    start_dir = os.path.abspath(start_dir)
    if not os.path.isdir(start_dir):
        print(f"Folder not found: {start_dir}")
        sys.exit(1)

    ctk.set_widget_scaling(1.1)
    ctk.set_window_scaling(1)

    ctk.set_appearance_mode("dark")
    ctk.set_default_color_theme("dark-blue")

    root = ctk.CTk()

    icon_path = get_resource_path("icon.ico")
    try:
        root.iconbitmap(icon_path)
    except Exception:
        pass

    root.title("VPCF Editor")
    root.geometry("1200x700")
    root.minsize(760, 480)

    app_state = createVpcfColorEditorApp(root, start_dir)

    applyThemeToTitlebar(root)
    root.mainloop()


if __name__ == "__main__":
    main()
