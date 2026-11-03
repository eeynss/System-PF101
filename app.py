import traceback
import tkinter as tk
from tkinter import messagebox
import mysql.connector
import database
import glass
import login_gui
import signup_gui
import products_gui

# START FILE. Run "python app.py" (not the other files).
# app.py makes the one window and switches between the login, sign-up, and products screens.
root = None


def clear_window():
    for widget in root.winfo_children():
        widget.destroy()
    for key in ("<Control-n>", "<Control-f>", "<MouseWheel>"):    # products-screen shortcuts
        root.unbind(key)


def show_login(username="", notice=""):
    clear_window()
    login_gui.show(root, show_products, close_app, show_signup, username, notice)


def show_signup():
    clear_window()
    signup_gui.show(root, lambda username: show_login(username, "Account created. Enter your password to sign in."),
                    show_login)


def show_products(user):          # user = (user_id, username) from a successful login
    clear_window()
    products_gui.show(root, user, show_login)


def close_app():
    if messagebox.askyesno("Exit", "Close the Inventory Manager?"):
        root.destroy()


# Every error inside a button or key action comes here, so the screens need no try/except.
def show_error(error_type, error, trace):
    traceback.print_exception(error_type, error, trace)
    if isinstance(error, mysql.connector.Error):
        messagebox.showerror("Database error", "Check MySQL and the settings in database.py.\n\n" + str(error))
    else:
        messagebox.showerror("Error", str(error))


def create_app():
    global root
    root = tk.Tk()
    root.title("PSAU Inventory Manager")
    root.geometry("1280x760")
    root.minsize(1100, 680)
    root.configure(bg=glass.BACKGROUND)
    glass.set_window_icon(root)       # PSAU seal as the window icon
    root.state("zoomed")              # start maximized
    root.report_callback_exception = show_error
    root.protocol("WM_DELETE_WINDOW", close_app)
    # F11 = full screen on/off, Esc = leave full screen.
    root.bind("<F11>", lambda event: root.attributes("-fullscreen", not root.attributes("-fullscreen")))
    root.bind("<Escape>", lambda event: root.attributes("-fullscreen", False))
    show_login()


if __name__ == "__main__":
    try:
        database.setup_database()
    except mysql.connector.Error as error:
        messagebox.showerror("MySQL connection error",
                             "Check that MySQL is running and the settings in database.py are correct.\n\n" + str(error))
    else:
        create_app()
        root.mainloop()
