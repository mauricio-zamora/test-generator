"""
Pestaña de Gestión del Banco de Preguntas / Ítems.
Permite visualizar, filtrar, buscar, crear, editar, duplicar, eliminar,
importar y exportar preguntas en formato CSV.
"""

import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import json
from typing import Optional, Callable, Dict, Any

import database
import height_calculator
import importer_exporter
from ui_dialogs import QuestionEditorDialog


class QuestionsTab(ttk.Frame):
    def __init__(self, parent, on_add_to_exam: Optional[Callable[[Dict[str, Any]], None]] = None, on_data_changed: Optional[Callable] = None):
        super().__init__(parent, padding="15")
        self.on_add_to_exam = on_add_to_exam
        self.on_data_changed = on_data_changed
        self._build_ui()
        self.refresh_data()

    def _build_ui(self):
        # Encabezado con botones de Importar / Exportar
        header = ttk.Frame(self)
        header.pack(fill=tk.X, pady=(0, 10))

        left_hdr = ttk.Frame(header)
        left_hdr.pack(side=tk.LEFT)
        ttk.Label(left_hdr, text="Banco General de Preguntas e Ítems", font=("Segoe UI", 12, "bold")).pack(anchor=tk.W)
        ttk.Label(left_hdr, text="Administre el repertorio de preguntas organizadas por categorías y subcategorías.", font=("Segoe UI", 9)).pack(anchor=tk.W)

        right_hdr = ttk.Frame(header)
        right_hdr.pack(side=tk.RIGHT)
        ttk.Button(right_hdr, text="📥 Importar Preguntas (CSV)...", command=self._import_questions_csv).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(right_hdr, text="📤 Exportar Preguntas (CSV)...", command=self._export_questions_csv).pack(side=tk.LEFT)

        # Barra de Filtros
        filter_bar = ttk.LabelFrame(self, text="Filtros y Búsqueda", padding="10")
        filter_bar.pack(fill=tk.X, pady=(0, 10))

        ttk.Label(filter_bar, text="Categoría:").grid(row=0, column=0, sticky=tk.W, padx=(0, 4))
        self.cat_filter = ttk.Combobox(filter_bar, state="readonly", width=20)
        self.cat_filter.grid(row=0, column=1, sticky=tk.W, padx=(0, 10))
        self.cat_filter.bind("<<ComboboxSelected>>", self._on_cat_filter_changed)

        ttk.Label(filter_bar, text="Subcategoría:").grid(row=0, column=2, sticky=tk.W, padx=(0, 4))
        self.subcat_filter = ttk.Combobox(filter_bar, state="readonly", width=18)
        self.subcat_filter.grid(row=0, column=3, sticky=tk.W, padx=(0, 10))
        self.subcat_filter.bind("<<ComboboxSelected>>", lambda e: self.refresh_questions_list())

        ttk.Label(filter_bar, text="Tipo:").grid(row=0, column=4, sticky=tk.W, padx=(0, 4))
        self.type_filter = ttk.Combobox(filter_bar, state="readonly", width=22)
        self.type_filter["values"] = [
            "Todos",
            "Selección Única",
            "Selección Múltiple",
            "Falso y Verdadero",
            "Desarrollo",
            "Escritura de Código",
            "Código / Errores",
            "1 Imagen",
            "2 Imágenes",
            "Asociación"
        ]
        self.type_filter.current(0)
        self.type_filter.grid(row=0, column=5, sticky=tk.W, padx=(0, 10))
        self.type_filter.bind("<<ComboboxSelected>>", lambda e: self.refresh_questions_list())

        ttk.Label(filter_bar, text="Buscar:").grid(row=0, column=6, sticky=tk.W, padx=(0, 4))
        self.search_entry = ttk.Entry(filter_bar, width=18)
        self.search_entry.grid(row=0, column=7, sticky=tk.W, padx=(0, 5))
        self.search_entry.bind("<KeyRelease>", lambda e: self.refresh_questions_list())

        ttk.Button(filter_bar, text="Limpiar", command=self._clear_filters).grid(row=0, column=8, sticky=tk.W)

        # PanedWindow Principal
        paned = ttk.PanedWindow(self, orient=tk.HORIZONTAL)
        paned.pack(fill=tk.BOTH, expand=True)

        # --- LISTA DE PREGUNTAS ---
        list_frame = ttk.LabelFrame(paned, text="Listado de Preguntas", padding="10")
        paned.add(list_frame, weight=3)

        cols = ("id", "title", "category", "subcategory", "type", "points", "height")
        self.tree = ttk.Treeview(list_frame, columns=cols, show="headings", selectmode="browse")
        self.tree.heading("id", text="ID")
        self.tree.heading("title", text="Título / Pregunta")
        self.tree.heading("category", text="Categoría")
        self.tree.heading("subcategory", text="Subcategoría")
        self.tree.heading("type", text="Tipo")
        self.tree.heading("points", text="Pts")
        self.tree.heading("height", text="Alto (px)")

        self.tree.column("id", width=35, anchor=tk.CENTER)
        self.tree.column("title", width=220)
        self.tree.column("category", width=130)
        self.tree.column("subcategory", width=120)
        self.tree.column("type", width=115)
        self.tree.column("points", width=45, anchor=tk.CENTER)
        self.tree.column("height", width=65, anchor=tk.CENTER)

        tree_scroll = ttk.Scrollbar(list_frame, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscrollcommand=tree_scroll.set)

        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        tree_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        self.tree.bind("<<TreeviewSelect>>", self._on_question_selected)
        self.tree.bind("<Double-1>", lambda e: self._edit_question())

        # Barra de acciones de la lista
        btn_bar = ttk.Frame(self)
        btn_bar.pack(fill=tk.X, pady=(10, 0))

        ttk.Button(btn_bar, text="➕ Nueva Pregunta", command=self._new_question).pack(side=tk.LEFT, padx=(0, 6))
        ttk.Button(btn_bar, text="✏️ Editar", command=self._edit_question).pack(side=tk.LEFT, padx=(0, 6))
        ttk.Button(btn_bar, text="📋 Duplicar", command=self._duplicate_question).pack(side=tk.LEFT, padx=(0, 6))
        ttk.Button(btn_bar, text="🗑️ Eliminar", command=self._delete_question).pack(side=tk.LEFT, padx=(0, 15))

        if self.on_add_to_exam:
            ttk.Button(btn_bar, text="➕ Añadir a Examen Actual", command=self._add_selected_to_exam).pack(side=tk.RIGHT)

        # --- VISTA PREVIA DETALLADA ---
        preview_frame = ttk.LabelFrame(paned, text="Vista Previa del Ítem", padding="10")
        paned.add(preview_frame, weight=2)

        self.preview_text = tk.Text(preview_frame, font=("Segoe UI", 9), wrap=tk.WORD, state="disabled")
        self.preview_text.pack(fill=tk.BOTH, expand=True)

    def refresh_data(self):
        cats = database.get_categories()
        cat_names = ["Todas"] + [c["name"] for c in cats]
        cur_cat = self.cat_filter.get()
        self.cat_filter["values"] = cat_names
        if cur_cat in cat_names:
            self.cat_filter.set(cur_cat)
        else:
            self.cat_filter.current(0)

        self._on_cat_filter_changed()

    def _on_cat_filter_changed(self, event=None):
        selected_cat = self.cat_filter.get()
        cat_id = None
        if selected_cat != "Todas":
            for c in database.get_categories():
                if c["name"] == selected_cat:
                    cat_id = c["id"]
                    break

        subcats = database.get_subcategories(category_id=cat_id) if cat_id else database.get_subcategories()
        subcat_names = ["Todas"] + [s["name"] for s in subcats]
        self.subcat_filter["values"] = subcat_names
        self.subcat_filter.current(0)
        self.refresh_questions_list()

    def _clear_filters(self):
        self.cat_filter.current(0)
        self._on_cat_filter_changed()
        self.type_filter.current(0)
        self.search_entry.delete(0, tk.END)
        self.refresh_questions_list()

    def refresh_questions_list(self):
        for item in self.tree.get_children():
            self.tree.delete(item)

        selected_cat = self.cat_filter.get()
        cat_id = None
        if selected_cat != "Todas":
            for c in database.get_categories():
                if c["name"] == selected_cat:
                    cat_id = c["id"]
                    break

        selected_subcat = self.subcat_filter.get()
        subcat_id = None
        if selected_subcat != "Todas":
            for s in database.get_subcategories():
                if s["name"] == selected_subcat and (cat_id is None or s["category_id"] == cat_id):
                    subcat_id = s["id"]
                    break

        query = self.search_entry.get().strip()
        questions = database.get_questions(category_id=cat_id, subcategory_id=subcat_id, search_query=query)

        selected_type = self.type_filter.get()
        type_code_map = {
            "Selección Única": "single_choice",
            "Selección Múltiple": "multiple_choice",
            "Falso y Verdadero": "true_false",
            "Desarrollo": "development",
            "Escritura de Código": "code_writing",
            "Código / Errores": "code_analysis",
            "1 Imagen": "single_image",
            "2 Imágenes": "double_image",
            "Asociación": "association"
        }
        filter_type_code = type_code_map.get(selected_type)

        type_names = {
            "single_choice": "Selección Única",
            "multiple_choice": "Selección Múltiple",
            "true_false": "Falso y Verdadero",
            "development": "Desarrollo",
            "code_writing": "Escritura Código",
            "code_analysis": "Código / Errores",
            "single_image": "1 Imagen",
            "double_image": "2 Imágenes",
            "association": "Asociación"
        }

        for q in questions:
            if filter_type_code and q["question_type"] != filter_type_code:
                continue

            self.tree.insert("", tk.END, values=(
                q["id"],
                q["title"],
                q["category_name"],
                q["subcategory_name"] or "—",
                type_names.get(q["question_type"], q["question_type"]),
                q["points"],
                q["estimated_height"]
            ))

    def _on_question_selected(self, event=None):
        selected = self.tree.selection()
        self.preview_text.config(state="normal")
        self.preview_text.delete("1.0", tk.END)

        if not selected:
            self.preview_text.config(state="disabled")
            return

        q_id = int(self.tree.item(selected[0], "values")[0])
        q = database.get_question_by_id(q_id)
        if not q:
            self.preview_text.config(state="disabled")
            return

        lines = [
            f"📌 TÍTULO: {q['title']}",
            f"📂 CATEGORÍA: {q['category_name']}",
            f"🏷️ SUBCATEGORÍA: {q['subcategory_name'] or 'Sin clasificar'}",
            f"🎯 PUNTOS: {q['points']} pts  |  📏 ALTO ESTIMADO: {q['estimated_height']} px",
            "-" * 45,
            f"ENUNCIADO:\n{q['question_text']}\n"
        ]

        extra = {}
        if q["extra_data"]:
            try:
                extra = json.loads(q["extra_data"])
            except Exception:
                pass

        t = q["question_type"]
        if t in ("single_choice", "multiple_choice"):
            lines.append("OPCIONES:")
            for opt in extra.get("options", []):
                sym = "○" if t == "single_choice" else "□"
                lines.append(f"  {sym} {opt}")
        elif t == "true_false":
            lines.append("FORMATO FALSO Y VERDADERO:")
            stmts = extra.get("statements", [])
            if stmts:
                for s in stmts:
                    lines.append(f"  ( ) V   ( ) F   {s}")
            else:
                lines.append("  ( ) V   ( ) F   [Enunciado principal]")
        elif t == "development":
            lines.append(f"ZONA DE RESPUESTA: {extra.get('lines_count', 10)} renglones con líneas horizontales.")
        elif t == "code_writing":
            lines.append(f"ESPACIO PARA ESCRIBIR CÓDIGO: Recuadro en blanco de altura equivalente a {extra.get('lines_count', 12)} renglones (sin líneas impresas).")
        elif t == "code_analysis":
            lines.append("CÓDIGO:")
            lines.append(extra.get("code", ""))
            lines.append(f"\nPREGUNTA DE ANÁLISIS: {extra.get('sub_prompt', '')}")
            lines.append(f"ZONA DE RESPUESTA: {extra.get('lines_count', 5)} renglones.")
        elif t == "single_image":
            lines.append(f"IMAGEN: Ancho {extra.get('image_width_percent', 70)}%")
            if extra.get("text_before"):
                lines.append(f"Texto antes: {extra.get('text_before')}")
            if extra.get("text_after"):
                lines.append(f"Texto después: {extra.get('text_after')}")
            lines.append(f"Renglones: {extra.get('lines_count', 0)}")
        elif t == "double_image":
            lines.append(f"DOS IMÁGENES ({extra.get('layout', 'side_by_side')}):")
            lines.append(f"Imagen 1 ({extra.get('image1_width_percent', 48)}%) | Imagen 2 ({extra.get('image2_width_percent', 48)}%)")
            if extra.get("text_before"):
                lines.append(f"Texto antes: {extra.get('text_before')}")
            if extra.get("text_after_img1"):
                lines.append(f"Texto tras img 1: {extra.get('text_after_img1')}")
            if extra.get("text_after_img2"):
                lines.append(f"Texto tras img 2: {extra.get('text_after_img2')}")
        elif t == "association":
            lines.append("PARES DE ASOCIACIÓN:")
            for p in extra.get("pairs", []):
                lines.append(f"  {p.get('letter')}. {p.get('definition')}  -->  ( )  {p.get('concept')}")
            distractors = extra.get("extra_distractors", [])
            if distractors:
                lines.append(f"DISTRACTORES: {', '.join(distractors)}")

        self.preview_text.insert("1.0", "\n".join(lines))
        self.preview_text.config(state="disabled")

    def _new_question(self):
        selected_cat_name = self.cat_filter.get()
        init_cat_id = None
        if selected_cat_name != "Todas":
            for c in database.get_categories():
                if c["name"] == selected_cat_name:
                    init_cat_id = c["id"]
                    break

        dlg = QuestionEditorDialog(self, initial_category_id=init_cat_id)
        self.wait_window(dlg)
        if dlg.result:
            self.refresh_questions_list()
            if self.on_data_changed:
                self.on_data_changed()

    def _edit_question(self):
        selected = self.tree.selection()
        if not selected:
            messagebox.showwarning("Atención", "Seleccione una pregunta para editar.")
            return
        q_id = int(self.tree.item(selected[0], "values")[0])
        dlg = QuestionEditorDialog(self, question_id=q_id)
        self.wait_window(dlg)
        if dlg.result:
            self.refresh_questions_list()
            self._on_question_selected()
            if self.on_data_changed:
                self.on_data_changed()

    def _duplicate_question(self):
        selected = self.tree.selection()
        if not selected:
            messagebox.showwarning("Atención", "Seleccione una pregunta para duplicar.")
            return
        q_id = int(self.tree.item(selected[0], "values")[0])
        q = database.get_question_by_id(q_id)
        if not q:
            return

        new_title = f"{q['title']} (Copia)"
        database.save_question(
            category_id=q["category_id"],
            subcategory_id=q["subcategory_id"],
            question_type=q["question_type"],
            title=new_title,
            question_text=q["question_text"],
            points=q["points"],
            estimated_height=q["estimated_height"],
            extra_data=q["extra_data"]
        )
        self.refresh_questions_list()
        if self.on_data_changed:
            self.on_data_changed()

    def _delete_question(self):
        selected = self.tree.selection()
        if not selected:
            messagebox.showwarning("Atención", "Seleccione una pregunta para eliminar.")
            return
        q_id = int(self.tree.item(selected[0], "values")[0])
        title = self.tree.item(selected[0], "values")[1]

        if messagebox.askyesno("Confirmar Eliminación", f"¿Desea eliminar la pregunta '{title}'?"):
            database.delete_question(q_id)
            self.refresh_questions_list()
            self._on_question_selected()
            if self.on_data_changed:
                self.on_data_changed()

    def _add_selected_to_exam(self):
        selected = self.tree.selection()
        if not selected:
            messagebox.showwarning("Atención", "Seleccione una pregunta para añadir al examen.")
            return
        q_id = int(self.tree.item(selected[0], "values")[0])
        q = database.get_question_by_id(q_id)
        if q and self.on_add_to_exam:
            self.on_add_to_exam(q)
            messagebox.showinfo("Éxito", f"Pregunta '{q['title']}' añadida al examen actual.")

    def _export_questions_csv(self):
        file_path = filedialog.asksaveasfilename(
            title="Exportar Preguntas a CSV",
            defaultextension=".csv",
            filetypes=[("Archivos CSV", "*.csv"), ("Todos los archivos", "*.*")],
            initialfile="preguntas_exportadas.csv",
            parent=self
        )
        if not file_path:
            return
        try:
            count = importer_exporter.export_questions_to_csv(file_path)
            messagebox.showinfo("Exportación Exitosa", f"Se exportaron {count} preguntas a:\n{file_path}", parent=self)
        except Exception as ex:
            messagebox.showerror("Error al Exportar", f"Ocurrió un error:\n{ex}", parent=self)

    def _import_questions_csv(self):
        file_path = filedialog.askopenfilename(
            title="Importar Preguntas desde CSV",
            filetypes=[("Archivos CSV y TXT", "*.csv;*.txt"), ("Todos los archivos", "*.*")],
            parent=self
        )
        if not file_path:
            return
        try:
            count = importer_exporter.import_questions_from_csv(file_path)
            self.refresh_data()
            if self.on_data_changed:
                self.on_data_changed()
            messagebox.showinfo("Importación Exitosa", f"Se importaron {count} preguntas correctamente.", parent=self)
        except Exception as ex:
            messagebox.showerror("Error al Importar", f"No se pudo importar el archivo:\n{ex}", parent=self)
