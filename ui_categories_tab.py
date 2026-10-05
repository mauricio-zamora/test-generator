"""
Pestaña de Gestión de Categorías (Secciones) y Subcategorías.
Permite crear, editar, eliminar, importar y exportar categorías en CSV/TXT.
"""

import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from typing import Optional, Callable
import database
import importer_exporter
from ui_dialogs import center_window


class CategoriesTab(ttk.Frame):
    def __init__(self, parent, on_data_changed: Optional[Callable] = None):
        super().__init__(parent, padding="15")
        self.on_data_changed = on_data_changed
        self._build_ui()
        self.refresh_data()

    def _build_ui(self):
        header = ttk.Frame(self)
        header.pack(fill=tk.X, pady=(0, 12))

        left_hdr = ttk.Frame(header)
        left_hdr.pack(side=tk.LEFT)
        ttk.Label(left_hdr, text="Gestión de Categorías y Subcategorías", font=("Segoe UI", 12, "bold")).pack(anchor=tk.W)
        ttk.Label(left_hdr, text="Las categorías representan las secciones del examen. La numeración romana ('Parte I, II, ...') se asigna automáticamente.", font=("Segoe UI", 9)).pack(anchor=tk.W)

        right_hdr = ttk.Frame(header)
        right_hdr.pack(side=tk.RIGHT)
        ttk.Button(right_hdr, text="📥 Importar (CSV)...", command=self._import_csv).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(right_hdr, text="📤 Exportar (CSV)...", command=self._export_csv).pack(side=tk.LEFT)

        paned = ttk.PanedWindow(self, orient=tk.HORIZONTAL)
        paned.pack(fill=tk.BOTH, expand=True)

        # --- PANEL IZQUIERDO: CATEGORÍAS ---
        cat_frame = ttk.LabelFrame(paned, text="Categorías (Secciones del Examen)", padding="10")
        paned.add(cat_frame, weight=1)

        self.cat_tree = ttk.Treeview(cat_frame, columns=("id", "name", "order"), show="headings", selectmode="browse")
        self.cat_tree.heading("id", text="ID")
        self.cat_tree.heading("name", text="Nombre de Categoría / Sección")
        self.cat_tree.heading("order", text="Orden")

        self.cat_tree.column("id", width=35, anchor=tk.CENTER)
        self.cat_tree.column("name", width=280)
        self.cat_tree.column("order", width=55, anchor=tk.CENTER)

        self.cat_tree.pack(side=tk.TOP, fill=tk.BOTH, expand=True)
        self.cat_tree.bind("<<TreeviewSelect>>", self._on_category_selected)

        cat_btns = ttk.Frame(cat_frame)
        cat_btns.pack(fill=tk.X, pady=(10, 0))
        ttk.Button(cat_btns, text="➕ Nueva Categoría", command=self._new_category_dialog).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(cat_btns, text="✏️ Editar", command=self._edit_category_dialog).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(cat_btns, text="🗑️ Eliminar", command=self._delete_category).pack(side=tk.LEFT)

        # --- PANEL DERECHO: SUBCATEGORÍAS ---
        subcat_frame = ttk.LabelFrame(paned, text="Subcategorías de la Categoría Seleccionada", padding="10")
        paned.add(subcat_frame, weight=1)

        self.subcat_tree = ttk.Treeview(subcat_frame, columns=("id", "name", "desc"), show="headings", selectmode="browse")
        self.subcat_tree.heading("id", text="ID")
        self.subcat_tree.heading("name", text="Nombre de Subcategoría")
        self.subcat_tree.heading("desc", text="Descripción")

        self.subcat_tree.column("id", width=35, anchor=tk.CENTER)
        self.subcat_tree.column("name", width=180)
        self.subcat_tree.column("desc", width=220)

        self.subcat_tree.pack(side=tk.TOP, fill=tk.BOTH, expand=True)

        subcat_btns = ttk.Frame(subcat_frame)
        subcat_btns.pack(fill=tk.X, pady=(10, 0))
        ttk.Button(subcat_btns, text="➕ Nueva Subcategoría", command=self._new_subcategory_dialog).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(subcat_btns, text="🗑️ Eliminar", command=self._delete_subcategory).pack(side=tk.LEFT)

    def refresh_data(self):
        for item in self.cat_tree.get_children():
            self.cat_tree.delete(item)
        cats = database.get_categories()
        for c in cats:
            self.cat_tree.insert("", tk.END, values=(c["id"], c["name"], c["default_order"]))

        for item in self.subcat_tree.get_children():
            self.subcat_tree.delete(item)

        if self.on_data_changed:
            self.on_data_changed()

    def _on_category_selected(self, event=None):
        selected = self.cat_tree.selection()
        for item in self.subcat_tree.get_children():
            self.subcat_tree.delete(item)
        if not selected:
            return

        cat_id = int(self.cat_tree.item(selected[0], "values")[0])
        subcats = database.get_subcategories(category_id=cat_id)
        for s in subcats:
            self.subcat_tree.insert("", tk.END, values=(s["id"], s["name"], s["description"] or ""))

    def _new_category_dialog(self):
        self._category_form_dialog()

    def _edit_category_dialog(self):
        selected = self.cat_tree.selection()
        if not selected:
            messagebox.showwarning("Atención", "Seleccione una categoría para editar.")
            return
        vals = self.cat_tree.item(selected[0], "values")
        self._category_form_dialog(cat_id=int(vals[0]), name=vals[1], order=int(vals[2]))

    def _category_form_dialog(self, cat_id: Optional[int] = None, name: str = "", order: int = 1):
        win = tk.Toplevel(self)
        win.title("Editar Categoría" if cat_id else "Nueva Categoría")
        win.resizable(False, False)
        center_window(win, 420, 210)
        win.transient(self)
        win.grab_set()

        f = ttk.Frame(win, padding="15")
        f.pack(fill=tk.BOTH, expand=True)

        ttk.Label(f, text="Nombre de la Categoría (ej: Desarrollo):").pack(anchor=tk.W, pady=(0, 2))
        e_name = ttk.Entry(f)
        e_name.insert(0, name)
        e_name.pack(fill=tk.X, pady=(0, 10))

        row_order = ttk.Frame(f)
        row_order.pack(fill=tk.X, pady=(0, 15))
        ttk.Label(row_order, text="Orden sugerido:").pack(side=tk.LEFT, padx=(0, 10))
        e_order = ttk.Spinbox(row_order, from_=1, to=20, width=6)
        e_order.set(str(order))
        e_order.pack(side=tk.LEFT)

        btn_row = ttk.Frame(f)
        btn_row.pack(fill=tk.X)
        ttk.Button(btn_row, text="Cancelar", command=win.destroy).pack(side=tk.RIGHT, padx=(5, 0))

        def save():
            n = e_name.get().strip()
            if not n:
                messagebox.showerror("Error", "Debe ingresar un nombre para la categoría.", parent=win)
                return
            try:
                ord_val = int(e_order.get())
            except Exception:
                ord_val = 1

            try:
                if cat_id:
                    database.update_category(cat_id, n, n, "", ord_val)
                else:
                    database.add_category(n, n, "", ord_val)
                win.destroy()
                self.refresh_data()
            except Exception as ex:
                messagebox.showerror("Error", f"No se pudo guardar la categoría:\n{ex}", parent=win)

        ttk.Button(btn_row, text="Guardar", command=save).pack(side=tk.RIGHT)

    def _delete_category(self):
        selected = self.cat_tree.selection()
        if not selected:
            messagebox.showwarning("Atención", "Seleccione una categoría para eliminar.")
            return
        vals = self.cat_tree.item(selected[0], "values")
        cat_id = int(vals[0])
        name = vals[1]

        if messagebox.askyesno("Confirmar Eliminación", f"¿Está seguro de eliminar la categoría '{name}'?"):
            try:
                database.delete_category(cat_id)
                self.refresh_data()
            except Exception as ex:
                messagebox.showerror("Error al Eliminar", f"No se puede eliminar la categoría porque contiene preguntas asociadas:\n{ex}")

    def _new_subcategory_dialog(self):
        selected = self.cat_tree.selection()
        if not selected:
            messagebox.showwarning("Atención", "Seleccione primero una categoría.")
            return
        cat_id = int(self.cat_tree.item(selected[0], "values")[0])
        cat_name = self.cat_tree.item(selected[0], "values")[1]

        win = tk.Toplevel(self)
        win.title(f"Nueva Subcategoría en '{cat_name}'")
        win.resizable(False, False)
        center_window(win, 400, 180)
        win.transient(self)
        win.grab_set()

        f = ttk.Frame(win, padding="15")
        f.pack(fill=tk.BOTH, expand=True)

        ttk.Label(f, text="Nombre de la Subcategoría (ej: Cadenas y Texto):").pack(anchor=tk.W, pady=(0, 2))
        e_name = ttk.Entry(f)
        e_name.pack(fill=tk.X, pady=(0, 15))

        btn_row = ttk.Frame(f)
        btn_row.pack(fill=tk.X)
        ttk.Button(btn_row, text="Cancelar", command=win.destroy).pack(side=tk.RIGHT, padx=(5, 0))

        def save():
            n = e_name.get().strip()
            if not n:
                messagebox.showerror("Error", "Debe ingresar un nombre para la subcategoría.", parent=win)
                return
            try:
                database.add_subcategory(cat_id, n, "")
                win.destroy()
                self._on_category_selected()
                if self.on_data_changed:
                    self.on_data_changed()
            except Exception as ex:
                messagebox.showerror("Error", f"No se pudo guardar la subcategoría:\n{ex}", parent=win)

        ttk.Button(btn_row, text="Guardar", command=save).pack(side=tk.RIGHT)

    def _delete_subcategory(self):
        selected = self.subcat_tree.selection()
        if not selected:
            messagebox.showwarning("Atención", "Seleccione una subcategoría para eliminar.")
            return
        vals = self.subcat_tree.item(selected[0], "values")
        sub_id = int(vals[0])
        name = vals[1]

        if messagebox.askyesno("Confirmar", f"¿Desea eliminar la subcategoría '{name}'?"):
            database.delete_subcategory(sub_id)
            self._on_category_selected()
            if self.on_data_changed:
                self.on_data_changed()

    def _export_csv(self):
        file_path = filedialog.asksaveasfilename(
            title="Exportar Categorías y Subcategorías",
            defaultextension=".csv",
            filetypes=[("Archivos CSV", "*.csv"), ("Todos los archivos", "*.*")],
            initialfile="categorias_exportadas.csv",
            parent=self
        )
        if not file_path:
            return
        try:
            count = importer_exporter.export_categories_to_csv(file_path)
            messagebox.showinfo("Exportación Exitosa", f"Se exportaron {count} registros a:\n{file_path}", parent=self)
        except Exception as ex:
            messagebox.showerror("Error al Exportar", f"Ocurrió un error:\n{ex}", parent=self)

    def _import_csv(self):
        file_path = filedialog.askopenfilename(
            title="Importar Categorías y Subcategorías",
            filetypes=[("Archivos CSV y TXT", "*.csv;*.txt"), ("Todos los archivos", "*.*")],
            parent=self
        )
        if not file_path:
            return
        try:
            c_cnt, s_cnt = importer_exporter.import_categories_from_csv(file_path)
            self.refresh_data()
            messagebox.showinfo("Importación Exitosa", f"Se importaron {c_cnt} categorías y {s_cnt} subcategorías.", parent=self)
        except Exception as ex:
            messagebox.showerror("Error al Importar", f"No se pudo importar el archivo:\n{ex}", parent=self)
