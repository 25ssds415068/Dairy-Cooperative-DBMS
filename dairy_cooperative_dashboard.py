"""
Dairy Cooperative & Milk Quality Testing Dashboard
-------------------------------------------------
A single-file Python application using SQLite and Tkinter.

Run:
    python dairy_cooperative_dashboard.py

The SQLite database file (dairy_cooperative.db) is created in the
same folder as this script. Foreign-key enforcement is enabled on
every database connection.
"""

import sqlite3
from contextlib import contextmanager
import tkinter as tk
from tkinter import ttk, messagebox
from datetime import date
from pathlib import Path


DB_PATH = Path(__file__).with_name("dairy_cooperative.db")


# ----------------------------- DATABASE LAYER -----------------------------

def get_connection():
    """Create a database connection and enable foreign-key enforcement."""
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


@contextmanager
def database_session():
    """Commit successful work and always close the database connection."""
    conn = get_connection()
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def initialize_database():
    """Create the relational tables and seed data only if all are empty."""
    with database_session() as conn:
        cur = conn.cursor()

        cur.execute("""
            CREATE TABLE IF NOT EXISTS centres (
                centre_id INTEGER PRIMARY KEY AUTOINCREMENT,
                centre_name TEXT NOT NULL UNIQUE,
                contact_email TEXT NOT NULL
            )
        """)

        cur.execute("""
            CREATE TABLE IF NOT EXISTS milk_collections (
                collection_id INTEGER PRIMARY KEY AUTOINCREMENT,
                centre_id INTEGER NOT NULL,
                farmer_name TEXT NOT NULL,
                collection_date TEXT NOT NULL,
                FOREIGN KEY (centre_id)
                    REFERENCES centres(centre_id)
                    ON DELETE CASCADE
            )
        """)

        cur.execute("""
            CREATE TABLE IF NOT EXISTS quality_tests (
                test_id INTEGER PRIMARY KEY AUTOINCREMENT,
                collection_id INTEGER NOT NULL,
                test_type TEXT NOT NULL,
                measured_value REAL NOT NULL CHECK (measured_value >= 0),
                FOREIGN KEY (collection_id)
                    REFERENCES milk_collections(collection_id)
                    ON DELETE CASCADE
            )
        """)

        # Seed only when all three tables are completely empty.
        counts = [
            cur.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
            for table in ("centres", "milk_collections", "quality_tests")
        ]

        if counts == [0, 0, 0]:
            sample_centres = [
                ("Green Valley Dairy Centre", "greenvalley@example.com"),
                ("Sunrise Milk Cooperative", "sunrise@example.com"),
                ("Village Fresh Collection Point", "villagefresh@example.com"),
            ]
            cur.executemany(
                "INSERT INTO centres (centre_name, contact_email) VALUES (?, ?)",
                sample_centres
            )

            centre_ids = {
                name: cur.execute(
                    "SELECT centre_id FROM centres WHERE centre_name = ?", (name,)
                ).fetchone()[0]
                for name, _ in sample_centres
            }

            sample_collections = [
                (centre_ids["Green Valley Dairy Centre"], "Sukhdev Yadav", "2026-11-01"),
                (centre_ids["Sunrise Milk Cooperative"], "Lakshmi Amma", "2026-11-02"),
                (centre_ids["Village Fresh Collection Point"], "Ramesh Kumar", "2026-11-03"),
            ]
            cur.executemany("""
                INSERT INTO milk_collections
                    (centre_id, farmer_name, collection_date)
                VALUES (?, ?, ?)
            """, sample_collections)

            collection_ids = [
                row[0] for row in cur.execute(
                    "SELECT collection_id FROM milk_collections ORDER BY collection_id"
                ).fetchall()
            ]
            sample_tests = [
                (collection_ids[0], "Fat %", 4.2),
                (collection_ids[0], "SNF %", 8.5),
                (collection_ids[0], "Volume (litres)", 25.0),
                (collection_ids[1], "Fat %", 3.8),
                (collection_ids[1], "SNF %", 8.2),
                (collection_ids[1], "Volume (litres)", 18.5),
                (collection_ids[2], "Fat %", 4.0),
                (collection_ids[2], "SNF %", 8.4),
                (collection_ids[2], "Volume (litres)", 22.0),
            ]
            cur.executemany("""
                INSERT INTO quality_tests
                    (collection_id, test_type, measured_value)
                VALUES (?, ?, ?)
            """, sample_tests)


def add_collection_record(centre_name, contact_email, farmer_name,
                          test_type, measured_value):
    """Find/create a centre, then insert one collection and one quality test."""
    with database_session() as conn:
        cur = conn.cursor()

        existing = cur.execute(
            "SELECT centre_id FROM centres WHERE centre_name = ?",
            (centre_name,)
        ).fetchone()

        if existing:
            centre_id = existing[0]
        else:
            cur.execute("""
                INSERT INTO centres (centre_name, contact_email)
                VALUES (?, ?)
            """, (centre_name, contact_email))
            centre_id = cur.lastrowid

        cur.execute("""
            INSERT INTO milk_collections
                (centre_id, farmer_name, collection_date)
            VALUES (?, ?, ?)
        """, (centre_id, farmer_name, date.today().isoformat()))
        collection_id = cur.lastrowid

        cur.execute("""
            INSERT INTO quality_tests
                (collection_id, test_type, measured_value)
            VALUES (?, ?, ?)
        """, (collection_id, test_type, measured_value))


def fetch_rows(query, params=()):
    with database_session() as conn:
        return conn.execute(query, params).fetchall()


def delete_record(table, id_column, record_id):
    """Delete one selected record. Foreign keys perform required cascades."""
    allowed = {
        ("centres", "centre_id"),
        ("milk_collections", "collection_id"),
        ("quality_tests", "test_id"),
    }
    if (table, id_column) not in allowed:
        raise ValueError("Invalid table selection.")

    with database_session() as conn:
        cur = conn.cursor()
        cur.execute(
            f"DELETE FROM {table} WHERE {id_column} = ?",
            (record_id,)
        )
        return cur.rowcount


# ------------------------------- GUI LAYER --------------------------------

class DairyDashboard:
    def __init__(self, root):
        self.root = root
        self.root.title("Dairy Cooperative | Milk Quality Dashboard")
        self.root.geometry("1120x760")
        self.root.minsize(900, 620)

        self.setup_style()
        self.build_interface()
        self.refresh_all()

    def setup_style(self):
        style = ttk.Style()
        try:
            style.theme_use("clam")
        except tk.TclError:
            pass
        style.configure("Title.TLabel", font=("Arial", 17, "bold"))
        style.configure("Section.TLabelframe.Label", font=("Arial", 10, "bold"))
        style.configure("Treeview", rowheight=25)
        style.configure("Treeview.Heading", font=("Arial", 9, "bold"))
        style.configure("Action.TButton", padding=(10, 6))

    def build_interface(self):
        outer = ttk.Frame(self.root, padding=14)
        outer.pack(fill="both", expand=True)

        ttk.Label(
            outer,
            text="Dairy Cooperative & Milk Quality Testing Dashboard",
            style="Title.TLabel"
        ).pack(anchor="w", pady=(0, 4))

        ttk.Label(
            outer,
            text="Manage collection centres, milk collections and quality test records."
        ).pack(anchor="w", pady=(0, 12))

        self.notebook = ttk.Notebook(outer)
        self.notebook.pack(fill="both", expand=True)

        self.insert_tab = ttk.Frame(self.notebook, padding=14)
        self.delete_tab = ttk.Frame(self.notebook, padding=14)
        self.display_tab = ttk.Frame(self.notebook, padding=10)

        self.notebook.add(self.insert_tab, text="Insert Record")
        self.notebook.add(self.delete_tab, text="Delete Records")
        self.notebook.add(self.display_tab, text="View Database")

        self.build_insert_panel()
        self.build_delete_panel()
        self.build_display_panel()

    def build_insert_panel(self):
        form = ttk.LabelFrame(
            self.insert_tab, text="Add a Milk Collection and Quality Test",
            padding=16, style="Section.TLabelframe"
        )
        form.pack(fill="x", anchor="n")

        self.centre_var = tk.StringVar()
        self.email_var = tk.StringVar()
        self.farmer_var = tk.StringVar()
        self.test_type_var = tk.StringVar(value="Fat %")
        self.value_var = tk.StringVar()

        fields = [
            ("Centre Name", self.centre_var),
            ("Centre Contact Email (required for a new centre)", self.email_var),
            ("Farmer Name", self.farmer_var),
        ]

        for row, (label, variable) in enumerate(fields):
            ttk.Label(form, text=label).grid(
                row=row, column=0, sticky="w", padx=(0, 12), pady=7
            )
            ttk.Entry(form, textvariable=variable, width=48).grid(
                row=row, column=1, sticky="ew", pady=7
            )

        ttk.Label(form, text="Test Type").grid(
            row=3, column=0, sticky="w", padx=(0, 12), pady=7
        )
        test_choices = ttk.Combobox(
            form, textvariable=self.test_type_var, width=45,
            values=("Fat %", "SNF %", "Volume (litres)", "Other"),
            state="normal"
        )
        test_choices.grid(row=3, column=1, sticky="ew", pady=7)

        ttk.Label(form, text="Measured Value").grid(
            row=4, column=0, sticky="w", padx=(0, 12), pady=7
        )
        ttk.Entry(form, textvariable=self.value_var, width=48).grid(
            row=4, column=1, sticky="ew", pady=7
        )

        form.columnconfigure(1, weight=1)

        ttk.Button(
            form, text="Add Record", style="Action.TButton",
            command=self.add_record
        ).grid(row=5, column=1, sticky="e", pady=(14, 4))

        ttk.Label(
            self.insert_tab,
            text=("Note: If the centre already exists, its existing profile is reused. "
                  "A new centre requires a contact email. Each submission creates "
                  "one new collection dated today and one quality test."),
            wraplength=900
        ).pack(anchor="w", pady=14)

    def build_delete_panel(self):
        ttk.Label(
            self.delete_tab,
            text="Select a record type and the specific record to delete.",
            font=("Arial", 10)
        ).pack(anchor="w", pady=(0, 12))

        self.delete_widgets = {}

        configurations = [
            ("centres", "Collection Centre", "centre_id"),
            ("milk_collections", "Milk Collection", "collection_id"),
            ("quality_tests", "Quality Test", "test_id"),
        ]

        for table, label, id_column in configurations:
            panel = ttk.LabelFrame(
                self.delete_tab, text=f"Delete {label}",
                padding=12, style="Section.TLabelframe"
            )
            panel.pack(fill="x", pady=7)

            variable = tk.StringVar()
            combo = ttk.Combobox(panel, textvariable=variable, state="readonly")
            combo.pack(side="left", fill="x", expand=True, padx=(0, 12))

            button = ttk.Button(
                panel, text="Delete Selected", style="Action.TButton",
                command=lambda t=table, c=id_column, v=variable:
                    self.confirm_delete(t, c, v)
            )
            button.pack(side="right")

            self.delete_widgets[table] = {
                "variable": variable,
                "combo": combo,
                "id_column": id_column
            }

        ttk.Label(
            self.delete_tab,
            text=("Deleting a centre also deletes its milk collections and their tests. "
                  "Deleting a collection deletes its tests. Deleting a quality test "
                  "does not delete its parent collection or centre."),
            wraplength=900
        ).pack(anchor="w", pady=14)

    def build_display_panel(self):
        self.view_notebook = ttk.Notebook(self.display_tab)
        self.view_notebook.pack(fill="both", expand=True)

        self.treeviews = {}

        view_specs = [
            ("joined", "Combined JOIN View",
             ("Collection ID", "Centre Name", "Farmer Name",
              "Collection Date", "Test Type", "Measured Value")),
            ("centres", "Centres",
             ("Centre ID", "Centre Name", "Contact Email")),
            ("milk_collections", "Milk Collections",
             ("Collection ID", "Centre ID", "Farmer Name", "Collection Date")),
            ("quality_tests", "Quality Tests",
             ("Test ID", "Collection ID", "Test Type", "Measured Value")),
        ]

        for key, title, columns in view_specs:
            frame = ttk.Frame(self.view_notebook, padding=6)
            self.view_notebook.add(frame, text=title)

            tree = ttk.Treeview(
                frame, columns=columns, show="headings", height=18
            )
            vertical = ttk.Scrollbar(frame, orient="vertical", command=tree.yview)
            horizontal = ttk.Scrollbar(frame, orient="horizontal", command=tree.xview)
            tree.configure(yscrollcommand=vertical.set, xscrollcommand=horizontal.set)

            for column in columns:
                tree.heading(column, text=column)
                tree.column(column, width=145, minwidth=90, anchor="center")

            tree.pack(side="top", fill="both", expand=True)
            vertical.pack(side="right", fill="y")
            horizontal.pack(side="bottom", fill="x")

            self.treeviews[key] = tree

        bottom = ttk.Frame(self.display_tab)
        bottom.pack(fill="x", pady=(8, 0))
        self.status_var = tk.StringVar(value="Database ready.")
        ttk.Label(bottom, textvariable=self.status_var).pack(side="left")
        ttk.Button(
            bottom, text="Refresh Views", command=self.refresh_all
        ).pack(side="right")

    def add_record(self):
        centre = self.centre_var.get().strip()
        email = self.email_var.get().strip()
        farmer = self.farmer_var.get().strip()
        test_type = self.test_type_var.get().strip()
        raw_value = self.value_var.get().strip()

        if not all((centre, farmer, test_type, raw_value)):
            messagebox.showwarning(
                "Missing Information", "Please fill in all required fields."
            )
            return

        try:
            measured_value = float(raw_value)
        except ValueError:
            messagebox.showerror(
                "Invalid Value", "Measured Value must be a valid number."
            )
            return

        if measured_value < 0:
            messagebox.showerror(
                "Invalid Value", "Measured Value cannot be negative."
            )
            return

        existing = fetch_rows(
            "SELECT centre_id FROM centres WHERE centre_name = ?", (centre,)
        )
        if not existing and not email:
            messagebox.showwarning(
                "Contact Email Required",
                "Enter a contact email when creating a new collection centre."
            )
            return

        if email and ("@" not in email or "." not in email.split("@")[-1]):
            messagebox.showerror(
                "Invalid Email", "Please enter a valid contact email address."
            )
            return

        try:
            add_collection_record(
                centre, email if email else "Not provided",
                farmer, test_type, measured_value
            )
            self.centre_var.set("")
            self.email_var.set("")
            self.farmer_var.set("")
            self.test_type_var.set("Fat %")
            self.value_var.set("")
            self.refresh_all()
            messagebox.showinfo(
                "Success", "Milk collection and quality test added successfully."
            )
        except sqlite3.Error as error:
            messagebox.showerror("Database Error", str(error))

    def confirm_delete(self, table, id_column, variable):
        selected = variable.get().strip()
        if not selected:
            messagebox.showwarning(
                "No Selection", "Please select a record before deleting."
            )
            return

        try:
            record_id = int(selected.split(" | ", 1)[0].replace("#", ""))
        except (ValueError, IndexError):
            messagebox.showerror(
                "Selection Error", "The selected record could not be identified."
            )
            return

        descriptions = {
            "centres": "this centre and all its related collections and tests",
            "milk_collections": "this collection and all its quality tests",
            "quality_tests": "only this quality test",
        }
        if not messagebox.askyesno(
            "Confirm Deletion",
            f"Are you sure you want to delete {descriptions[table]}?"
        ):
            return

        try:
            deleted = delete_record(table, id_column, record_id)
            self.refresh_all()
            if deleted:
                messagebox.showinfo("Deleted", "The selected record was deleted.")
            else:
                messagebox.showwarning(
                    "Not Found", "That record no longer exists. The lists were refreshed."
                )
        except sqlite3.Error as error:
            messagebox.showerror("Database Error", str(error))

    def fill_tree(self, key, rows):
        tree = self.treeviews[key]
        tree.delete(*tree.get_children())
        for row in rows:
            tree.insert("", "end", values=row)

    def refresh_dropdowns(self):
        centre_rows = fetch_rows("""
            SELECT centre_id, centre_name FROM centres ORDER BY centre_id
        """)
        collection_rows = fetch_rows("""
            SELECT mc.collection_id, mc.farmer_name, c.centre_name
            FROM milk_collections mc
            JOIN centres c ON c.centre_id = mc.centre_id
            ORDER BY mc.collection_id
        """)
        test_rows = fetch_rows("""
            SELECT qt.test_id, qt.test_type, mc.farmer_name
            FROM quality_tests qt
            JOIN milk_collections mc ON mc.collection_id = qt.collection_id
            ORDER BY qt.test_id
        """)

        options = {
            "centres": [
                f"#{row[0]} | {row[1]}" for row in centre_rows
            ],
            "milk_collections": [
                f"#{row[0]} | {row[1]} | {row[2]}" for row in collection_rows
            ],
            "quality_tests": [
                f"#{row[0]} | {row[1]} | {row[2]}" for row in test_rows
            ],
        }

        for table, values in options.items():
            combo = self.delete_widgets[table]["combo"]
            variable = self.delete_widgets[table]["variable"]
            previous = variable.get()
            combo["values"] = values
            # Never retain a selection that no longer exists.
            variable.set(previous if previous in values else "")
            if values and not variable.get():
                variable.set(values[0])

    def refresh_all(self):
        joined_rows = fetch_rows("""
            SELECT mc.collection_id, c.centre_name, mc.farmer_name,
                   mc.collection_date, qt.test_type, qt.measured_value
            FROM milk_collections mc
            JOIN centres c ON c.centre_id = mc.centre_id
            JOIN quality_tests qt ON qt.collection_id = mc.collection_id
            ORDER BY mc.collection_id, qt.test_id
        """)

        centre_rows = fetch_rows("""
            SELECT centre_id, centre_name, contact_email
            FROM centres ORDER BY centre_id
        """)
        collection_rows = fetch_rows("""
            SELECT collection_id, centre_id, farmer_name, collection_date
            FROM milk_collections ORDER BY collection_id
        """)
        test_rows = fetch_rows("""
            SELECT test_id, collection_id, test_type, measured_value
            FROM quality_tests ORDER BY test_id
        """)

        self.fill_tree("joined", joined_rows)
        self.fill_tree("centres", centre_rows)
        self.fill_tree("milk_collections", collection_rows)
        self.fill_tree("quality_tests", test_rows)
        self.refresh_dropdowns()

        self.status_var.set(
            f"Centres: {len(centre_rows)} | "
            f"Collections: {len(collection_rows)} | "
            f"Quality tests: {len(test_rows)}"
        )


def main():
    initialize_database()

    try:
        root = tk.Tk()
    except tk.TclError as error:
        print("The SQLite database was initialized successfully.")
        print("The Tkinter window could not be opened in this environment.")
        print("Run this script on a desktop Python installation with GUI support,")
        print("such as VS Code on Windows, macOS or Linux.")
        print("GUI error:", error)
        return

    DairyDashboard(root)
    root.mainloop()


if __name__ == "__main__":
    main()
