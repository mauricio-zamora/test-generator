"""
Pestaña de Gestión del Banco de Indicaciones Generales Reutilizables.
"""

import tkinter as tk
from tkinter import ttk, messagebox
from typing import Optional, Callable
import database


class InstructionsTab(ttk.Frame):
    def __init__(self, parent, on_data_changed: Optional[Callable] = None):
        super().__init__(parent, padding="15")
        self.on_data_changed = on_data_changed
        self.current_id = None
        self._build_ui()
        self.refresh_data()

    def _build_ui(self):
        header = ttk.Frame(self)
        header.pack(fill=tk.X, pady=(0, 15))
        ttk.Label(header, text="Banco de Indicaciones Generales", font=("Segoe UI", 12, "bold")).pack(anchor=tk.W)
        ttk.Label(header, text="Defina plantillas de instrucciones recurrentes para seleccionarlas rápidamente al crear exámenes.", font=("Segoe UI", 9)).pack(anchor=tk.W)

        paned = ttk.PanedWindow(self, orient=tk.HORIZONTAL)
        paned.pack(fill=tk.BOTH, expand=True)

        # Panel izquierdo: Lista de plantillas
        left_frame = ttk.LabelFrame(paned, text="Plantillas Guardadas", padding="10")
        paned.add(left_frame, weight=1)

        self.tree = ttk.Treeview(left_frame, columns=("id", "title", "default"), show="headings", selectmode="browse")
        self.tree.heading("id", text="ID")
        self.tree.heading("title", text="Título de la Plantilla")
        self.tree.heading("default", text="Por Defecto")

        self.tree.column("id", width=35, anchor=tk.CENTER)
        self.tree.column("title", width=220)
        self.tree.column("default", width=80, anchor=tk.CENTER)

        self.tree.pack(side=tk.TOP, fill=tk.BOTH, expand=True)
        self.tree.bind("<<TreeviewSelect>>", self._on_select_template)

        left_btns = ttk.Frame(left_frame)
        left_btns.pack(fill=tk.X, pady=(10, 0))
        ttk.Button(left_btns, text="➕ Nueva", command=self._new_instruction).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(left_btns, text="🗑️ Eliminar", command=self._delete_instruction).pack(side=tk.LEFT)

        # Panel derecho: Editor de contenido
        right_frame = ttk.LabelFrame(paned, text="Detalle de la Indicación", padding="10")
        paned.add(right_frame, weight=2)

        ttk.Label(right_frame, text="Título identificador:").pack(anchor=tk.W, pady=(0, 2))
        self.title_entry = ttk.Entry(right_frame)
        self.title_entry.pack(fill=tk.X, pady=(0, 10))

        self.default_var = tk.BooleanVar(value=False)
        self.default_check = ttk.Checkbutton(right_frame, text="Marcar como plantilla por defecto para nuevos exámenes", variable=self.default_var)
        self.default_check.pack(anchor=tk.W, pady=(0, 10))

        ttk.Label(right_frame, text="Texto de las Indicaciones (admite <b>negrita</b>, etc.):").pack(anchor=tk.W, pady=(0, 2))
        self.content_text = tk.Text(right_frame, height=12, font=("Segoe UI", 9), wrap=tk.WORD)
        self.content_text.pack(fill=tk.BOTH, expand=True, pady=(0, 10))

        right_btns = ttk.Frame(right_frame)
        right_btns.pack(fill=tk.X)
        ttk.Button(right_btns, text="💾 Guardar Plantilla", command=self._save_instruction).pack(side=tk.RIGHT)

    def refresh_data(self):
        for item in self.tree.get_children():
            self.tree.delete(item)

        items = database.get_instructions()
        for ins in items:
            def_str = "Sí" if ins["is_default"] else ""
            self.tree.insert("", tk.END, values=(ins["id"], ins["title"], def_str))

        if self.on_data_changed:
            self.on_data_changed()

    def _on_select_template(self, event=None):
        selected = self.tree.selection()
        if not selected:
            return
        ins_id = int(self.tree.item(selected[0], "values")[0])
        self.current_id = ins_id

        items = database.get_instructions()
        for ins in items:
            if ins["id"] == ins_id:
                self.title_entry.delete(0, tk.END)
                self.title_entry.insert(0, ins["title"])
                self.default_var.set(bool(ins["is_default"]))
                self.content_text.delete("1.0", tk.END)
                self.content_text.insert("1.0", ins["content"])
                break

    def _new_instruction(self):
        self.current_id = None
        self.title_entry.delete(0, tk.END)
        self.default_var.set(False)
        self.content_text.delete("1.0", tk.END)
        self.title_entry.focus_set()

    def _save_instruction(self):
        t = self.title_entry.get().strip()
        c = self.content_text.get("1.0", tk.END).strip()
        if not t:
            messagebox.showerror("Error", "Debe ingresar un título identificador.")
            return
        if not c:
            messagebox.showerror("Error", "Debe ingresar el texto de las indicaciones.")
            return

        is_def = 1 if self.default_var.get() else 0

        database.save_instruction(title=t, content=c, is_default=is_def, instruction_id=self.current_id)
        messagebox.showinfo("Guardado", "Plantilla de indicaciones guardada con éxito.")
        self.refresh_data()

    def _delete_instruction(self):
        if not self.current_id:
            messagebox.showwarning("Atención", "Seleccione una plantilla para eliminar.")
            return
        if messagebox.askyesno("Confirmar", "¿Desea eliminar esta plantilla de indicaciones?"):
            database.delete_instruction(self.current_id)
            self._new_instruction()
            self.refresh_data()
