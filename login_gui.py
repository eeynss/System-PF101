import tkinter as tk
import database
import glass
from glass import label, MUTED
from password_utils import password_matches

# LOGIN SCREEN. show() is called from app.py.
# paint_card() and draw_link() are also used by the sign-up screen, so both look the same.
canvas = None
username_entry = None
password_entry = None
password_visible = False
message = ("", glass.ERROR)          # (text, color) shown above the Sign in button
callbacks = {}


# username / notice are filled in after a new account is made on the sign-up screen.
def show(parent, on_success, on_exit, on_signup, username="", notice=""):
    global canvas, username_entry, password_entry, password_visible, message
    callbacks.update(success=on_success, exit=on_exit, signup=on_signup)
    password_visible = False
    message = (notice, glass.SUCCESS)
    canvas = new_screen(parent, render)
    username_entry = glass.make_entry(canvas, "ring_username")
    password_entry = glass.make_entry(canvas, "ring_password", show="•")
    # Enter in Username goes to Password; Enter in Password signs in.
    username_entry.bind("<Return>", lambda event: password_entry.focus_set())
    password_entry.bind("<Return>", lambda event: login())
    username_entry.insert(0, username)
    (password_entry if username else username_entry).focus_set()


def render():
    card = paint_card(canvas, [156, 236])
    if card is None:
        return
    x0, y0, left, boxes, colors, card_color = card
    right = boxes[0][2]
    label(canvas, left, y0 + 66, "Welcome back", 24, bold=True)
    label(canvas, left, y0 + 102, "Sign in to manage the store inventory.", color=MUTED)
    label(canvas, left, y0 + 142, "Username")
    glass.place_entry(canvas, username_entry, boxes[0], colors[0], "ring_username")
    label(canvas, left, y0 + 222, "Password")
    glass.place_entry(canvas, password_entry, boxes[1], colors[1], "ring_password")
    glass.checkbox(canvas, left, y0 + 301, "Show password", password_visible, toggle_password, card_color)
    label(canvas, left, y0 + 336, message[0], color=message[1], tags="message")
    glass.primary_button(canvas, (left, y0 + 360, right, y0 + 404), "Sign in", login, size=11)
    glass.ghost_button(canvas, (left, y0 + 416, right, y0 + 456), "Exit application", callbacks["exit"], card_color)
    draw_link(canvas, left, y0 + 478, "Don't have an account?", "Create one", callbacks["signup"])


def toggle_password():
    global password_visible
    password_visible = not password_visible
    password_entry.config(show="" if password_visible else "•")
    render()


# Show a message above the Sign in button (red = problem, green = good news).
def show_message(text, color=glass.ERROR):
    global message
    message = (text, color)
    canvas.itemconfig("message", text=text, fill=color)


# Check the typed username and password against the users table.
def login():
    typed_username = username_entry.get().strip()
    typed_password = password_entry.get()
    if typed_username == "" or typed_password == "":
        return show_message("Enter your username and password.")

    # SQL: find the account with this username. %s is a blank that MySQL fills with typed_username.
    # Answer: one row (user_id, username, salt, hash), or None if there is no such username.
    user_row = database.run_sql("SELECT user_id, username, password_salt, password_hash FROM users "
                                "WHERE username = %s", (typed_username,), "one")
    if user_row is not None:
        user_id, username, saved_salt, saved_hash = user_row      # give each value in the row a name
        if password_matches(typed_password, saved_salt, saved_hash):
            return callbacks["success"]((user_id, username))     # correct: open the products screen

    # Wrong username OR wrong password: the same message, so guessers learn nothing.
    password_entry.delete(0, "end")
    show_message("Incorrect username or password.")
    password_entry.focus_set()


# ---------- shared with the sign-up screen ----------

# A full-window canvas that redraws itself (render_function) after the window changes size.
def new_screen(parent, render_function):
    screen = tk.Canvas(parent, bg=glass.BACKGROUND, highlightthickness=0, bd=0)
    screen.pack(fill="both", expand=True)
    screen.bind("<Configure>", lambda event: glass.later(screen, "render", 60, render_function))
    return screen


# Paint the background, the glass card, the green PSAU panel, and text boxes at field_tops.
# Returns (x0, y0, left, boxes, colors, card_color) or None if the window is still too small.
def paint_card(screen, field_tops):
    width, height = screen.winfo_width(), screen.winfo_height()
    if width < 100 or height < 100:
        return None
    card_width = min(880, width - 40)
    x0, y0 = (width - card_width) // 2, (height - 500) // 2
    x1, y1 = x0 + card_width, y0 + 500
    left = x0 + 424                                        # the form starts here
    image = glass.make_background(width, height)
    glass.add_glass(image, (x0, y0, x1, y1), radius=26)
    # Green PSAU panel on the left: small seal + white PSAU lettering.
    glass.add_glass(image, (x0 + 12, y0 + 12, x0 + 372, y1 - 12), radius=20, whiteness=0.82,
                    tint=glass.to_rgb(glass.PSAU_GREEN), shadow=False)
    seal_width = glass.paste_logo(image, "psau_seal.png", x0 + 40, y0 + 40, 44)
    glass.paste_logo(image, "psau_wordmark_white.png", x0 + 50 + seal_width, y0 + 42, 40)
    boxes = [(left, y0 + top, x1 - 44, y0 + top + 38) for top in field_tops]
    colors = [glass.add_field(image, box) for box in boxes]
    card_color = glass.average(image, (left, y0, x1, y1))
    glass.show_image(screen, image)

    screen.create_line(x0 + 42, y0 + 96, x0 + 104, y0 + 96, fill=glass.PSAU_GOLD, width=3)
    label(screen, x0 + 40, y0 + 112, "PAMPANGA STATE AGRICULTURAL UNIVERSITY", 8, "#d7ecd9", bold=True)
    label(screen, x0 + 40, y0 + 202, "Inventory\nManager System", 26, "#ffffff", bold=True, anchor="nw")
    label(screen, x0 + 40, y0 + 312, "Products, prices,\nand every piece in stock.", 11, "#d7ecd9", anchor="nw")
    label(screen, x0 + 40, y1 - 40, "PSAU  ·  EST. 1885", 9, glass.PSAU_GOLD, bold=True)
    label(screen, width / 2, height - 22, "PSAU INVENTORY MANAGER     /     F11: Full screen     /     "
          "Esc: Window mode", 9, MUTED, anchor="center")
    return x0, y0, left, boxes, colors, card_color


# A clickable line like "Don't have an account? Create one".
def draw_link(screen, x, y, question, link_text, command):
    label(screen, x, y, question, color=MUTED)
    screen.create_text(x + glass.text_width(question, (glass.FONT, 10)) + 6, y, text=link_text, anchor="w",
                       fill=glass.PSAU_GREEN, font=(glass.FONT, 10, "bold underline"), tags="link")
    glass.clickable(screen, "link", command)
