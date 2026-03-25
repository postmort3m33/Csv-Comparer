import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import pandas as pd

class CsvCompareApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("CSV Compare")
        self.geometry("1000x700")

        self.path_a = tk.StringVar()
        self.path_b = tk.StringVar()
        self.key_col = tk.StringVar()

        self.df_a = None
        self.df_b = None
        self.result_only_a = None
        self.result_only_b = None

        self._build_ui()

    def _build_ui(self):
        top = ttk.Frame(self, padding=10)
        top.pack(fill="x")

        # File A
        ttk.Label(top, text="CSV A:").grid(row=0, column=0, sticky="w")
        ttk.Entry(top, textvariable=self.path_a, width=80).grid(row=0, column=1, sticky="we", padx=5)
        ttk.Button(top, text="Browse", command=self._browse_a).grid(row=0, column=2)

        # File B
        ttk.Label(top, text="CSV B:").grid(row=1, column=0, sticky="w")
        ttk.Entry(top, textvariable=self.path_b, width=80).grid(row=1, column=1, sticky="we", padx=5)
        ttk.Button(top, text="Browse", command=self._browse_b).grid(row=1, column=2)

        # Key column selector
        ttk.Label(top, text="Compare on column:").grid(row=2, column=0, sticky="w", pady=(10, 0))
        self.key_combo = ttk.Combobox(top, textvariable=self.key_col, state="readonly", width=30)
        self.key_combo.grid(row=2, column=1, sticky="w", pady=(10, 0))

        # Actions
        btns = ttk.Frame(top)
        btns.grid(row=2, column=2, sticky="e", pady=(10, 0))
        ttk.Button(btns, text="Compare", command=self._compare).pack(side="left", padx=5)
        ttk.Button(btns, text="Export Results", command=self._export).pack(side="left")

        top.columnconfigure(1, weight=1)

        # Results area
        mid = ttk.Frame(self, padding=10)
        mid.pack(fill="both", expand=True)

        self.tabs = ttk.Notebook(mid)
        self.tabs.pack(fill="both", expand=True)

        self.tree_only_a = self._make_tab("Only in A")
        self.tree_only_b = self._make_tab("Only in B")

        # Status
        self.status = tk.StringVar(value="Select two CSV files to begin.")
        ttk.Label(self, textvariable=self.status, padding=10).pack(fill="x")

    def _make_tab(self, title: str) -> ttk.Treeview:
        frame = ttk.Frame(self.tabs)
        self.tabs.add(frame, text=title)

        tree = ttk.Treeview(frame, show="headings")
        tree.pack(side="left", fill="both", expand=True)

        vsb = ttk.Scrollbar(frame, orient="vertical", command=tree.yview)
        vsb.pack(side="right", fill="y")
        tree.configure(yscrollcommand=vsb.set)

        return tree

    def _browse_a(self):
        path = filedialog.askopenfilename(filetypes=[("CSV files", "*.csv"), ("All files", "*.*")])
        if path:
            self.path_a.set(path)
            self._try_load()

    def _browse_b(self):
        path = filedialog.askopenfilename(filetypes=[("CSV files", "*.csv"), ("All files", "*.*")])
        if path:
            self.path_b.set(path)
            self._try_load()

    def _try_load(self):
        if not self.path_a.get() or not self.path_b.get():
            return

        try:
            self.df_a = pd.read_csv(self.path_a.get(), dtype=str, keep_default_na=False)
            self.df_b = pd.read_csv(self.path_b.get(), dtype=str, keep_default_na=False)
        except Exception as e:
            messagebox.showerror("Load error", str(e))
            return

        common_cols = sorted(set(self.df_a.columns).intersection(set(self.df_b.columns)))
        if not common_cols:
            messagebox.showwarning("No common columns", "These CSVs share no column names. Rename columns or pick a different approach.")
            return

        self.key_combo["values"] = common_cols
        self.key_col.set(common_cols[0])
        self.status.set(f"Loaded. Common columns: {len(common_cols)}. Selected key: {common_cols[0]}")

    def _compare(self):
        if self.df_a is None or self.df_b is None:
            messagebox.showinfo("Missing files", "Please choose both CSV files first.")
            return

        key = self.key_col.get().strip()
        if not key:
            messagebox.showinfo("Missing key", "Select a column to compare on.")
            return

        if key not in self.df_a.columns or key not in self.df_b.columns:
            messagebox.showerror("Invalid key", f"Column '{key}' must exist in both files.")
            return

        # Normalize keys (trim + consistent casing) to reduce false mismatches
        a_keys = self.df_a[key].astype(str).str.strip()
        b_keys = self.df_b[key].astype(str).str.strip()

        # Optional: uncomment if you want case-insensitive matching
        # a_keys = a_keys.str.lower()
        # b_keys = b_keys.str.lower()

        a_set = set(a_keys[a_keys != ""])
        b_set = set(b_keys[b_keys != ""])

        only_a = sorted(a_set - b_set)
        only_b = sorted(b_set - a_set)

        self.result_only_a = pd.DataFrame({key: only_a})
        self.result_only_b = pd.DataFrame({key: only_b})

        self._fill_tree(self.tree_only_a, self.result_only_a)
        self._fill_tree(self.tree_only_b, self.result_only_b)

        self.status.set(f"Compared on '{key}'. Only in A: {len(only_a)} | Only in B: {len(only_b)}")

    def _fill_tree(self, tree: ttk.Treeview, df: pd.DataFrame):
        tree.delete(*tree.get_children())
        tree["columns"] = list(df.columns)

        for col in df.columns:
            tree.heading(col, text=col)
            tree.column(col, width=400, anchor="w")

        # Insert rows (cap for UI performance; adjust as needed)
        MAX_ROWS = 5000
        for _, row in df.head(MAX_ROWS).iterrows():
            tree.insert("", "end", values=list(row.values))

        if len(df) > MAX_ROWS:
            tree.insert("", "end", values=[f"... showing first {MAX_ROWS} of {len(df)} rows ..."])

    def _export(self):
        if self.result_only_a is None or self.result_only_b is None:
            messagebox.showinfo("Nothing to export", "Run a comparison first.")
            return

        folder = filedialog.askdirectory()
        if not folder:
            return

        try:
            self.result_only_a.to_csv(f"{folder}/only_in_a.csv", index=False)
            self.result_only_b.to_csv(f"{folder}/only_in_b.csv", index=False)
        except Exception as e:
            messagebox.showerror("Export error", str(e))
            return

        messagebox.showinfo("Exported", "Saved only_in_a.csv and only_in_b.csv")

if __name__ == "__main__":
    app = CsvCompareApp()
    app.mainloop()