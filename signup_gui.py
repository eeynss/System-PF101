import re
import database
import glass
import login_gui
from glass import label, MUTED
from password_utils import new_salt, hash_password

# SIGN-UP SCREEN. show() is called from app.py when "Create one" is clicked on the login screen.
# It uses the same card as the login screen (login_gui.paint_card).
canvas = None
text_boxes = {}
password_visible = False
callbacks = {}

# The 3 text boxes: (box name, label above it, rule shown on the right of the label).
SIGNUP_BOXES = [
    ("username", "Username", "3–30 letters, numbers, _ or ."),
    ("password", "Password", "at least 6 characters"),
    ("confirm", "Confirm password", ""),
]


def show(parent, on_created, on_back):
    global canvas, password_visible
    callbacks.update(created=on_created, back=on_back)
    password_visible = False
    canvas = login_gui.new_screen(parent, render)
    for key, text, rule in SIGNUP_BOXES:
        text_boxes[key] = glass.make_entry(canvas, "ring_" + key, show="" if key == "username" else "•")
    # Enter moves to the next box; Enter on the last box creates the account.
    text_boxes["username"].bind("<Return>", lambda event: text_boxes["password"].focus_set())
    text_boxes["password"].bind("<Return>", lambda event: text_boxes["confirm"].focus_set())
    text_boxes["confirm"].bind("<Return>", lambda event: create_account())
    text_boxes["username"].focus_set()


def render():
    card = login_gui.paint_card(canvas, [136, 202, 268])
    if card is None:
        return
    x0, y0, left, boxes, colors, card_color = card
    label(canvas, left, y0 + 56, "Create account", 24, bold=True)
    label(canvas, left, y0 + 90, "Sign up to use the PSAU Inventory Manager.", color=MUTED)
    for (key, text, rule), box, color in zip(SIGNUP_BOXES, boxes, colors):
        label(canvas, left, box[1] - 12, text)
        label(canvas, box[2], box[1] - 12, rule, 9, MUTED, anchor="e")
        glass.place_entry(canvas, text_boxes[key], box, color, "ring_" + key)
    glass.checkbox(canvas, left, y0 + 329, "Show passwords", password_visible, toggle_password, card_color)
    label(canvas, left, y0 + 360, "", color=glass.ERROR, tags="message")
    glass.primary_button(canvas, (left, y0 + 380, boxes[0][2], y0 + 424), "Create account", create_account, size=11)
    login_gui.draw_link(canvas, left, y0 + 456, "Already have an account?", "Sign in", lambda: callbacks["back"]())


def toggle_password():
    global password_visible
    password_visible = not password_visible
    for key in ("password", "confirm"):
        text_boxes[key].config(show="" if password_visible else "•")
    render()


# Show a problem in red and put the cursor in the box to fix.
def show_error(text, key):
    canvas.itemconfig("message", text=text)
    text_boxes[key].focus_set()


# CREATE (users table): check the form, then INSERT the new account with a hashed password.
def create_account():
    username = text_boxes["username"].get().strip()
    password, confirm = text_boxes["password"].get(), text_boxes["confirm"].get()
    if re.match(r"^[A-Za-z0-9_.]{3,30}$", username) is None:
        return show_error("Username: 3 to 30 letters, numbers, _ or . only.", "username")
    if not 6 <= len(password) <= 128 or password.strip() == "":
        return show_error("Password: use 6 to 128 characters.", "password")
    if password != confirm:
        text_boxes["confirm"].delete(0, "end")
        return show_error("The passwords do not match.", "confirm")
    # SQL: is there already an account with this username? (None = no, the name is free)
    existing_user = database.run_sql("SELECT user_id FROM users WHERE username = %s", (username,), "one")
    if existing_user is not None:
        return show_error("That username is already taken.", "username")

    # SQL: add the new account as a new row in the users table.
    # We save only the salt and the hash, never the password itself.
    salt = new_salt()
    database.run_sql("INSERT INTO users (username, password_salt, password_hash) VALUES (%s, %s, %s)",
                     (username, salt, hash_password(password, salt)))
    callbacks["created"](username)       # back to the login screen, username filled in
