import tkinter as tk
from tkinter import messagebox
import database
import glass
from glass import label, MUTED
from password_utils import new_salt, hash_password, password_matches

# CHANGE PASSWORD WINDOW. Opened from the products screen.
WIDTH, HEIGHT = 440, 420
LABELS = ["Current password", "New password", "Confirm new password"]


def show(root, user_id):
    window = tk.Toplevel(root)
    window.title("Change Password")
    window.resizable(False, False)
    window.transient(root)
    window.grab_set()       # finish this window first before going back
    x = root.winfo_rootx() + (root.winfo_width() - WIDTH) // 2
    y = root.winfo_rooty() + (root.winfo_height() - HEIGHT) // 2
    window.geometry(str(WIDTH) + "x" + str(HEIGHT) + "+" + str(x) + "+" + str(y))
    canvas = tk.Canvas(window, width=WIDTH, height=HEIGHT, bg=glass.BACKGROUND, highlightthickness=0, bd=0)
    canvas.pack()

    # Glass picture: one card with three text boxes.
    image = glass.make_background(WIDTH, HEIGHT)
    glass.add_glass(image, (18, 18, WIDTH - 18, HEIGHT - 18))
    boxes = [(44, 120 + row * 66, WIDTH - 44, 156 + row * 66) for row in range(3)]
    colors = [glass.add_field(image, box) for box in boxes]
    card_color = glass.average(image, (18, 18, WIDTH - 18, HEIGHT - 18))
    glass.show_image(canvas, image)

    label(canvas, 44, 54, "Change password", 17, bold=True)
    label(canvas, 44, 82, "The new password needs 6 to 128 characters.", 9, MUTED)
    text_boxes = []
    for row in range(3):
        label(canvas, 44, boxes[row][1] - 12, LABELS[row])
        text_boxes.append(glass.make_entry(canvas, "ring" + str(row), show="•"))
        glass.place_entry(canvas, text_boxes[row], boxes[row], colors[row], "ring" + str(row))
    label(canvas, 44, 312, "", 9, glass.ERROR, tags="message")

    def save_password():
        old_password, new_password, confirm = [entry.get() for entry in text_boxes]
        if not 6 <= len(new_password) <= 128 or new_password.strip() == "":
            return canvas.itemconfig("message", text="Use 6 to 128 characters.")
        if new_password != confirm:
            return canvas.itemconfig("message", text="The new passwords do not match.")
        # SQL: get this user's saved salt and hash, to check the current password.
        saved_salt, saved_hash = database.run_sql("SELECT password_salt, password_hash FROM users "
                                                  "WHERE user_id = %s", (user_id,), "one")
        if not password_matches(old_password, saved_salt, saved_hash):
            return canvas.itemconfig("message", text="The current password is incorrect.")

        # SQL: change this user's row only (WHERE user_id = %s) to the new salt and hash.
        new_salt_value = new_salt()     # a new random salt every time the password changes
        database.run_sql("UPDATE users SET password_salt = %s, password_hash = %s WHERE user_id = %s",
                         (new_salt_value, hash_password(new_password, new_salt_value), user_id))
        messagebox.showinfo("Success", "Password changed successfully.", parent=window)
        window.destroy()

    glass.primary_button(canvas, (44, 334, 216, 374), "Save password", save_password)
    glass.ghost_button(canvas, (226, 334, WIDTH - 44, 374), "Cancel", window.destroy, card_color)
    # Enter moves to the next box; Enter on the last box saves. Escape closes.
    text_boxes[0].bind("<Return>", lambda event: text_boxes[1].focus_set())
    text_boxes[1].bind("<Return>", lambda event: text_boxes[2].focus_set())
    text_boxes[2].bind("<Return>", lambda event: save_password())
    window.bind("<Escape>", lambda event: window.destroy())
    text_boxes[0].focus_set()
    return window
