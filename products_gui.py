import csv
import math
import re
import tkinter as tk
from tkinter import messagebox, filedialog
import database
import glass
import password_gui
from glass import label, FONT, TEXT, MUTED, WHITE, PSAU_GREEN, PSAU_GOLD

# PRODUCTS SCREEN: the table on the left (Read, Update, Delete) and the add form on the right (Create).
# show() is called from app.py after a successful login.
#
# Every product row from MySQL comes in this order:
#     (id, code, name, category, price, quantity)
# for example (5, "BEV-002", "C2 Green Tea Apple 500ml", "Beverages", 30.00, 5)

LOW_STOCK = 10                  # this many pieces or fewer = "low on stock"
ROW_HEIGHT = 44                 # height of one table row, in pixels
CATEGORY_ROW_HEIGHT = 28        # height of one row of category buttons, in pixels

# Ready-made store categories: name -> (code prefix, color as (red, green, blue)).
# The order here is the order of the buttons.
PRESET_CATEGORIES = {
    "Snacks": ("SNK", (234, 88, 12)),            # orange
    "Beverages": ("BEV", (37, 99, 235)),         # blue
    "Personal Care": ("HYG", (13, 148, 136)),    # teal: toothpaste, toothbrush, soap, shampoo
    "Canned Goods": ("CAN", (190, 24, 93)),      # rose
    "Noodles": ("NDL", (202, 138, 4)),           # amber
    "Household": ("HSE", (71, 85, 105)),         # slate: detergent, dishwashing liquid, tissue
    "Rice & Grains": ("RIC", (146, 64, 14)),     # brown
    "Condiments": ("CON", (124, 58, 237)),       # purple
    "School Supplies": ("SCH", (79, 70, 229)),   # indigo
}
# Colors for categories the user types in (not in the list above).
EXTRA_COLORS = [(8, 145, 178), (77, 124, 15), (219, 39, 119), (21, 128, 61), (147, 51, 234), (2, 132, 199)]

# Table columns work like Tkinter's grid: (column name, heading, minimum width, weight, text alignment).
# Every column gets its minimum width; the space left over is shared by weight (0 = never grows).
# Alignment: "w" = left, "e" = right, "center" = middle.
COLUMNS = [
    ("id", "ID", 46, 0, "center"),
    ("code", "Code", 86, 0, "center"),
    ("name", "Product Name", 130, 4, "w"),
    ("category", "Category", 118, 1, "w"),
    ("price", "Price", 84, 1, "e"),
    ("quantity", "Stock", 108, 0, "center"),
    ("action", "Action", 124, 0, "center"),
]
HIDE_WHEN_NARROW = ("id", "code")       # hidden first when the window is too narrow

# The 5 boxes of the add form: (box name, label above it). Enter moves through them in this order.
FORM_FIELDS = [("name", "Product name"), ("category", "Category"), ("price", "Price (₱)"),
               ("quantity", "Quantity"), ("code", "Product code")]

# Checked before saving: (box name, pattern the typed text must match, message if it does not).
# How to read a pattern:  ^ = start   $ = end   \d = a digit   {1,7} = 1 to 7 of them   ? = optional
INPUT_RULES = [
    ("price", r"^\d{1,8}(\.\d{1,2})?$", "Enter a price like 25 or 19.75."),
    ("quantity", r"^\d{1,7}$", "Quantity must be a whole number from 0 up."),
    ("code", r"^[A-Z0-9-]{2,20}$", "Code: letters, numbers, and dashes only (example: SNK-001)."),
]

# ---------- variables the whole screen shares ----------
root = None                     # the main window
canvas = None                   # the drawing area that fills the window
user = None                     # who is signed in: (user_id, username)
on_logout = None                # function from app.py that goes back to the login screen
text_boxes = {}                 # the Entry boxes: "search", "name", "category", "price", "quantity", "code"
positions = {}                  # where everything is drawn (worked out by render())

products = []                   # the product rows shown on the current page
used_categories = []            # categories already used in the products table, most used first
matching_count = 0              # how many products match the search
rows_to_skip = 0                # how many rows come before this page (for OFFSET)
totals = (0, 0, 0)              # (number of products, how many low on stock, inventory value in pesos)

sort_column = "id"              # which column the table is sorted by
sort_descending = True          # True = biggest first (so the newest product is on top)
current_page = 1
rows_per_page = 8               # changes with the window height
total_pages = 1

editing_product_id = None       # None = adding a new product; a number = the ID of the product being edited
auto_fill_code = True           # True until the user types their own product code
form_message = ("", MUTED)      # (text, color) shown under the form


# ---------- small helpers ----------

# Badge text and color for a stock quantity: green = OK, yellow = low, red = none left.
def stock_badge(quantity):
    if quantity == 0:
        return "Out of stock", (220, 38, 38)
    if quantity <= LOW_STOCK:
        return str(quantity) + " pcs (low)", (230, 160, 0)
    return str(quantity) + " pcs", (11, 140, 30)


# Each category gets its own color. The same name always gets the same color.
def category_color(category):
    for preset_name, (prefix, color) in PRESET_CATEGORIES.items():
        if preset_name.lower() == category.lower():
            return color
    # Not a ready-made category: add up the letter codes of the name, then pick a color with % (remainder).
    letter_total = sum(ord(letter) for letter in category.lower())
    return EXTRA_COLORS[letter_total % len(EXTRA_COLORS)]


# Money with a peso sign and two decimals: 1234.5 -> ₱1,234.50
def peso(amount):
    return "₱" + format(amount, ",.2f")


# Replace the text inside one of the boxes.
def set_text(box_name, new_text):
    text_boxes[box_name].delete(0, "end")
    text_boxes[box_name].insert(0, str(new_text))


def screen_is_open():
    return canvas is not None and canvas.winfo_exists()


# ---------- building the screen ----------

def show(parent, logged_in_user, logout_callback):
    global root, canvas, user, on_logout, editing_product_id, auto_fill_code, form_message, current_page
    root, user, on_logout = parent, logged_in_user, logout_callback
    editing_product_id, auto_fill_code, form_message, current_page = None, True, ("", MUTED), 1
    canvas = tk.Canvas(root, bg=glass.BACKGROUND, highlightthickness=0, bd=0)
    canvas.pack(fill="both", expand=True)

    # Make the text boxes. Search runs 0.3 seconds after the user stops typing.
    text_boxes["search"] = glass.make_entry(canvas, "ring_search")
    text_boxes["search"].bind("<KeyRelease>", lambda event: glass.later(canvas, "search", 300, run_search))
    for box_name, label_text in FORM_FIELDS:
        text_boxes[box_name] = glass.make_entry(canvas, "ring_" + box_name)
        text_boxes[box_name].bind("<Return>", lambda event, name=box_name: go_to_next_box(name))
    text_boxes["category"].bind("<KeyRelease>", category_changed)
    text_boxes["code"].bind("<Key>", code_typed)

    # Redraw when the window changes size, plus keyboard and mouse-wheel shortcuts.
    canvas.bind("<Configure>", lambda event: glass.later(canvas, "render", 60, render))
    root.bind("<MouseWheel>", mouse_wheel)
    root.bind("<Control-n>", lambda event: new_product())
    root.bind("<Control-f>", lambda event: text_boxes["search"].focus_set())
    text_boxes["name"].focus_set()


# Paint the glass picture for the current window size, then draw everything on it.
# A box is (left, top, right, bottom) in pixels from the top-left corner of the window.
def render():
    global rows_per_page
    if not screen_is_open() or canvas.winfo_width() < 300:
        return
    width, height = canvas.winfo_width(), canvas.winfo_height()
    form_width = 360 if width >= 1300 else 320      # small window = narrower form, more room for the table
    top_bar = (24, 14, width - 24, 66)
    table_card = (24, 80, width - 40 - form_width, height - 20)
    form_card = (width - 24 - form_width, 80, width - 24, height - 20)
    search_width = max(140, min(240, table_card[2] - table_card[0] - 420))
    search_box = (table_card[2] - 160 - search_width, 106, table_card[2] - 160, 142)
    form_boxes = place_form_boxes(form_card)

    # 1. The picture: background, three glass cards, logos, and the text-box backgrounds.
    image = glass.make_background(width, height)
    for card in (top_bar, table_card, form_card):
        glass.add_glass(image, card)
    glass.paste_logo(image, "psau_seal.png", 38, 20, 40)
    brand_end_x = 88 + glass.paste_logo(image, "psau_wordmark.png", 88, 29, 22)
    box_colors = {box_name: glass.add_field(image, box) for box_name, box in form_boxes.items()}
    box_colors["search"] = glass.add_field(image, search_box)
    positions.update(top_bar=top_bar, table_card=table_card, form_card=form_card, form_width=form_width,
                     top_bar_color=glass.average(image, top_bar), table_card_color=glass.average(image, table_card),
                     form_card_color=glass.average(image, form_card))
    glass.show_image(canvas, image)
    canvas.config(cursor="")

    # 2. Top bar: PSAU brand on the left, account buttons on the right.
    middle_y, right = 40, top_bar[2]
    canvas.create_line(brand_end_x + 12, middle_y - 13, brand_end_x + 12, middle_y + 13, fill=PSAU_GOLD, width=2)
    label(canvas, brand_end_x + 24, middle_y, "Inventory Manager", 14, bold=True)
    title_width = glass.text_width("Inventory Manager", (FONT, 14, "bold"))
    label(canvas, brand_end_x + 40 + title_width, middle_y, "Products", 11, MUTED)
    glass.ghost_button(canvas, (right - 112, middle_y - 16, right - 16, middle_y + 16), "Log out", on_logout,
                       positions["top_bar_color"])
    glass.ghost_button(canvas, (right - 276, middle_y - 16, right - 124, middle_y + 16), "Change password",
                       lambda: password_gui.show(root, user[0]), positions["top_bar_color"])
    label(canvas, right - 292, middle_y, "Signed in as " + user[1], color=MUTED, anchor="e")

    # 3. The table card and the form card.
    draw_table_card(search_box, box_colors["search"])
    draw_form(form_boxes, box_colors)
    rows_per_page = max(3, (positions["rows_bottom"] - positions["rows_top"]) // ROW_HEIGHT)   # rows that fit
    load_products()


def draw_table_card(search_box, search_color):
    left, top, right, bottom = positions["table_card"]
    label(canvas, left + 28, top + 36, "Products", 20, bold=True)
    label(canvas, left + 28, top + 66, "", color=MUTED, tags="totals")
    label(canvas, search_box[0] - 10, top + 44, "Search", color=MUTED, anchor="e")
    glass.place_entry(canvas, text_boxes["search"], search_box, search_color, "ring_search")
    glass.ghost_button(canvas, (right - 148, top + 26, right - 28, top + 62), "Export CSV", export_to_csv,
                       positions["table_card_color"])

    # Column positions, like grid's minsize and weight. Too narrow? Hide ID, then Code.
    table_left, table_right = left + 24, right - 24
    available_width = table_right - table_left
    shown_columns = list(COLUMNS)
    for column_name in HIDE_WHEN_NARROW:
        if sum(column[2] for column in shown_columns) > available_width:
            shown_columns = [column for column in shown_columns if column[0] != column_name]
    extra_width = max(0, available_width - sum(column[2] for column in shown_columns))
    total_weight = sum(column[3] for column in shown_columns)
    columns = []
    x = table_left
    for column_name, heading, minimum_width, weight, align in shown_columns:
        column_width = minimum_width + extra_width * weight / total_weight
        columns.append((column_name, heading, x, column_width, align))
        x += column_width
    positions.update(columns=columns, table_left=table_left, table_right=table_right, headings_y=top + 100,
                     rows_top=top + 120, rows_bottom=bottom - 58)


# Work out where each box of the form goes, top to bottom.
def place_form_boxes(form_card):
    left, top, right, bottom = form_card
    box_left, box_right = left + 24, right - 24
    # Category buttons get as many rows as the panel height allows (1 to 4).
    # The rest of the form needs about 526 pixels; whatever is left is for the buttons.
    positions["max_category_rows"] = max(1, min(4, (bottom - top - 526) // CATEGORY_ROW_HEIGHT))
    positions["category_rows"] = len(arrange_category_buttons(box_left, box_right, positions["max_category_rows"])[0])
    y = top + 80
    form_boxes = {}
    for box_name, label_text in FORM_FIELDS:
        positions["label_" + box_name] = y
        this_box_right = box_right - 84 if box_name == "quantity" else box_right     # room for − and +
        form_boxes[box_name] = (box_left, y + 20, this_box_right, y + 54)
        y += 62
        if box_name == "category":
            positions["category_buttons_top"] = y - 4          # category buttons go under Category
            y += positions["category_rows"] * CATEGORY_ROW_HEIGHT + 2
    positions["form_boxes_end"] = y
    return form_boxes


def draw_form(form_boxes, box_colors):
    left, top, right, bottom = positions["form_card"]
    label(canvas, left + 24, top + 32, "", 17, bold=True, tags="form_title")
    label(canvas, left + 24, top + 58, "Press Enter to jump to the next box.", 9, MUTED)
    for box_name, label_text in FORM_FIELDS:
        label(canvas, left + 24, positions["label_" + box_name] + 8, label_text)
        glass.place_entry(canvas, text_boxes[box_name], form_boxes[box_name], box_colors[box_name], "ring_" + box_name)
    label(canvas, right - 24, positions["label_code"] + 8, "", 9, MUTED, anchor="e", tags="code_hint")
    label(canvas, right - 24, positions["label_category"] + 8, "click one below, or type a new one", 9, MUTED,
          anchor="e")
    qty_left, qty_top, qty_right, qty_bottom = form_boxes["quantity"]
    glass.ghost_button(canvas, (qty_right + 8, qty_top, qty_right + 42, qty_bottom), "−",
                       lambda: change_quantity(-1), positions["form_card_color"], size=13)
    glass.ghost_button(canvas, (qty_right + 50, qty_top, qty_right + 84, qty_bottom), "+",
                       lambda: change_quantity(1), positions["form_card_color"], size=13)
    label(canvas, left + 24, positions["form_boxes_end"] + 10, form_message[0], color=form_message[1],
          tags="form_message", width=positions["form_width"] - 48)
    draw_form_buttons()


# Title and buttons change between "adding" and "editing".
def draw_form_buttons():
    canvas.delete("form_buttons")
    left, top, right, bottom = positions["form_card"]
    y = positions["form_boxes_end"] + 30
    adding = editing_product_id is None
    canvas.itemconfig("form_title", text="New product" if adding else "Edit product #" + str(editing_product_id))
    canvas.itemconfig("code_hint", text="filled in for you" if adding else "")
    glass.primary_button(canvas, (left + 24, y, right - 24, y + 42), "Add product" if adding else "Save changes",
                         save_product, tags=("form_buttons",), size=11)
    glass.ghost_button(canvas, (left + 24, y + 50, right - 24, y + 86), "Clear form" if adding else "Cancel edit",
                       new_product, positions["form_card_color"], tags=("form_buttons",))


def show_form_message(text, color=MUTED):
    global form_message
    form_message = (text, color)
    canvas.itemconfig("form_message", text=text, fill=color)


# ---------- READ: get products from MySQL and draw the table ----------

# Make the WHERE part of the SQL for the search box.
# LIKE '%bev%' means "contains bev anywhere". It checks the code, the name, OR the category.
def make_search_filter(search_text):
    if search_text == "":
        return "", ()                    # empty search box = no filter = all products
    pattern = "%" + search_text + "%"
    return " WHERE code LIKE %s OR name LIKE %s OR category LIKE %s", (pattern, pattern, pattern)


# READ: get one page of products, the totals, and the used categories from MySQL.
def load_products():
    global products, used_categories, matching_count, rows_to_skip, totals, current_page, total_pages
    if not screen_is_open() or "columns" not in positions:
        return
    search_filter, search_values = make_search_filter(text_boxes["search"].get().strip())
    # ORDER BY = sort the rows. ASC = smallest first, DESC = biggest first.
    order = " ORDER BY " + sort_column + (" DESC" if sort_descending else " ASC") + ", id DESC"

    # SQL 1: COUNT(*) = how many products match the search. We need it to know how many pages there are.
    matching_count = database.run_sql("SELECT COUNT(*) FROM products" + search_filter, search_values, "one")[0]
    total_pages = max(1, math.ceil(matching_count / rows_per_page))
    current_page = min(current_page, total_pages)
    rows_to_skip = (current_page - 1) * rows_per_page

    # SQL 2: get only the products for this page.
    # LIMIT = how many rows to get. OFFSET = how many rows to skip first (page 2 skips page 1's rows).
    products = database.run_sql("SELECT id, code, name, category, price, quantity FROM products" + search_filter
                                + order + " LIMIT %s OFFSET %s", search_values + (rows_per_page, rows_to_skip), "all")

    # SQL 3: the totals under "Products".
    #   COUNT(*)              = how many products
    #   SUM(quantity <= 10)   = how many are low on stock (each "yes" counts as 1)
    #   SUM(price * quantity) = total peso value of everything in stock
    #   COALESCE(..., 0)      = use 0 when the table is empty
    totals = database.run_sql("SELECT COUNT(*), COALESCE(SUM(quantity <= %s), 0), COALESCE(SUM(price * quantity), 0)"
                              " FROM products", (LOW_STOCK,), "one")

    # SQL 4: the category names already used, most used first (for the category buttons).
    # GROUP BY category = put rows with the same category together, so each name comes once.
    category_rows = database.run_sql("SELECT category FROM products GROUP BY category "
                                     "ORDER BY COUNT(*) DESC, category LIMIT 12", (), "all")
    used_categories = [row[0] for row in category_rows]

    product_count, low_stock_count, inventory_value = totals
    canvas.itemconfig("totals", text=str(product_count) + " products  ·  " + str(int(low_stock_count)) +
                      " low on stock  ·  Inventory value " + peso(inventory_value))
    draw_table()
    draw_category_buttons()


# Where text goes inside a column: 8 pixels from the left, 8 pixels from the right, or the middle.
def column_text_x(column_x, column_width, align):
    if align == "w":
        return column_x + 8
    if align == "e":
        return column_x + column_width - 8
    return column_x + column_width / 2


def draw_table():
    canvas.delete("table")
    canvas.config(cursor="")
    card_color = positions["table_card_color"]
    table_left, table_right = positions["table_left"], positions["table_right"]

    # Headings. Click one to sort by it; the arrow shows the direction.
    for column_name, heading, column_x, column_width, align in positions["columns"]:
        arrow = ("  ▼" if sort_descending else "  ▲") if column_name == sort_column else ""
        heading_tag = "heading_" + column_name
        label(canvas, column_text_x(column_x, column_width, align), positions["headings_y"], heading + arrow,
              bold=True, anchor=align, tags=("table", heading_tag))
        if column_name != "action":
            glass.clickable(canvas, heading_tag, lambda name=column_name: sort_by(name))
    canvas.create_line(table_left, positions["headings_y"] + 16, table_right, positions["headings_y"] + 16,
                       fill=PSAU_GREEN, width=2, tags="table")
    if len(products) == 0:
        empty_text = "No products match your search." if totals[0] else "No products yet.\nUse the form on the right."
        label(canvas, (table_left + table_right) / 2, positions["rows_top"] + 90, empty_text, 12, MUTED,
              anchor="center", justify="center", tags="table")

    # One row per product.
    for row_number, product in enumerate(products):
        product_id, code, name, category, price, quantity = product      # give each value a name
        row_top = positions["rows_top"] + row_number * ROW_HEIGHT
        row_middle = row_top + ROW_HEIGHT / 2
        if product_id == editing_product_id:          # the row being edited is highlighted in gold
            glass.round_rect(canvas, table_left - 8, row_top + 3, table_right + 8, row_top + ROW_HEIGHT - 3, 10,
                             outline="", fill=glass.to_hex(glass.mix(card_color, glass.to_rgb(PSAU_GOLD), 0.35)),
                             tags="table")
        for column_name, heading, column_x, column_width, align in positions["columns"]:
            if column_name == "quantity":
                badge_text, badge_color = stock_badge(quantity)
                glass.pill(canvas, column_x + column_width / 2, row_middle, badge_text, badge_color, outline=True,
                           tags="table")
            elif column_name == "category":
                short_category = glass.fit_text(category, (FONT, 9, "bold"), column_width - 36)
                glass.pill(canvas, column_x + 8, row_middle, short_category, category_color(category),
                           centered=False, tags="table")
            elif column_name == "action":
                center_x = column_x + column_width / 2
                # p=product makes each button remember ITS OWN row.
                glass.ghost_button(canvas, (center_x - 58, row_middle - 14, center_x - 6, row_middle + 14), "Edit",
                                   lambda p=product: edit_product(p), card_color, tags=("table",), size=9)
                glass.danger_button(canvas, (center_x, row_middle - 14, center_x + 58, row_middle + 14), "Delete",
                                    lambda p=product: delete_product(p), card_color, tags=("table",), size=9)
            else:
                cell_text = {"id": str(product_id), "code": code, "name": name, "price": peso(price)}[column_name]
                label(canvas, column_text_x(column_x, column_width, align), row_middle,
                      glass.fit_text(cell_text, (FONT, 11), column_width - 16), 11, anchor=align, tags="table")
        if row_number < len(products) - 1:          # a thin line between rows
            canvas.create_line(table_left, row_top + ROW_HEIGHT, table_right, row_top + ROW_HEIGHT,
                               fill=glass.shade(card_color, 0.12), tags="table")
    draw_page_buttons(card_color)


# "Showing 1 to 9 of 15 entries" and the page buttons: « ‹ 1 2 3 › »
def draw_page_buttons(card_color):
    y = positions["table_card"][3] - 30
    first_shown = rows_to_skip + 1 if matching_count else 0
    last_shown = rows_to_skip + len(products)
    info = "Showing " + str(first_shown) + " to " + str(last_shown) + " of " + str(matching_count) + " entries"
    if matching_count != totals[0]:
        info += " (filtered from " + str(totals[0]) + " total)"
    label(canvas, positions["table_left"], y, info, color=MUTED, tags="table")

    # The buttons: (text, page it opens, can it be clicked?)
    first_number = max(1, min(current_page - 2, total_pages - 4))
    last_number = min(total_pages, first_number + 4)
    buttons = [("«", 1, current_page > 1), ("‹", current_page - 1, current_page > 1)]
    buttons += [(str(page), page, page != current_page) for page in range(first_number, last_number + 1)]
    buttons += [("›", current_page + 1, current_page < total_pages), ("»", total_pages, current_page < total_pages)]
    x = positions["table_right"] - len(buttons) * 34 + 4
    for text, page, can_click in buttons:
        box = (x, y - 15, x + 30, y + 15)
        if text == str(current_page):           # the page we're on: green
            glass.button(canvas, box, text, None, PSAU_GREEN, PSAU_GREEN, glass.ON_GREEN, size=9, tags=("table",))
        elif can_click:
            glass.ghost_button(canvas, box, text, lambda p=page: go_to_page(p), card_color, tags=("table",), size=9)
        else:                                   # greyed out, cannot be clicked
            faded = glass.ghost_colors(card_color)["fill"]
            glass.button(canvas, box, text, None, faded, faded, glass.shade(card_color, 0.30), size=9, tags=("table",))
        x += 34


# Click a heading to sort by it. Click the same heading again to reverse the order.
def sort_by(column_name):
    global sort_column, sort_descending, current_page
    if column_name == sort_column:
        sort_descending = not sort_descending
    else:
        sort_descending = False
    sort_column, current_page = column_name, 1
    load_products()


def go_to_page(page):
    global current_page
    current_page = page
    load_products()


# Mouse wheel over the table = next / previous page.
def mouse_wheel(event):
    if not screen_is_open():
        return
    left, top, right, bottom = positions["table_card"]
    mouse_x, mouse_y = event.x_root - canvas.winfo_rootx(), event.y_root - canvas.winfo_rooty()
    if left <= mouse_x <= right and top <= mouse_y <= bottom:
        if event.delta < 0 and current_page < total_pages:
            go_to_page(current_page + 1)
        elif event.delta > 0 and current_page > 1:
            go_to_page(current_page - 1)


# A new search starts again from page 1.
def run_search():
    global current_page
    current_page = 1
    load_products()


# ---------- the add form: category buttons and product code ----------

# The names on the category buttons: the categories already used first, then the ready-made ones.
def category_button_names():
    used_lowercase = [name.lower() for name in used_categories]
    ready_made = [name for name in PRESET_CATEGORIES if name.lower() not in used_lowercase]
    return list(used_categories) + ready_made


# Put the category buttons into rows, like words in a sentence: if one doesn't fit, it goes to the next row.
# Returns (rows, hidden): rows = [[(name, x, width), ...], ...], hidden = names that did not fit.
def arrange_category_buttons(left, right, max_rows):
    font = (FONT, 9, "bold")
    rows = [[]]
    x = left
    for name in category_button_names():
        button_width = glass.text_width(name, font) + 22
        if x + button_width > right and len(rows[-1]) > 0:
            rows.append([])                      # no room: start a new row
            x = left
        rows[-1].append((name, x, button_width))
        x += button_width + 6
    hidden = [name for row in rows[max_rows:] for name, x, button_width in row]
    rows = rows[:max_rows]
    # Some did not fit: make room for a "+N more" button at the end of the last row.
    while hidden and rows[-1]:
        name, x, button_width = rows[-1][-1]
        more_width = glass.text_width("+" + str(len(hidden)) + " more", font) + 22
        if x + button_width + 6 + more_width <= right:
            break
        hidden.insert(0, rows[-1].pop()[0])
    return rows, hidden


# Category buttons: click one instead of typing the category.
def draw_category_buttons():
    canvas.delete("category_buttons")
    left, top, right, bottom = positions["form_card"]
    rows, hidden = arrange_category_buttons(left + 24, right - 24, positions["max_category_rows"])
    if len(rows) != positions["category_rows"]:
        glass.later(canvas, "render", 60, render)      # number of rows changed: redraw to make room
    typed_category = text_boxes["category"].get().strip().lower()
    for row_number, row in enumerate(rows):
        y = positions["category_buttons_top"] + row_number * CATEGORY_ROW_HEIGHT
        for category, x, button_width in row:
            is_selected = category.lower() == typed_category
            glass.color_button(canvas, (x, y, x + button_width, y + 24), category,
                               lambda c=category: pick_category(c), category_color(category), is_selected,
                               tags=("category_buttons",))
    if hidden:      # "+N more" opens a small menu with the categories that did not fit
        last_row = rows[-1]
        x = last_row[-1][1] + last_row[-1][2] + 6 if last_row else left + 24
        y = positions["category_buttons_top"] + (len(rows) - 1) * CATEGORY_ROW_HEIGHT
        text = "+" + str(len(hidden)) + " more"
        glass.ghost_button(canvas, (x, y, x + glass.text_width(text, (FONT, 9, "bold")) + 22, y + 24), text,
                           lambda: show_more_menu(hidden, x, y + 26), positions["form_card_color"],
                           tags=("category_buttons",), size=9)


def show_more_menu(category_names, x, y):
    menu = tk.Menu(canvas, tearoff=0, font=(FONT, 10), bg="#ffffff", activebackground=PSAU_GREEN,
                   activeforeground="#ffffff")
    for name in category_names:
        menu.add_command(label="●  " + name, command=lambda c=name: pick_category(c),
                         foreground=glass.to_hex(category_color(name)))
    menu.tk_popup(canvas.winfo_rootx() + int(x), canvas.winfo_rooty() + int(y))


def pick_category(category):
    set_text("category", category)
    draw_category_buttons()
    update_code_suggestion()
    text_boxes["price"].focus_set()


# Typing a category: highlight the matching button now, suggest a code after a short pause.
def category_changed(event=None):
    draw_category_buttons()
    glass.later(canvas, "code", 300, update_code_suggestion)


# Once the user types their own code, stop filling it in for them.
def code_typed(event):
    global auto_fill_code
    if event.char not in ("", "\t", "\r"):
        auto_fill_code = False


# Suggest the next free code for a category, like SNK-004 after SNK-003.
def suggest_code(category):
    # The prefix: ready-made categories have their own (Snacks -> SNK); others use their first 3 letters.
    preset_prefixes = {name.lower(): info[0] for name, info in PRESET_CATEGORIES.items()}
    letters_only = re.sub(r"[^A-Za-z]", "", category).upper()
    prefix = preset_prefixes.get(category.lower(), letters_only[:3])
    if len(prefix) < 2:
        prefix = "PRD"

    # SQL: does this category already have a product with a code like "XXX-001"? Then keep using that prefix.
    first_code_row = database.run_sql("SELECT code FROM products WHERE category = %s AND code LIKE %s "
                                      "ORDER BY id LIMIT 1", (category, "%-%"), "one")
    if first_code_row is not None:
        prefix = first_code_row[0].rsplit("-", 1)[0]        # "SNK-001" -> "SNK"

    # SQL: get every code that starts with this prefix, like SNK-001, SNK-002, SNK-003.
    code_rows = database.run_sql("SELECT code FROM products WHERE code LIKE %s", (prefix + "-%",), "all")
    code_numbers = []
    for (code,) in code_rows:
        number_part = code.rsplit("-", 1)[1]                # "SNK-003" -> "003"
        if number_part.isdigit():
            code_numbers.append(int(number_part))
    next_number = max(code_numbers, default=0) + 1          # biggest + 1 -> 4
    return prefix + "-" + str(next_number).zfill(3)          # zfill(3): 4 -> "004", so "SNK-004"


def update_code_suggestion():
    if screen_is_open() and auto_fill_code:
        category = text_boxes["category"].get().strip()
        set_text("code", suggest_code(category) if category != "" else "")


# Enter moves to the next box. Enter on the last box saves.
def go_to_next_box(box_name):
    box_order = [name for name, label_text in FORM_FIELDS]
    if box_name == box_order[-1]:
        save_product()
    else:
        next_box = box_order[box_order.index(box_name) + 1]
        text_boxes[next_box].focus_set()
    return "break"


# The − and + buttons next to Quantity.
def change_quantity(step):
    typed = text_boxes["quantity"].get().strip()
    current_quantity = int(typed) if typed.isdigit() else 0
    set_text("quantity", max(0, current_quantity + step))       # max(0, ...) = never below 0


# Empty the form. After adding, keep the category so the next product is faster to add.
def clear_form(keep_category=False):
    global editing_product_id, auto_fill_code
    editing_product_id, auto_fill_code = None, True
    category = text_boxes["category"].get().strip() if keep_category else ""
    for box_name, label_text in FORM_FIELDS:
        set_text(box_name, "")
    set_text("category", category)
    if category != "":
        update_code_suggestion()
    draw_form_buttons()
    text_boxes["name"].focus_set()


def new_product():
    clear_form()
    show_form_message("")
    draw_table()
    draw_category_buttons()


# Show a problem under the form and put the cursor in the box to fix.
def form_error(text, box_name):
    show_form_message(text, glass.ERROR)
    text_boxes[box_name].focus_set()


# ---------- CREATE, UPDATE, DELETE ----------

# Read the form boxes and put their values in a dictionary.
def read_product_form():
    values = {}
    for box_name, label_text in FORM_FIELDS:
        values[box_name] = text_boxes[box_name].get().strip()
    values["code"] = values["code"].upper()
    return values


# Check the form before sending anything to MySQL.
def validate_product_form(values):
    # Every box must have a value.
    for box_name, label_text in FORM_FIELDS:
        if values[box_name] == "":
            form_error("Please fill in " + label_text.lower() + ".", box_name)
            return False

    # Price, quantity, and code must match their rules above.
    for box_name, pattern, problem in INPUT_RULES:
        if re.match(pattern, values[box_name]) is None:
            form_error(problem, box_name)
            return False
    return True


# Save the values with INSERT for a new product, or UPDATE for the product being edited.
# Return True when adding, False when editing, and None if the code is already used.
def save_product_to_database(values):
    # Check for a duplicate code. During an edit, ignore the product's own ID.
    other_product = database.run_sql("SELECT id FROM products WHERE code = %s AND id <> %s",
                                     (values["code"], editing_product_id or 0), "one")
    if other_product is not None:
        form_error("The code " + values["code"] + " is already used by another product.", "code")
        return None

    # Put the form values in the same order as the %s placeholders in the SQL.
    product_values = (values["code"], values["name"], values["category"],
                      float(values["price"]), int(values["quantity"]))
    adding = editing_product_id is None
    if adding:
        # INSERT adds a new row to the products table.
        database.run_sql("INSERT INTO products (code, name, category, price, quantity) VALUES (%s, %s, %s, %s, %s)",
                         product_values)
    else:
        # UPDATE changes only the row with this ID.
        database.run_sql("UPDATE products SET code = %s, name = %s, category = %s, price = %s, quantity = %s "
                         "WHERE id = %s", product_values + (editing_product_id,))
    return adding

# Button function: read, check, save, then refresh the screen.
def save_product():
    values = read_product_form()
    if not validate_product_form(values):
        return

    adding = save_product_to_database(values)
    if adding is None:  # The duplicate-code check stopped the save.
        return

    # Clear the form, show a success message, and reload the product table.
    clear_form(keep_category=adding)
    action = "✓ Added " if adding else "✓ Saved changes to "
    show_form_message(action + values["name"], glass.SUCCESS)
    load_products()


# UPDATE (step 1): put the clicked product into the form.
def edit_product(product):
    global editing_product_id, auto_fill_code
    product_id, code, name, category, price, quantity = product
    editing_product_id = product_id          # remember WHICH product we are editing
    auto_fill_code = False                   # keep its own code
    set_text("name", name)
    set_text("category", category)
    set_text("price", price)
    set_text("quantity", quantity)
    set_text("code", code)
    show_form_message("Change what you need, then press Save changes.")
    draw_form_buttons()
    draw_table()
    draw_category_buttons()
    text_boxes["name"].focus_set()


# DELETE: remove the clicked product, after asking Yes / No.
def delete_product(product):
    product_id, code, name, category, price, quantity = product
    if messagebox.askyesno("Confirm delete", "Delete " + name + " (" + code + ")?", parent=root):
        # SQL: remove exactly one row: the product with this ID.
        database.run_sql("DELETE FROM products WHERE id = %s", (product_id,))
        if product_id == editing_product_id:
            clear_form()
        show_form_message("Deleted " + name + ".")
        load_products()


# Save every product that matches the current search to a CSV file (opens in Excel).
def export_to_csv():
    search_filter, search_values = make_search_filter(text_boxes["search"].get().strip())
    order = " ORDER BY " + sort_column + (" DESC" if sort_descending else " ASC")
    # SQL: get ALL matching products (no LIMIT, so not just one page).
    all_rows = database.run_sql("SELECT id, code, name, category, price, quantity FROM products" + search_filter
                                + order, search_values, "all")
    if len(all_rows) == 0:
        return messagebox.showinfo("Nothing to export", "There are no products to export.", parent=root)
    file_path = filedialog.asksaveasfilename(parent=root, defaultextension=".csv", initialfile="products.csv",
                                             filetypes=[("CSV files", "*.csv")])
    if file_path:
        with open(file_path, "w", newline="", encoding="utf-8-sig") as file:
            writer = csv.writer(file)
            writer.writerow([column[1] for column in COLUMNS if column[0] != "action"])    # the headings row
            writer.writerows(all_rows)                                                   # one line per product
        messagebox.showinfo("Export complete", "Saved " + str(len(all_rows)) + " product(s) to:\n" + file_path,
                            parent=root)


def logout():
    on_logout()
