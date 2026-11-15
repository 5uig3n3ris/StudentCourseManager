"""
COS201 PROGRAMMING I - MID-SEMESTER LAB ASSESSMENT
Student Course Management System (Mini-System)

A modern, dark-themed desktop GUI built with Python's standard library only
(tkinter) - no extra packages to install.

Run:  python course_manager.py
"""

import json
import re
import string
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

# --------------------------------------------------------------------------- #
#  Theme
# --------------------------------------------------------------------------- #
BG = "#0E1120"
SIDEBAR = "#141830"
CARD = "#1A1F3D"
CARD_2 = "#232954"
FIELD = "#10142A"
BORDER = "#2E3566"
ACCENT = "#6C7BFF"
ACCENT_HOVER = "#8793FF"
CYAN = "#22D3EE"
TEXT = "#EEF0FF"
MUTED = "#8E96BF"
OK = "#34D399"
ERR = "#F87171"
WARN = "#FBBF24"

FONT = "Segoe UI"
SEMESTER_TARGET = 24  # typical maximum semester load, used by the progress ring


# --------------------------------------------------------------------------- #
#  Custom exceptions (appropriate error handling)
# --------------------------------------------------------------------------- #
class InvalidInputError(Exception):
    """Raised when the user supplies invalid course data."""


class DuplicateCourseError(Exception):
    """Raised when a course code is already recorded."""


class CourseFileError(Exception):
    """Raised when a saved file is corrupted or in the wrong format."""


# --------------------------------------------------------------------------- #
#  Model: Course
# --------------------------------------------------------------------------- #
class Course:
    """A single course with a code, a title and a number of credit units."""

    CODE_PATTERN = re.compile(r"^[A-Z]{2,4}\d{3}$")
    MIN_UNITS, MAX_UNITS = 1, 6

    def __init__(self, code, title, units):
        self.code = code
        self.title = title
        self.units = units

    # ---- string processing / validation (trim, casing, regex) ----
    @staticmethod
    def clean_code(raw):
        code = re.sub(r"\s+", "", raw.strip()).upper()  # trim, remove spaces, upper-case
        if not code:
            raise InvalidInputError("Course code cannot be empty.")
        if not Course.CODE_PATTERN.match(code):
            raise InvalidInputError(
                "Course code must be 2-4 letters followed by 3 digits (e.g. COS201)."
            )
        return code

    @staticmethod
    def clean_title(raw):
        title = " ".join(raw.split())  # trim + collapse repeated spaces
        if not title:
            raise InvalidInputError("Course title cannot be empty.")
        if len(title) < 3 or len(title) > 60:
            raise InvalidInputError("Course title must be 3-60 characters long.")
        if not any(ch.isalpha() for ch in title):
            raise InvalidInputError("Course title must contain letters.")
        return string.capwords(title)  # Title Casing

    @staticmethod
    def clean_units(raw):
        text = str(raw).strip()
        if not text:
            raise InvalidInputError("Units cannot be empty.")
        if not text.isdigit():
            raise InvalidInputError("Units must be a whole number (e.g. 3).")
        units = int(text)
        if not Course.MIN_UNITS <= units <= Course.MAX_UNITS:
            raise InvalidInputError(
                f"Units must be between {Course.MIN_UNITS} and {Course.MAX_UNITS}."
            )
        return units

    @classmethod
    def create(cls, code, title, units):
        """Validate raw text and build a Course object."""
        return cls(cls.clean_code(code), cls.clean_title(title), cls.clean_units(units))

    def to_dict(self):
        return {"code": self.code, "title": self.title, "units": self.units}

    def __str__(self):
        return f"{self.code} - {self.title} ({self.units} units)"


# --------------------------------------------------------------------------- #
#  Model: CourseManager (internal structure + operations)
# --------------------------------------------------------------------------- #
class CourseManager:
    """Stores courses in a list and performs all operations on them."""

    def __init__(self):
        self.courses = []

    def add_course(self, course):
        if self.find_recursive(course.code) is not None:
            raise DuplicateCourseError(f"{course.code} has already been added.")
        self.courses.append(course)

    def remove_course(self, code):
        index = self.find_recursive(code)
        if index is None:
            raise InvalidInputError(f"{code} was not found.")
        del self.courses[index]

    # ---- RECURSIVE FEATURES ----
    def find_recursive(self, code, index=0):
        """Recursive linear search. Returns the position of the course or None."""
        if index >= len(self.courses):  # base case: end of the list
            return None
        if self.courses[index].code == code:  # base case: found
            return index
        return self.find_recursive(code, index + 1)  # recursive step

    def total_units_recursive(self, index=0):
        """Recursively add up the units of every course."""
        if index >= len(self.courses):
            return 0
        return self.courses[index].units + self.total_units_recursive(index + 1)

    # ---- queries ----
    def search(self, raw_code):
        """Return (position, course) for a code, raising errors for bad input."""
        code = Course.clean_code(raw_code)
        index = self.find_recursive(code)
        return (index, self.courses[index]) if index is not None else (None, code)

    def total_units(self):
        return self.total_units_recursive()

    def count(self):
        return len(self.courses)

    # ---- file handling ----
    def save(self, path):
        data = [course.to_dict() for course in self.courses]  # loop via comprehension
        with open(path, "w", encoding="utf-8") as file:
            json.dump({"app": "COS201 Course Manager", "courses": data}, file, indent=2)

    def load(self, path):
        """Load a file. The current list is replaced only if the whole file is valid."""
        try:
            with open(path, "r", encoding="utf-8") as file:
                payload = json.load(file)
            records = payload["courses"]
            loaded = CourseManager()
            for record in records:
                loaded.add_course(
                    Course.create(record["code"], record["title"], record["units"])
                )
        except json.JSONDecodeError:
            raise CourseFileError("That file is not valid JSON.")
        except (KeyError, TypeError):
            raise CourseFileError("That file is not a course list saved by this app.")
        except (InvalidInputError, DuplicateCourseError) as err:
            raise CourseFileError(f"The file contains bad data: {err}")
        self.courses = loaded.courses
        return len(self.courses)


# --------------------------------------------------------------------------- #
#  Custom widgets
# --------------------------------------------------------------------------- #
class RoundButton(tk.Canvas):
    """A flat, rounded, hover-aware button drawn on a canvas."""

    def __init__(self, parent, text, command, bg=ACCENT, hover=ACCENT_HOVER, fg="white",
                 width=170, height=44, radius=14, anchor="center", size=11, bold=True):
        super().__init__(parent, width=width, height=height, bg=parent["bg"],
                         highlightthickness=0, bd=0, cursor="hand2")
        self.command, self.bg, self.hover = command, bg, hover
        self.w, self.h, self.r = width, height, radius
        self.shape = self._round_rect(1, 1, width - 1, height - 1, radius, fill=bg)
        self.bar = self.create_rectangle(0, 10, 4, height - 10, fill=bg, outline="")
        weight = "bold" if bold else "normal"
        x = 20 if anchor == "w" else width / 2
        self.label = self.create_text(x, height / 2, text=text, fill=fg, anchor=anchor if anchor == "w" else "center",
                                      font=(FONT, size, weight))
        self.bind("<Enter>", lambda e: self.itemconfig(self.shape, fill=self.hover))
        self.bind("<Leave>", lambda e: self.itemconfig(self.shape, fill=self.bg))
        self.bind("<ButtonRelease-1>", lambda e: self.command())

    def _round_rect(self, x1, y1, x2, y2, r, **kw):
        pts = [x1 + r, y1, x2 - r, y1, x2, y1, x2, y1 + r, x2, y2 - r, x2, y2,
               x2 - r, y2, x1 + r, y2, x1, y2, x1, y2 - r, x1, y1 + r, x1, y1]
        return self.create_polygon(pts, smooth=True, outline="", **kw)

    def set_active(self, active):
        """Used by the sidebar to highlight the current page."""
        self.bg = CARD_2 if active else SIDEBAR
        self.itemconfig(self.shape, fill=self.bg)
        self.itemconfig(self.bar, fill=CYAN if active else self.bg)
        self.itemconfig(self.label, fill=TEXT if active else MUTED)


def make_field(parent, label, hint, variable, width=None):
    """Label + bordered entry (accent border on focus) + hint text."""
    wrap = tk.Frame(parent, bg=CARD)
    tk.Label(wrap, text=label, bg=CARD, fg=TEXT, font=(FONT, 10, "bold")).pack(anchor="w")
    box = tk.Frame(wrap, bg=BORDER, padx=1, pady=1)
    box.pack(fill="x", pady=(6, 4))
    entry = tk.Entry(box, textvariable=variable, bg=FIELD, fg=TEXT, insertbackground=CYAN,
                     relief="flat", bd=0, font=(FONT, 12), width=width or 20,
                     selectbackground=ACCENT)
    entry.pack(fill="x", ipady=10, ipadx=8)
    entry.bind("<FocusIn>", lambda e: box.config(bg=ACCENT))
    entry.bind("<FocusOut>", lambda e: box.config(bg=BORDER))
    tk.Label(wrap, text=hint, bg=CARD, fg=MUTED, font=(FONT, 9)).pack(anchor="w")
    return wrap, entry


# --------------------------------------------------------------------------- #
#  Application window
# --------------------------------------------------------------------------- #
class CourseApp(tk.Tk):
    MENU = [
        ("add", "01   Add Course"),
        ("view", "02   View All Courses"),
        ("search", "03   Search by Code"),
        ("total", "04   Compute Total Units"),
        ("save", "05   Save to File"),
        ("load", "06   Load from File"),
        ("exit", "07   Exit Program"),
    ]

    def __init__(self):
        super().__init__()
        self.title("COS201 - Student Course Manager")
        self.geometry("1120x720")
        self.minsize(980, 640)
        self.configure(bg=BG)

        self.manager = CourseManager()
        self.unsaved = False
        self.current = None
        self.nav = {}

        self._style_widgets()
        self._build_layout()
        self.protocol("WM_DELETE_WINDOW", self.exit_program)
        self.handle_menu("add")

    # ------------------------------------------------------------------ setup
    def _style_widgets(self):
        style = ttk.Style(self)
        style.theme_use("clam")
        style.configure("Treeview", background=CARD, fieldbackground=CARD, foreground=TEXT,
                        rowheight=42, borderwidth=0, font=(FONT, 11))
        style.configure("Treeview.Heading", background=CARD_2, foreground=MUTED, relief="flat",
                        font=(FONT, 10, "bold"), padding=(10, 10))
        style.map("Treeview", background=[("selected", ACCENT)], foreground=[("selected", "white")])
        style.map("Treeview.Heading", background=[("active", CARD_2)])
        style.configure("Vertical.TScrollbar", background=CARD_2, troughcolor=CARD,
                        bordercolor=CARD, arrowcolor=MUTED, lightcolor=CARD_2, darkcolor=CARD_2)

    def _build_layout(self):
        # Sidebar
        side = tk.Frame(self, bg=SIDEBAR, width=270)
        side.pack(side="left", fill="y")
        side.pack_propagate(False)

        brand = tk.Frame(side, bg=SIDEBAR)
        brand.pack(fill="x", padx=24, pady=(30, 26))
        logo = tk.Canvas(brand, width=46, height=46, bg=SIDEBAR, highlightthickness=0)
        logo.create_oval(2, 2, 44, 44, fill=ACCENT, outline="")
        logo.create_oval(14, 14, 32, 32, fill=CYAN, outline="")
        logo.pack(side="left")
        names = tk.Frame(brand, bg=SIDEBAR)
        names.pack(side="left", padx=12)
        tk.Label(names, text="CourseHub", bg=SIDEBAR, fg=TEXT, font=(FONT, 17, "bold")).pack(anchor="w")
        tk.Label(names, text="COS201 · Programming I", bg=SIDEBAR, fg=MUTED, font=(FONT, 9)).pack(anchor="w")

        tk.Label(side, text="MENU", bg=SIDEBAR, fg=MUTED, font=(FONT, 9, "bold")).pack(anchor="w", padx=28, pady=(0, 8))
        for key, label in self.MENU:
            btn = RoundButton(side, label, lambda k=key: self.handle_menu(k), bg=SIDEBAR,
                              hover=CARD, fg=MUTED, width=232, height=46, radius=12,
                              anchor="w", size=11, bold=False)
            btn.pack(padx=19, pady=2)
            btn.set_active(False)
            self.nav[key] = btn

        tk.Label(side, text="Mid-Semester Lab Assessment", bg=SIDEBAR, fg=MUTED,
                 font=(FONT, 8)).pack(side="bottom", pady=18)

        # Main area
        main = tk.Frame(self, bg=BG)
        main.pack(side="left", fill="both", expand=True)

        status = tk.Frame(main, bg=SIDEBAR, height=38)
        status.pack(side="bottom", fill="x")
        status.pack_propagate(False)
        self.status_left = tk.Label(status, bg=SIDEBAR, fg=MUTED, font=(FONT, 10))
        self.status_left.pack(side="left", padx=24)
        self.status_right = tk.Label(status, bg=SIDEBAR, font=(FONT, 10, "bold"))
        self.status_right.pack(side="right", padx=24)

        self.content = tk.Frame(main, bg=BG)
        self.content.pack(fill="both", expand=True, padx=40, pady=(32, 24))
        self.update_status()

    # -------------------------------------------------------- menu decisions
    def handle_menu(self, choice):
        """Logical decision-making for the seven menu operations."""
        if choice == "add":
            self.show_page("add", self.page_add)
        elif choice == "view":
            self.show_page("view", self.page_view)
        elif choice == "search":
            self.show_page("search", self.page_search)
        elif choice == "total":
            self.show_page("total", self.page_total)
        elif choice == "save":
            self.save_courses()
        elif choice == "load":
            self.load_courses()
        elif choice == "exit":
            self.exit_program()
        else:
            raise InvalidInputError(f"Unknown menu option: {choice}")

    def show_page(self, key, builder):
        self.current = key
        for child in self.content.winfo_children():  # loop: clear old page
            child.destroy()
        for name, btn in self.nav.items():  # loop: highlight active item
            btn.set_active(name == key)
        builder()

    # ---------------------------------------------------------------- helpers
    def header(self, title, subtitle):
        tk.Label(self.content, text=title, bg=BG, fg=TEXT, font=(FONT, 26, "bold")).pack(anchor="w")
        tk.Label(self.content, text=subtitle, bg=BG, fg=MUTED, font=(FONT, 11)).pack(anchor="w", pady=(2, 22))

    def card(self, parent=None, **pack):
        frame = tk.Frame(parent or self.content, bg=CARD, padx=28, pady=26,
                         highlightthickness=1, highlightbackground=BORDER)
        return frame

    def toast(self, message, kind="ok"):
        color = {"ok": OK, "err": ERR, "info": CYAN}[kind]
        box = tk.Frame(self, bg=CARD_2, highlightthickness=1, highlightbackground=BORDER)
        tk.Frame(box, bg=color, width=6).pack(side="left", fill="y")
        tk.Label(box, text=message, bg=CARD_2, fg=TEXT, font=(FONT, 11),
                 padx=16, pady=14, wraplength=340, justify="left").pack(side="left")
        box.place(relx=1.0, x=-24, y=22, anchor="ne")
        box.lift()
        self.after(3000, box.destroy)

    def update_status(self):
        self.status_left.config(
            text=f"{self.manager.count()} course(s)   ·   {self.manager.total_units()} unit(s)")
        if self.unsaved:
            self.status_right.config(text="● Unsaved changes", fg=WARN)
        else:
            self.status_right.config(text="● All changes saved", fg=OK)

    def mark_changed(self):
        self.unsaved = True
        self.update_status()

    # ------------------------------------------------------------- 01 ADD
    def page_add(self):
        self.header("Add Course", "Enter the details of a course you are taking this semester.")
        row = tk.Frame(self.content, bg=BG)
        row.pack(fill="both", expand=True)

        form = self.card(row)
        form.pack(side="left", fill="both", expand=True, padx=(0, 20))

        self.v_code, self.v_title, self.v_units = tk.StringVar(), tk.StringVar(), tk.StringVar()
        f1, e1 = make_field(form, "Course code", "2-4 letters + 3 digits, e.g. COS201", self.v_code)
        f2, e2 = make_field(form, "Course title", "e.g. Programming I", self.v_title)
        f3, e3 = make_field(form, "Credit units", f"Whole number from {Course.MIN_UNITS} to {Course.MAX_UNITS}", self.v_units)
        for f in (f1, f2, f3):
            f.pack(fill="x", pady=(0, 14))

        self.error_label = tk.Label(form, text="", bg=CARD, fg=ERR, font=(FONT, 10), wraplength=420, justify="left")
        self.error_label.pack(anchor="w", pady=(0, 8))

        buttons = tk.Frame(form, bg=CARD)
        buttons.pack(anchor="w")
        RoundButton(buttons, "Add Course", self.submit_course).pack(side="left")
        RoundButton(buttons, "Clear", self.clear_form, bg=CARD_2, hover=BORDER, width=110).pack(side="left", padx=12)
        for entry, nxt in ((e1, e2), (e2, e3)):
            entry.bind("<Return>", lambda ev, n=nxt: n.focus_set())
        e3.bind("<Return>", lambda ev: self.submit_course())
        e1.focus_set()

        # Live preview card
        prev = self.card(row)
        prev.pack(side="left", fill="y")
        prev.config(width=330)
        prev.pack_propagate(False)
        tk.Label(prev, text="LIVE PREVIEW", bg=CARD, fg=MUTED, font=(FONT, 9, "bold")).pack(anchor="w")
        self.pv_code = tk.Label(prev, bg=CARD, fg=CYAN, font=(FONT, 28, "bold"))
        self.pv_code.pack(anchor="w", pady=(24, 4))
        self.pv_title = tk.Label(prev, bg=CARD, fg=TEXT, font=(FONT, 14), wraplength=270, justify="left")
        self.pv_title.pack(anchor="w")
        self.pv_units = tk.Label(prev, bg=CARD_2, fg=TEXT, font=(FONT, 11, "bold"), padx=14, pady=6)
        self.pv_units.pack(anchor="w", pady=22)
        tk.Label(prev, text="Cleaned automatically:\ntrimmed, upper-cased code,\nTitle Cased name.",
                 bg=CARD, fg=MUTED, font=(FONT, 9), justify="left").pack(side="bottom", anchor="w")
        for var in (self.v_code, self.v_title, self.v_units):
            var.trace_add("write", lambda *a: self.refresh_preview())
        self.refresh_preview()

    def refresh_preview(self):
        try:
            code = Course.clean_code(self.v_code.get())
        except InvalidInputError:
            code = self.v_code.get().strip().upper() or "CODE000"
        try:
            title = Course.clean_title(self.v_title.get())
        except InvalidInputError:
            title = " ".join(self.v_title.get().split()) or "Course title"
        try:
            units = f"{Course.clean_units(self.v_units.get())} unit(s)"
        except InvalidInputError:
            units = "– units"
        self.pv_code.config(text=code)
        self.pv_title.config(text=title)
        self.pv_units.config(text=units)

    def clear_form(self):
        for var in (self.v_code, self.v_title, self.v_units):
            var.set("")
        self.error_label.config(text="")

    def submit_course(self):
        try:
            course = Course.create(self.v_code.get(), self.v_title.get(), self.v_units.get())
            self.manager.add_course(course)
        except (InvalidInputError, DuplicateCourseError) as err:
            self.error_label.config(text=f"⚠  {err}")
            self.toast(str(err), "err")
            return
        self.clear_form()
        self.mark_changed()
        self.toast(f"{course.code} added successfully.", "ok")

    # ------------------------------------------------------------- 02 VIEW
    def page_view(self):
        self.header("All Courses", "Every course recorded for this semester.")
        chips = tk.Frame(self.content, bg=BG)
        chips.pack(fill="x", pady=(0, 14))
        for text in (f"{self.manager.count()} courses", f"{self.manager.total_units()} total units"):
            tk.Label(chips, text=text, bg=CARD_2, fg=TEXT, font=(FONT, 10, "bold"),
                     padx=14, pady=6).pack(side="left", padx=(0, 10))

        holder = tk.Frame(self.content, bg=CARD, highlightthickness=1, highlightbackground=BORDER)
        holder.pack(fill="both", expand=True)
        columns = ("no", "code", "title", "units")
        self.tree = ttk.Treeview(holder, columns=columns, show="headings", selectmode="browse")
        for col, text, width, anchor in (("no", "#", 60, "center"), ("code", "CODE", 140, "w"),
                                         ("title", "COURSE TITLE", 460, "w"), ("units", "UNITS", 90, "center")):
            self.tree.heading(col, text=text)
            self.tree.column(col, width=width, anchor=anchor, stretch=(col == "title"))
        scroll = ttk.Scrollbar(holder, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=scroll.set)
        scroll.pack(side="right", fill="y")
        self.tree.pack(fill="both", expand=True)
        self.tree.tag_configure("odd", background="#1E2446")

        for i, course in enumerate(self.manager.courses, start=1):  # loop over courses
            self.tree.insert("", "end", iid=course.code, tags=("odd" if i % 2 == 0 else "",),
                             values=(i, course.code, course.title, course.units))

        if not self.manager.courses:
            tk.Label(holder, text="No courses yet.\nUse “Add Course” or “Load from File”.",
                     bg=CARD, fg=MUTED, font=(FONT, 12), justify="center").place(relx=0.5, rely=0.5, anchor="center")

        bar = tk.Frame(self.content, bg=BG)
        bar.pack(fill="x", pady=(14, 0))
        RoundButton(bar, "Remove Selected", self.remove_selected, bg="#3A2440", hover="#5A2D50",
                    fg=ERR, width=180).pack(side="left")

    def remove_selected(self):
        selected = self.tree.selection()
        if not selected:
            self.toast("Select a course in the table first.", "info")
            return
        code = selected[0]
        if messagebox.askyesno("Remove course", f"Remove {code} from your list?"):
            self.manager.remove_course(code)
            self.mark_changed()
            self.show_page("view", self.page_view)
            self.toast(f"{code} removed.", "ok")

    # ----------------------------------------------------------- 03 SEARCH
    def page_search(self):
        self.header("Search Course", "Find a course instantly using its course code.")
        bar = self.card()
        bar.pack(fill="x")
        self.v_search = tk.StringVar()
        field, entry = make_field(bar, "Course code", "Spaces and letter case are ignored (cos 201 = COS201)", self.v_search)
        field.pack(side="left", fill="x", expand=True)
        RoundButton(bar, "Search", self.run_search, width=130).pack(side="left", padx=(18, 0), pady=(0, 20))
        entry.bind("<Return>", lambda e: self.run_search())
        entry.focus_set()
        self.result_area = tk.Frame(self.content, bg=BG)
        self.result_area.pack(fill="both", expand=True, pady=(20, 0))

    def run_search(self):
        for child in self.result_area.winfo_children():
            child.destroy()
        try:
            position, result = self.manager.search(self.v_search.get())
        except InvalidInputError as err:
            self.toast(str(err), "err")
            return
        box = self.card(self.result_area)
        box.pack(fill="x")
        if position is None:
            tk.Label(box, text="No match", bg=CARD, fg=ERR, font=(FONT, 20, "bold")).pack(anchor="w")
            tk.Label(box, text=f"{result} is not in your course list.", bg=CARD, fg=MUTED,
                     font=(FONT, 12)).pack(anchor="w", pady=(6, 0))
            return
        tk.Label(box, text="COURSE FOUND", bg=CARD, fg=OK, font=(FONT, 9, "bold")).pack(anchor="w")
        tk.Label(box, text=result.code, bg=CARD, fg=CYAN, font=(FONT, 30, "bold")).pack(anchor="w", pady=(8, 0))
        tk.Label(box, text=result.title, bg=CARD, fg=TEXT, font=(FONT, 16)).pack(anchor="w")
        tk.Label(box, text=f"{result.units} credit unit(s)", bg=CARD_2, fg=TEXT,
                 font=(FONT, 11, "bold"), padx=14, pady=6).pack(anchor="w", pady=(16, 8))
        tk.Label(box, text=f"Located at position {position + 1} of {self.manager.count()} using recursive search.",
                 bg=CARD, fg=MUTED, font=(FONT, 10)).pack(anchor="w")

    # ------------------------------------------------------------ 04 TOTAL
    def page_total(self):
        self.header("Total Units", f"Your credit load compared with a {SEMESTER_TARGET}-unit semester target.")
        row = tk.Frame(self.content, bg=BG)
        row.pack(fill="both", expand=True)

        ring_card = self.card(row)
        ring_card.pack(side="left", padx=(0, 20))
        size = 300
        canvas = tk.Canvas(ring_card, width=size, height=size, bg=CARD, highlightthickness=0)
        canvas.pack()
        canvas.create_arc(30, 30, size - 30, size - 30, start=90, extent=359.9, style="arc", outline=CARD_2, width=26)
        arc = canvas.create_arc(30, 30, size - 30, size - 30, start=90, extent=0, style="arc", outline=CYAN, width=26)
        number = canvas.create_text(size / 2, size / 2 - 10, text="0", fill=TEXT, font=(FONT, 58, "bold"))
        canvas.create_text(size / 2, size / 2 + 40, text="UNITS", fill=MUTED, font=(FONT, 11, "bold"))

        total = self.manager.total_units()
        count = self.manager.count()
        self.count_up(canvas, arc, number, 0, total)  # recursive animation

        stats = tk.Frame(row, bg=BG)
        stats.pack(side="left", fill="both", expand=True)
        average = f"{total / count:.1f}" if count else "0"
        if total == 0:
            level, color = "No courses yet", MUTED
        elif total < 15:
            level, color = "Light load", CYAN
        elif total <= SEMESTER_TARGET:
            level, color = "Healthy load", OK
        else:
            level, color = "Above the usual limit", WARN
        for title, value, tint in (("Courses recorded", str(count), TEXT),
                                   ("Average units per course", average, TEXT),
                                   ("Load status", level, color)):
            tile = self.card(stats)
            tile.pack(fill="x", pady=(0, 14))
            tk.Label(tile, text=title.upper(), bg=CARD, fg=MUTED, font=(FONT, 9, "bold")).pack(anchor="w")
            tk.Label(tile, text=value, bg=CARD, fg=tint, font=(FONT, 22, "bold")).pack(anchor="w", pady=(6, 0))

    def count_up(self, canvas, arc, number, current, target):
        """Recursive animation: counts from 0 up to the total units."""
        try:
            canvas.itemconfig(number, text=str(current))
            canvas.itemconfig(arc, extent=-min(current / SEMESTER_TARGET, 1) * 359.9)
            if current < target:
                self.after(45, self.count_up, canvas, arc, number, current + 1, target)
        except tk.TclError:  # page changed before the animation finished
            pass

    # ------------------------------------------------------------- 05 SAVE
    def save_courses(self):
        if not self.manager.courses:
            self.toast("Nothing to save yet - add a course first.", "info")
            return False
        path = filedialog.asksaveasfilename(title="Save course list", defaultextension=".json",
                                            initialfile="my_courses.json",
                                            filetypes=[("Course files", "*.json"), ("All files", "*.*")])
        if not path:
            return False
        try:
            self.manager.save(path)
        except OSError as err:
            messagebox.showerror("Could not save", f"The file could not be written.\n\n{err}")
            return False
        self.unsaved = False
        self.update_status()
        self.toast(f"Saved {self.manager.count()} course(s).", "ok")
        return True

    # ------------------------------------------------------------- 06 LOAD
    def load_courses(self):
        path = filedialog.askopenfilename(title="Load course list",
                                          filetypes=[("Course files", "*.json"), ("All files", "*.*")])
        if not path:
            return
        try:
            loaded = self.manager.load(path)
        except FileNotFoundError:
            self.toast("That file could not be found.", "err")
            return
        except CourseFileError as err:
            self.toast(str(err), "err")
            return
        except OSError as err:
            messagebox.showerror("Could not load", f"The file could not be read.\n\n{err}")
            return
        self.unsaved = False
        self.update_status()
        self.toast(f"Loaded {loaded} course(s).", "ok")
        if self.current == "view":
            self.show_page("view", self.page_view)
        elif self.current == "total":
            self.show_page("total", self.page_total)

    # ------------------------------------------------------------- 07 EXIT
    def exit_program(self):
        if self.unsaved and self.manager.courses:
            answer = messagebox.askyesnocancel("Exit", "You have unsaved changes.\nSave before exiting?")
            if answer is None:
                return
            if answer and not self.save_courses():
                return
        elif not messagebox.askyesno("Exit", "Close the Course Manager?"):
            return
        self.destroy()


if __name__ == "__main__":
    CourseApp().mainloop()
