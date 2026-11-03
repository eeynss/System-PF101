# Glassmorphism helpers shared by every screen, in PSAU colors (green and gold).
#
# Tkinter cannot blur things or make a widget see-through, so we fake the glass look
# with Pillow (PIL), a picture library:
#   1. Paint a soft green / gold / sky background picture (make_background).
#   2. For each card, blur the part of the picture behind it and mix in white (add_glass).
#   3. Paste the PSAU logos into the picture (paste_logo).
#   4. Show the picture on a Canvas (show_image) and draw text and buttons on top.
#      Canvas text has no background box, so it sits right on the glass.

import itertools
import os
import tkinter as tk
from tkinter import font as tkfont
from PIL import Image, ImageDraw, ImageFilter, ImageTk

# PSAU color system.
PSAU_GREEN = "#0b6a12"      # seal green: main buttons, focus ring
GREEN_HOVER = "#138a1d"
PSAU_GOLD = "#f5b400"       # seal gold: highlights and selected items
TEXT = "#0f3d1c"            # dark green text
MUTED = "#4a6b52"           # soft green-gray text
ON_GREEN = "#ffffff"        # text on green buttons
DANGER = "#c62828"
SUCCESS = "#0b6a12"
ERROR = "#b3261e"
BACKGROUND = "#e6f2e8"
FONT = "Segoe UI"
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
INK = (15, 61, 28)          # TEXT as (r, g, b), used to darken colors
ASSETS = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets")

# Background: four corner colors, plus big blurry color "blobs" (x, y, size, color).
CORNER_COLORS = [(232, 244, 233), (252, 246, 220), (220, 238, 226), (238, 247, 232)]
BLOBS = [
    (0.10, 0.15, 0.55, (34, 139, 34)),      # green
    (0.90, 0.10, 0.45, (245, 180, 0)),      # gold
    (0.80, 0.92, 0.55, (11, 106, 18)),      # deep PSAU green
    (0.22, 0.95, 0.40, (110, 170, 230)),    # sky blue
    (0.55, 0.45, 0.30, (250, 215, 90)),     # light gold
]

# A "box" everywhere in this program = (x0, y0, x1, y1) in pixels:
#   x0, y0 = its top-left corner, x1, y1 = its bottom-right corner (0, 0 is the top-left of the window).

saved_pictures = {}         # backgrounds and logos already made, so we don't make them twice
button_numbers = itertools.count()
fonts = {}


# ---------- colors ----------

# Mix two (r, g, b) colors. amount 0 = all first color, 1 = all second color.
def mix(first, second, amount):
    return tuple(int(a + (b - a) * amount) for a, b in zip(first, second))


def to_hex(color):
    return "#%02x%02x%02x" % color


def to_rgb(hex_color):
    return tuple(int(hex_color[i:i + 2], 16) for i in (1, 3, 5))


# A darker version of a glass color, used for lines (amount 0 = same, 1 = dark green).
def shade(card_color, amount):
    return to_hex(mix(card_color, INK, amount))


# Average color of one area of the picture.
def average(image, box):
    return image.crop(tuple(int(v) for v in box)).resize((1, 1), Image.Resampling.BOX).getpixel((0, 0))


# Colors for a light "ghost" button drawn on top of a glass card.
def ghost_colors(card_color):
    return {"fill": to_hex(mix(card_color, WHITE, 0.45)), "hover": to_hex(mix(card_color, WHITE, 0.80)),
            "outline": shade(card_color, 0.25)}


# ---------- the glass picture ----------

def make_background(width, height):
    if (width, height) not in saved_pictures:
        # Paint it small (fast), blur it, then stretch it to the window size.
        small_width, small_height = max(width // 4, 8), max(height // 4, 8)
        corners = Image.new("RGB", (2, 2))
        corners.putdata(CORNER_COLORS)
        picture = corners.resize((small_width, small_height), Image.Resampling.BILINEAR).convert("RGBA")
        blobs = Image.new("RGBA", (small_width, small_height), (0, 0, 0, 0))
        size = min(small_width, small_height)
        for x, y, radius, color in BLOBS:
            x, y, radius = x * small_width, y * small_height, radius * size
            ImageDraw.Draw(blobs).ellipse((x - radius, y - radius, x + radius, y + radius), fill=color + (170,))
        picture = Image.alpha_composite(picture, blobs.filter(ImageFilter.GaussianBlur(size // 5)))
        if len(saved_pictures) > 12:
            saved_pictures.clear()
        saved_pictures[(width, height)] = picture.convert("RGB").resize((width, height), Image.Resampling.BICUBIC)
    return saved_pictures[(width, height)].copy()


# Turn one rectangle of the picture into frosted glass.
# tint = the color mixed in (white for normal cards, PSAU green for the login's brand panel).
def add_glass(image, box, radius=22, whiteness=0.55, tint=WHITE, shadow=True):
    x0, y0, x1, y1 = [int(v) for v in box]
    # 1. Blur what is behind the card and mix in the tint color = frosted glass.
    behind = image.crop((x0, y0, x1, y1)).filter(ImageFilter.GaussianBlur(14))
    frosted = Image.blend(behind, Image.new("RGB", behind.size, tint), whiteness)
    # 2. Soft green shadow a little below the card.
    if shadow:
        area = (max(x0 - 26, 0), max(y0 - 26, 0), min(x1 + 26, image.width), min(y1 + 26, image.height))
        mask = Image.new("L", (area[2] - area[0], area[3] - area[1]), 0)
        ImageDraw.Draw(mask).rounded_rectangle((x0 - area[0], y0 - area[1] + 10, x1 - area[0], y1 - area[1] + 10),
                                               radius, fill=55)
        image.paste(INK, area, mask.filter(ImageFilter.GaussianBlur(14)))
    # 3. Paste the frosted card with rounded corners and a thin light border.
    mask = Image.new("L", frosted.size, 0)
    ImageDraw.Draw(mask).rounded_rectangle((0, 0, x1 - x0 - 1, y1 - y0 - 1), radius, fill=255)
    image.paste(frosted, (x0, y0), mask)
    ImageDraw.Draw(image).rounded_rectangle((x0, y0, x1 - 1, y1 - 1), radius,
                                            outline=to_hex(mix(average(image, box), WHITE, 0.7)))


# Draw a text-box background on the glass. Returns its color so the Entry can match it.
def add_field(image, box, radius=10):
    fill = mix(average(image, box), WHITE, 0.60)
    ImageDraw.Draw(image).rounded_rectangle([int(v) for v in box], radius, fill=fill,
                                            outline=to_hex(mix(fill, INK, 0.23)))
    return to_hex(fill)


# Paste a logo from the assets folder into the picture. Returns its width.
def paste_logo(image, name, x, y, height):
    if (name, height) not in saved_pictures:
        logo = Image.open(os.path.join(ASSETS, name)).convert("RGBA")
        width = round(logo.width * height / logo.height)
        saved_pictures[(name, height)] = logo.resize((width, height), Image.Resampling.LANCZOS)
    logo = saved_pictures[(name, height)]
    image.paste(logo, (int(x), int(y)), logo)
    return logo.width


# Use the PSAU seal as the window icon (top-left corner and taskbar).
def set_window_icon(window):
    seal = Image.open(os.path.join(ASSETS, "psau_seal.png")).convert("RGBA").resize((64, 64))
    window.icon = ImageTk.PhotoImage(seal)
    window.iconphoto(True, window.icon)


# Clear the canvas and put the finished picture behind everything.
def show_image(canvas, image):
    canvas.delete("all")
    canvas.photo = ImageTk.PhotoImage(image)    # keep a reference, or Tkinter forgets the picture
    canvas.create_image(0, 0, image=canvas.photo, anchor="nw")


# Run function after ms milliseconds. Calling again before then restarts the wait,
# so typing or resizing only triggers it once the user pauses.
def later(widget, name, ms, function):
    if not hasattr(widget, "jobs"):
        widget.jobs = {}
    if name in widget.jobs:
        widget.after_cancel(widget.jobs[name])
    widget.jobs[name] = widget.after(ms, function)


# ---------- things drawn on the canvas ----------

def label(canvas, x, y, text, size=10, color=TEXT, bold=False, anchor="w", **options):
    return canvas.create_text(x, y, text=text, anchor=anchor, fill=color,
                              font=(FONT, size, "bold" if bold else "normal"), **options)


def round_rect(canvas, x0, y0, x1, y1, radius, **options):
    points = [x0 + radius, y0, x1 - radius, y0, x1, y0, x1, y0 + radius,
              x1, y1 - radius, x1, y1, x1 - radius, y1, x0 + radius, y1,
              x0, y1, x0, y1 - radius, x0, y0 + radius, x0, y0]
    return canvas.create_polygon(points, smooth=True, **options)


# Make everything with this tag clickable, with a hand cursor on hover.
# on_enter / on_leave (optional) also run when the mouse goes in / out, e.g. to change a color.
def clickable(canvas, tag, command, on_enter=None, on_leave=None):
    canvas.tag_bind(tag, "<Button-1>", lambda event: command())
    canvas.tag_bind(tag, "<Enter>", lambda event: (canvas.config(cursor="hand2"), on_enter and on_enter()))
    canvas.tag_bind(tag, "<Leave>", lambda event: (canvas.config(cursor=""), on_leave and on_leave()))


# A rounded button made of a shape + text. command=None makes a button you cannot click.
def button(canvas, box, text, command, fill, hover, text_color=TEXT, outline="", size=10, tags=()):
    x0, y0, x1, y1 = box
    tag = "button" + str(next(button_numbers))
    shape = round_rect(canvas, x0, y0, x1, y1, min(10, (y1 - y0) / 2), fill=fill, outline=outline,
                       tags=(tag,) + tuple(tags))
    canvas.create_text((x0 + x1) / 2, (y0 + y1) / 2, text=text, fill=text_color, font=(FONT, size, "bold"),
                       tags=(tag,) + tuple(tags))
    if command is not None:
        clickable(canvas, tag, command, lambda: canvas.itemconfig(shape, fill=hover),
                  lambda: canvas.itemconfig(shape, fill=fill))


# Green button with white text, for the main action.
def primary_button(canvas, box, text, command, tags=(), size=10):
    button(canvas, box, text, command, PSAU_GREEN, GREEN_HOVER, ON_GREEN, tags=tags, size=size)


def ghost_button(canvas, box, text, command, card_color, tags=(), size=10):
    colors = ghost_colors(card_color)
    button(canvas, box, text, command, colors["fill"], colors["hover"], TEXT, colors["outline"], size, tags)


# Red-outlined button, for Delete.
def danger_button(canvas, box, text, command, card_color, tags=(), size=10):
    button(canvas, box, text, command, to_hex(mix(card_color, WHITE, 0.45)), to_hex(mix(to_rgb(DANGER), WHITE, 0.82)),
           DANGER, DANGER, size, tags)


# A button tinted with its own color (category buttons). selected = filled with the color.
def color_button(canvas, box, text, command, color, selected, tags=()):
    if selected:
        button(canvas, box, text, command, to_hex(color), to_hex(mix(color, WHITE, 0.15)), ON_GREEN,
               to_hex(color), 9, tags)
    else:
        button(canvas, box, text, command, to_hex(mix(WHITE, color, 0.12)), to_hex(mix(WHITE, color, 0.28)),
               to_hex(mix(color, BLACK, 0.30)), to_hex(mix(WHITE, color, 0.45)), 9, tags)


# A small rounded colored label (categories and stock in the table).
def pill(canvas, x, y, text, color, centered=True, outline=False, tags=()):
    font = (FONT, 9, "bold")
    width = text_width(text, font) + 20
    left = x - width / 2 if centered else x
    round_rect(canvas, left, y - 12, left + width, y + 12, 12, fill=to_hex(mix(WHITE, color, 0.17)),
               outline=to_hex(color) if outline else "", tags=tags)
    canvas.create_text(left + width / 2, y, text=text, font=font, fill=to_hex(mix(color, BLACK, 0.4)), tags=tags)


# A check box made of a small square, a check mark, and a label.
def checkbox(canvas, x, y, text, checked, command, card_color):
    colors = ghost_colors(card_color)
    round_rect(canvas, x, y - 9, x + 18, y + 9, 5, fill=colors["fill"], outline=colors["outline"], tags="checkbox")
    label(canvas, x + 9, y, "✓" if checked else "", bold=True, anchor="center", tags="checkbox")
    label(canvas, x + 28, y, text, color=MUTED, tags="checkbox")
    clickable(canvas, "checkbox", command)


# A text box that blends into the glass. Its ring lights up green while you type in it.
def make_entry(canvas, ring_tag, show=""):
    entry = tk.Entry(canvas, relief="flat", bd=0, highlightthickness=0, fg=TEXT, insertbackground=TEXT,
                     selectbackground=PSAU_GREEN, selectforeground=ON_GREEN, font=(FONT, 11), show=show)
    entry.bind("<FocusIn>", lambda event: canvas.itemconfig(ring_tag, outline=PSAU_GREEN))
    entry.bind("<FocusOut>", lambda event: canvas.itemconfig(ring_tag, outline=""))
    return entry


# Put an Entry inside a field drawn by add_field, with its focus ring around it.
def place_entry(canvas, entry, box, color, ring_tag):
    x0, y0, x1, y1 = box
    round_rect(canvas, x0 - 2, y0 - 2, x1 + 2, y1 + 2, 12, fill="", width=2, tags=ring_tag,
               outline=PSAU_GREEN if canvas.focus_get() is entry else "")
    entry.config(bg=color)
    canvas.create_window(x0 + 12, (y0 + y1) / 2, window=entry, anchor="w", width=x1 - x0 - 24, height=y1 - y0 - 8)


# Width of a text in pixels, used to size buttons and labels.
def text_width(text, font):
    if font not in fonts:
        fonts[font] = tkfont.Font(font=font)
    return fonts[font].measure(text)


# Cut a long text and add "…" so it fits in a column.
def fit_text(text, font, width):
    if text_width(text, font) <= width:
        return text
    while text and text_width(text + "…", font) > width:
        text = text[:-1]
    return text + "…"
