"""
Pestaña Principal: Generador y Constructor de Exámenes.
Configuración de encabezado, tipografía, indicaciones, banco de ítems,
personalización de secciones finales (Resumen y Observaciones con página y renglones),
cálculo de altura, diagnóstico visual de páginas y exportación a HTML.
"""

import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import webbrowser
import os
import tempfile
from typing import Dict, Any, List, Optional

import database
import height_calculator
import html_generator
import importer_exporter
from ui_dialogs import SelectQuestionsDialog, AssignPageDialog, center_window


class ExamTab(ttk.Frame):
    def __init__(self, parent):
        super().__init__(parent, padding="10")
        self.current_exam_id: Optional[int] = None
        self.exam_items: List[Dict[str, Any]] = []

        self._build_ui()
        self.load_default_or_first_exam()

    def _build_ui(self):
        # Panel superior de acciones principales
        top_bar = ttk.Frame(self)
        top_bar.pack(fill=tk.X, pady=(0, 8))

        ttk.Label(top_bar, text="Generador de Exámenes Impresos", font=("Segoe UI", 12, "bold")).pack(side=tk.LEFT)

        ttk.Button(top_bar, text="📄 Exportar HTML...", command=self._export_html).pack(side=tk.RIGHT, padx=(4, 0))
        ttk.Button(top_bar, text="👁️ Vista Previa Navegador", command=self._preview_in_browser).pack(side=tk.RIGHT, padx=(4, 0))
        ttk.Button(top_bar, text="💾 Guardar Examen", command=self._save_exam_to_db).pack(side=tk.RIGHT, padx=(4, 0))
        ttk.Button(top_bar, text="📂 Cargar Examen...", command=self._show_load_exam_dialog).pack(side=tk.RIGHT, padx=(4, 0))
        ttk.Button(top_bar, text="➕ Nuevo Examen", command=self._new_blank_exam).pack(side=tk.RIGHT, padx=(4, 0))

        # Botones de Importar / Exportar JSON del examen
        ttk.Button(top_bar, text="📤 Exportar Examen (JSON)", command=self._export_exam_json).pack(side=tk.RIGHT, padx=(4, 0))
        ttk.Button(top_bar, text="📥 Importar Examen (JSON)", command=self._import_exam_json).pack(side=tk.RIGHT, padx=(4, 0))

        # PanedWindow Principal (Izquierda: Configuración; Derecha: Ítems y Paginación)
        main_paned = ttk.PanedWindow(self, orient=tk.HORIZONTAL)
        main_paned.pack(fill=tk.BOTH, expand=True)

        # =========================================================================
        # COLUMNA IZQUIERDA: CONFIGURACIÓN
        # =========================================================================
        left_container = ttk.Frame(main_paned, padding="5")
        main_paned.add(left_container, weight=2)

        left_canvas = tk.Canvas(left_container, borderwidth=0, highlightthickness=0)
        left_scroll = ttk.Scrollbar(left_container, orient=tk.VERTICAL, command=left_canvas.yview)
        left_content = ttk.Frame(left_canvas)

        left_content.bind(
            "<Configure>",
            lambda e: left_canvas.configure(scrollregion=left_canvas.bbox("all"))
        )
        left_canvas.create_window((0, 0), window=left_content, anchor="nw")
        left_canvas.configure(yscrollcommand=left_scroll.set)

        left_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        left_scroll.pack(side=tk.RIGHT, fill=tk.Y)

        # --- 1. ENCABEZADO DEL EXAMEN ---
        header_group = ttk.LabelFrame(left_content, text="🏫 Encabezado Institucional y Curso", padding="10")
        header_group.pack(fill=tk.X, pady=(0, 8))

        ttk.Label(header_group, text="Institución / Escuela:").grid(row=0, column=0, sticky=tk.W, pady=2)
        self.entry_institution = ttk.Entry(header_group, width=38)
        self.entry_institution.grid(row=0, column=1, columnspan=3, sticky=tk.EW, pady=2)

        ttk.Label(header_group, text="Sigla:").grid(row=1, column=0, sticky=tk.W, pady=2)
        self.entry_sigla = ttk.Entry(header_group, width=12)
        self.entry_sigla.grid(row=1, column=1, sticky=tk.W, pady=2)

        ttk.Label(header_group, text="Curso:").grid(row=1, column=2, sticky=tk.W, padx=(5, 2), pady=2)
        self.entry_curso = ttk.Entry(header_group, width=20)
        self.entry_curso.grid(row=1, column=3, sticky=tk.EW, pady=2)

        ttk.Label(header_group, text="Carrera:").grid(row=2, column=0, sticky=tk.W, pady=2)
        self.entry_carrera = ttk.Entry(header_group, width=18)
        self.entry_carrera.grid(row=2, column=1, sticky=tk.EW, pady=2)

        ttk.Label(header_group, text="Grupo:").grid(row=2, column=2, sticky=tk.W, padx=(5, 2), pady=2)
        self.entry_grupo = ttk.Entry(header_group, width=8)
        self.entry_grupo.grid(row=2, column=3, sticky=tk.W, pady=2)

        ttk.Label(header_group, text="Evaluación:").grid(row=3, column=0, sticky=tk.W, pady=2)
        self.entry_evaluacion = ttk.Entry(header_group, width=18)
        self.entry_evaluacion.grid(row=3, column=1, sticky=tk.EW, pady=2)

        ttk.Label(header_group, text="Duración:").grid(row=3, column=2, sticky=tk.W, padx=(5, 2), pady=2)
        self.entry_duracion = ttk.Entry(header_group, width=12)
        self.entry_duracion.grid(row=3, column=3, sticky=tk.W, pady=2)

        ttk.Label(header_group, text="Fecha:").grid(row=4, column=0, sticky=tk.W, pady=2)
        self.entry_fecha = ttk.Entry(header_group, width=18)
        self.entry_fecha.grid(row=4, column=1, sticky=tk.EW, pady=2)

        ttk.Label(header_group, text="Periodo:").grid(row=4, column=2, sticky=tk.W, padx=(5, 2), pady=2)
        self.entry_periodo = ttk.Entry(header_group, width=15)
        self.entry_periodo.grid(row=4, column=3, sticky=tk.EW, pady=2)

        ttk.Label(header_group, text="Profesor:").grid(row=5, column=0, sticky=tk.W, pady=2)
        self.entry_profesor = ttk.Entry(header_group, width=38)
        self.entry_profesor.grid(row=5, column=1, columnspan=3, sticky=tk.EW, pady=2)

        # --- 2. TIPOGRAFÍA Y FORMATO ---
        format_group = ttk.LabelFrame(left_content, text="⚙️ Tipografía y Formato de Impresión", padding="10")
        format_group.pack(fill=tk.X, pady=(0, 8))

        ttk.Label(format_group, text="Fuente:").grid(row=0, column=0, sticky=tk.W, pady=2)
        self.combo_font = ttk.Combobox(format_group, state="readonly", width=18)
        self.combo_font["values"] = [
            "Arial, sans-serif",
            "'Times New Roman', serif",
            "'Segoe UI', sans-serif",
            "'Calibri', sans-serif",
            "'Roboto', sans-serif",
            "'Georgia', serif",
            "'Courier New', monospace"
        ]
        self.combo_font.current(0)
        self.combo_font.grid(row=0, column=1, sticky=tk.W, pady=2)
        self.combo_font.bind("<<ComboboxSelected>>", lambda e: self.update_pagination_analysis())

        ttk.Label(format_group, text="Tamaño:").grid(row=0, column=2, sticky=tk.W, padx=(10, 2), pady=2)
        self.combo_size = ttk.Combobox(format_group, state="readonly", width=8)
        self.combo_size["values"] = ["10px", "11px", "12px", "13px", "14px"]
        self.combo_size.set("12px")
        self.combo_size.grid(row=0, column=3, sticky=tk.W, pady=2)
        self.combo_size.bind("<<ComboboxSelected>>", lambda e: self.update_pagination_analysis())

        ttk.Label(format_group, text="Interlineado:").grid(row=1, column=0, sticky=tk.W, pady=2)
        self.combo_lh = ttk.Combobox(format_group, state="readonly", width=8)
        self.combo_lh["values"] = ["1.2", "1.3", "1.4", "1.5", "1.6"]
        self.combo_lh.set("1.4")
        self.combo_lh.grid(row=1, column=1, sticky=tk.W, pady=2)
        self.combo_lh.bind("<<ComboboxSelected>>", lambda e: self.update_pagination_analysis())

        # --- SECCIONES FINALES CONFIGURABLES (RESUMEN Y OBSERVACIONES) ---
        sections_cfg_group = ttk.LabelFrame(left_content, text="📋 Secciones Opcionales de Calificación y Cierre", padding="10")
        sections_cfg_group.pack(fill=tk.X, pady=(0, 8))

        # Resumen de Calificación
        r_sum = ttk.Frame(sections_cfg_group)
        r_sum.pack(fill=tk.X, pady=3)

        self.var_show_summary = tk.BooleanVar(value=True)
        self.check_summary = ttk.Checkbutton(
            r_sum,
            text="Resumen de Calificación",
            variable=self.var_show_summary,
            command=self.update_pagination_analysis
        )
        self.check_summary.pack(side=tk.LEFT)

        ttk.Label(r_sum, text="en:").pack(side=tk.LEFT, padx=(10, 3))
        self.combo_summary_page = ttk.Combobox(r_sum, state="readonly", width=18)
        self.combo_summary_page.pack(side=tk.LEFT)
        self.combo_summary_page.bind("<<ComboboxSelected>>", lambda e: self.update_pagination_analysis())

        # Observaciones del Profesor
        r_obs = ttk.Frame(sections_cfg_group)
        r_obs.pack(fill=tk.X, pady=3)

        self.var_show_obs = tk.BooleanVar(value=True)
        self.check_obs = ttk.Checkbutton(
            r_obs,
            text="Observaciones del Profesor",
            variable=self.var_show_obs,
            command=self.update_pagination_analysis
        )
        self.check_obs.pack(side=tk.LEFT)

        ttk.Label(r_obs, text="en:").pack(side=tk.LEFT, padx=(10, 3))
        self.combo_obs_page = ttk.Combobox(r_obs, state="readonly", width=18)
        self.combo_obs_page.pack(side=tk.LEFT)
        self.combo_obs_page.bind("<<ComboboxSelected>>", lambda e: self.update_pagination_analysis())
        self._update_page_combos()

        r_obs_lines = ttk.Frame(sections_cfg_group)
        r_obs_lines.pack(fill=tk.X, pady=(3, 0))
        ttk.Label(r_obs_lines, text="Renglones de Observaciones:").pack(side=tk.LEFT, padx=(22, 5))
        self.spin_obs_lines = ttk.Spinbox(r_obs_lines, from_=0, to=25, increment=1, width=5)
        self.spin_obs_lines.set("8")
        self.spin_obs_lines.pack(side=tk.LEFT)
        self.spin_obs_lines.bind("<KeyRelease>", lambda e: self.update_pagination_analysis())
        self.spin_obs_lines.bind("<<Increment>>", lambda e: self.update_pagination_analysis())
        self.spin_obs_lines.bind("<<Decrement>>", lambda e: self.update_pagination_analysis())

        # --- 3. INDICACIONES GENERALES ---
        inst_group = ttk.LabelFrame(left_content, text="📋 Indicaciones Generales del Examen", padding="10")
        inst_group.pack(fill=tk.X, pady=(0, 8))

        row_sel = ttk.Frame(inst_group)
        row_sel.pack(fill=tk.X, pady=(0, 6))

        ttk.Label(row_sel, text="Cargar Plantilla:").pack(side=tk.LEFT, padx=(0, 4))
        self.combo_templates = ttk.Combobox(row_sel, state="readonly", width=22)
        self.combo_templates.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 4))
        ttk.Button(row_sel, text="Aplicar", command=self._apply_instruction_template).pack(side=tk.LEFT)

        self.text_instructions = tk.Text(inst_group, height=5, font=("Segoe UI", 9), wrap=tk.WORD)
        self.text_instructions.pack(fill=tk.X)

        self._refresh_instructions_combo()

        # =========================================================================
        # COLUMNA DERECHA: ÍTEMS, PAGINACIÓN Y DIAGNÓSTICO
        # =========================================================================
        right_container = ttk.Frame(main_paned, padding="5")
        main_paned.add(right_container, weight=3)

        # Panel de Métricas de Paginación en Tiempo Real
        self.page_status_frame = ttk.LabelFrame(right_container, text="📊 Paginación en Tiempo Real (Tamaño Carta)", padding="10")
        self.page_status_frame.pack(fill=tk.X, pady=(0, 8))

        self.page_meters_frame = ttk.Frame(self.page_status_frame)
        self.page_meters_frame.pack(fill=tk.X)

        self.lbl_global_summary = ttk.Label(self.page_status_frame, text="", font=("Segoe UI", 9, "bold"))
        self.lbl_global_summary.pack(anchor=tk.W, pady=(6, 0))

        # Barra de herramientas de ítems
        tools_frame = ttk.Frame(right_container)
        tools_frame.pack(fill=tk.X, pady=(0, 6))

        ttk.Button(tools_frame, text="➕ Agregar Preguntas...", command=self._open_add_questions_dialog).pack(side=tk.LEFT, padx=(0, 4))
        ttk.Button(tools_frame, text="🗑️ Quitar", command=self._remove_selected_item).pack(side=tk.LEFT, padx=(0, 4))
        ttk.Button(tools_frame, text="▲ Subir", command=self._move_item_up).pack(side=tk.LEFT, padx=(0, 4))
        ttk.Button(tools_frame, text="▼ Bajar", command=self._move_item_down).pack(side=tk.LEFT, padx=(0, 4))
        ttk.Button(tools_frame, text="📄 Asignar Página...", command=self._open_assign_page_dialog).pack(side=tk.LEFT, padx=(0, 4))
        ttk.Button(tools_frame, text="✨ Auto-Distribuir Paginación", command=self._auto_paginate).pack(side=tk.RIGHT)

        # Tabla de Ítems del Examen
        tree_container = ttk.Frame(right_container)
        tree_container.pack(fill=tk.BOTH, expand=True)

        cols = ("num", "page", "title", "section", "type", "points", "height")
        self.items_tree = ttk.Treeview(tree_container, columns=cols, show="headings", selectmode="extended")
        self.items_tree.heading("num", text="#")
        self.items_tree.heading("page", text="Página")
        self.items_tree.heading("title", text="Título / Pregunta")
        self.items_tree.heading("section", text="Sección (Auto: Parte I, II, ...)")
        self.items_tree.heading("type", text="Tipo")
        self.items_tree.heading("points", text="Pts")
        self.items_tree.heading("height", text="Alto (px)")

        self.items_tree.column("num", width=30, anchor=tk.CENTER)
        self.items_tree.column("page", width=55, anchor=tk.CENTER)
        self.items_tree.column("title", width=220)
        self.items_tree.column("section", width=160)
        self.items_tree.column("type", width=110)
        self.items_tree.column("points", width=45, anchor=tk.CENTER)
        self.items_tree.column("height", width=65, anchor=tk.CENTER)

        tree_scroll = ttk.Scrollbar(tree_container, orient=tk.VERTICAL, command=self.items_tree.yview)
        self.items_tree.configure(yscrollcommand=tree_scroll.set)

        self.items_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        tree_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        self.items_tree.bind("<Double-1>", lambda e: self._quick_edit_item())
        self.items_tree.bind("<Button-3>", self._show_tree_context_menu)
        self.items_tree.bind("<Alt-Up>", lambda e: (self._move_item_up(), "break")[1])
        self.items_tree.bind("<Alt-Down>", lambda e: (self._move_item_down(), "break")[1])
        self.items_tree.bind("<Control-Up>", lambda e: (self._move_item_up(), "break")[1])
        self.items_tree.bind("<Control-Down>", lambda e: (self._move_item_down(), "break")[1])

    def _update_page_combos(self):
        max_p = max([int(it.get("page_number", 1)) for it in self.exam_items], default=4)
        vals = ["Última Página (Auto)"] + [f"Página {i}" for i in range(1, max(max_p + 2, 6))]

        cur_sum = self.combo_summary_page.get()
        cur_obs = self.combo_obs_page.get()

        self.combo_summary_page["values"] = vals
        self.combo_obs_page["values"] = vals

        self.combo_summary_page.set(cur_sum if cur_sum in vals else "Última Página (Auto)")
        self.combo_obs_page.set(cur_obs if cur_obs in vals else "Última Página (Auto)")

    def _parse_selected_page(self, combo_str: str) -> int:
        if "Auto" in combo_str or "Última" in combo_str or not combo_str:
            return 0
        try:
            return int(combo_str.replace("Página", "").strip())
        except Exception:
            return 0

    def _refresh_instructions_combo(self):
        templates = database.get_instructions()
        self.combo_templates["values"] = [t["title"] for t in templates]
        if templates:
            self.combo_templates.current(0)

    def _apply_instruction_template(self):
        selected_title = self.combo_templates.get()
        templates = database.get_instructions()
        for t in templates:
            if t["title"] == selected_title:
                self.text_instructions.delete("1.0", tk.END)
                self.text_instructions.insert("1.0", t["content"])
                break

    def load_default_or_first_exam(self):
        exams = database.get_exams()
        if exams:
            self.load_exam(exams[0]["id"])
        else:
            self._new_blank_exam()

    def load_exam(self, exam_id: int):
        exam = database.get_exam_by_id(exam_id)
        if not exam:
            return

        self.current_exam_id = exam["id"]
        self.entry_evaluacion.delete(0, tk.END)
        self.entry_evaluacion.insert(0, exam.get("title", ""))

        self.entry_institution.delete(0, tk.END)
        self.entry_institution.insert(0, exam.get("institution", ""))

        self.entry_sigla.delete(0, tk.END)
        self.entry_sigla.insert(0, exam.get("course_code", ""))

        self.entry_curso.delete(0, tk.END)
        self.entry_curso.insert(0, exam.get("course_name", ""))

        self.entry_carrera.delete(0, tk.END)
        self.entry_carrera.insert(0, exam.get("career", ""))

        self.entry_profesor.delete(0, tk.END)
        self.entry_profesor.insert(0, exam.get("professor", ""))

        self.entry_grupo.delete(0, tk.END)
        self.entry_grupo.insert(0, exam.get("group_name", ""))

        self.entry_fecha.delete(0, tk.END)
        self.entry_fecha.insert(0, exam.get("exam_date", ""))

        self.entry_periodo.delete(0, tk.END)
        self.entry_periodo.insert(0, exam.get("period", ""))

        self.entry_duracion.delete(0, tk.END)
        self.entry_duracion.insert(0, exam.get("duration", ""))

        self.combo_font.set(exam.get("font_family", "Arial, sans-serif"))
        self.combo_size.set(exam.get("font_size", "12px"))
        self.combo_lh.set(exam.get("line_height", "1.4"))

        self.var_show_summary.set(bool(exam.get("show_grading_summary", True)))
        sum_pg = int(exam.get("summary_page", 0))
        self.combo_summary_page.set(f"Página {sum_pg}" if sum_pg > 0 else "Última Página (Auto)")

        self.var_show_obs.set(bool(exam.get("show_observations", True)))
        self.spin_obs_lines.set(str(exam.get("observations_lines", 8)))
        obs_pg = int(exam.get("observations_page", 0))
        self.combo_obs_page.set(f"Página {obs_pg}" if obs_pg > 0 else "Última Página (Auto)")

        self.text_instructions.delete("1.0", tk.END)
        self.text_instructions.insert("1.0", exam.get("instructions_text", ""))

        self.exam_items = exam.get("items", [])
        self._update_page_combos()
        self.refresh_items_tree()

    def _new_blank_exam(self):
        self.current_exam_id = None
        self.entry_evaluacion.delete(0, tk.END)
        self.entry_evaluacion.insert(0, "Quiz en Papel #01")

        self.entry_institution.delete(0, tk.END)
        self.entry_institution.insert(0, "Universidad de Costa Rica — Escuela de Ingeniería Industrial")

        self.entry_sigla.delete(0, tk.END)
        self.entry_sigla.insert(0, "II-1119")

        self.entry_curso.delete(0, tk.END)
        self.entry_curso.insert(0, "Fundamentos de Tecnología Digital")

        self.entry_carrera.delete(0, tk.END)
        self.entry_carrera.insert(0, "Ingeniería Industrial")

        self.entry_profesor.delete(0, tk.END)
        self.entry_profesor.insert(0, "Profesor del Curso")

        self.entry_grupo.delete(0, tk.END)
        self.entry_grupo.insert(0, "01")

        self.entry_fecha.delete(0, tk.END)
        self.entry_fecha.insert(0, "______/______/2026")

        self.entry_periodo.delete(0, tk.END)
        self.entry_periodo.insert(0, "I Ciclo Lectivo 2026")

        self.entry_duracion.delete(0, tk.END)
        self.entry_duracion.insert(0, "45 minutos")

        self.combo_summary_page.set("Última Página (Auto)")
        self.combo_obs_page.set("Última Página (Auto)")
        self.spin_obs_lines.set("8")

        self.exam_items = []
        self._update_page_combos()
        self.refresh_items_tree()

    def _gather_exam_dict(self) -> Dict[str, Any]:
        try:
            obs_lines = int(self.spin_obs_lines.get())
        except Exception:
            obs_lines = 8

        return {
            "id": self.current_exam_id,
            "title": self.entry_evaluacion.get().strip() or "Examen",
            "institution": self.entry_institution.get().strip(),
            "course_code": self.entry_sigla.get().strip(),
            "course_name": self.entry_curso.get().strip(),
            "career": self.entry_carrera.get().strip(),
            "professor": self.entry_profesor.get().strip(),
            "group_name": self.entry_grupo.get().strip(),
            "exam_date": self.entry_fecha.get().strip(),
            "period": self.entry_periodo.get().strip(),
            "duration": self.entry_duracion.get().strip(),
            "instructions_text": self.text_instructions.get("1.0", tk.END).strip(),
            "font_family": self.combo_font.get(),
            "font_size": self.combo_size.get(),
            "line_height": self.combo_lh.get(),
            "show_grading_summary": self.var_show_summary.get(),
            "summary_page": self._parse_selected_page(self.combo_summary_page.get()),
            "show_observations": self.var_show_obs.get(),
            "observations_lines": obs_lines,
            "observations_page": self._parse_selected_page(self.combo_obs_page.get())
        }

    def _save_exam_to_db(self):
        exam_data = self._gather_exam_dict()
        exam_id = database.save_exam_full(exam_data, self.exam_items)
        self.current_exam_id = exam_id
        messagebox.showinfo("Guardado", f"Examen '{exam_data['title']}' guardado correctamente en la base de datos.")

    def _show_load_exam_dialog(self):
        exams = database.get_exams()
        if not exams:
            messagebox.showinfo("Información", "No hay exámenes guardados en la base de datos.")
            return

        win = tk.Toplevel(self)
        win.title("Cargar Examen Guardado")
        center_window(win, 560, 340)
        win.transient(self)
        win.grab_set()

        f = ttk.Frame(win, padding="15")
        f.pack(fill=tk.BOTH, expand=True)

        ttk.Label(f, text="Seleccione un examen para cargar:", font=("Segoe UI", 9, "bold")).pack(anchor=tk.W, pady=(0, 6))

        tree = ttk.Treeview(f, columns=("id", "title", "course", "date"), show="headings", selectmode="browse")
        tree.heading("id", text="ID")
        tree.heading("title", text="Título / Evaluación")
        tree.heading("course", text="Curso")
        tree.heading("date", text="Fecha de Actualización")

        tree.column("id", width=35, anchor=tk.CENTER)
        tree.column("title", width=190)
        tree.column("course", width=180)
        tree.column("date", width=120)

        tree.pack(fill=tk.BOTH, expand=True)

        for ex in exams:
            tree.insert("", tk.END, values=(ex["id"], ex["title"], f"{ex['course_code']} {ex['course_name']}", ex["updated_at"]))

        btn_bar = ttk.Frame(f)
        btn_bar.pack(fill=tk.X, pady=(10, 0))

        ttk.Button(btn_bar, text="Cancelar", command=win.destroy).pack(side=tk.RIGHT, padx=(5, 0))

        def load_sel():
            sel = tree.selection()
            if not sel:
                return
            ex_id = int(tree.item(sel[0], "values")[0])
            self.load_exam(ex_id)
            win.destroy()

        ttk.Button(btn_bar, text="Cargar", command=load_sel).pack(side=tk.RIGHT)

    def _export_exam_json(self):
        if not self.exam_items:
            messagebox.showwarning("Atención", "No hay preguntas en el examen actual para exportar.")
            return

        default_name = f"examen_{self.entry_sigla.get().strip().replace(' ', '_')}.json"
        file_path = filedialog.asksaveasfilename(
            title="Exportar Examen a JSON",
            defaultextension=".json",
            filetypes=[("Archivos JSON", "*.json"), ("Todos los archivos", "*.*")],
            initialfile=default_name,
            parent=self
        )
        if not file_path:
            return

        # Asegurar guardado previo
        self._save_exam_to_db()
        try:
            importer_exporter.export_exam_to_json(self.current_exam_id, file_path)
            messagebox.showinfo("Exportación Exitosa", f"Examen exportado correctamente a:\n{file_path}", parent=self)
        except Exception as ex:
            messagebox.showerror("Error al Exportar", f"Ocurrió un error:\n{ex}", parent=self)

    def _import_exam_json(self):
        file_path = filedialog.askopenfilename(
            title="Importar Examen desde JSON",
            filetypes=[("Archivos JSON", "*.json"), ("Todos los archivos", "*.*")],
            parent=self
        )
        if not file_path:
            return
        try:
            new_id = importer_exporter.import_exam_from_json(file_path)
            self.load_exam(new_id)
            messagebox.showinfo("Importación Exitosa", "Examen importado y cargado en pantalla con éxito.", parent=self)
        except Exception as ex:
            messagebox.showerror("Error al Importar", f"No se pudo importar el examen:\n{ex}", parent=self)

    # =========================================================================
    # GESTIÓN DE ÍTEMS Y PAGINACIÓN
    # =========================================================================

    def refresh_items_tree(self):
        for item in self.items_tree.get_children():
            self.items_tree.delete(item)

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

        self.exam_items.sort(key=lambda x: (int(x.get("page_number", 1)), int(x.get("item_order", 0))))

        # Mapeo romano dinámico de secciones según orden de aparición
        sec_order = []
        for it in self.exam_items:
            s_id = it.get("section_id", it.get("category_id", 1))
            if s_id not in sec_order:
                sec_order.append(s_id)

        sec_roman_map = {}
        for idx, s_id in enumerate(sec_order, start=1):
            sec_roman_map[s_id] = html_generator.to_roman(idx)

        for idx, it in enumerate(self.exam_items, start=1):
            it["item_order"] = idx
            q_title = it.get("question_title") or it.get("title", "")
            q_type = it.get("question_type", "single_choice")

            s_id = it.get("section_id", it.get("category_id", 1))
            raw_sec_name = it.get("category_name") or it.get("section_title", "")
            clean_sec = html_generator.clean_section_name(raw_sec_name)
            roman = sec_roman_map.get(s_id, "I")
            q_sec_display = f"Parte {roman}: {clean_sec}"

            pts = it.get("custom_points") or it.get("points") or 5.0
            h = it.get("custom_height") or it.get("estimated_height") or 80
            pg = it.get("page_number", 1)

            self.items_tree.insert("", tk.END, iid=str(idx - 1), values=(
                idx,
                f"Pág {pg}",
                q_title,
                q_sec_display,
                type_names.get(q_type, q_type),
                pts,
                h
            ))

        self._update_page_combos()
        self.update_pagination_analysis()

    def update_pagination_analysis(self):
        for w in self.page_meters_frame.winfo_children():
            w.destroy()

        if not self.exam_items:
            ttk.Label(self.page_meters_frame, text="No hay preguntas añadidas al examen.", font=("Segoe UI", 9, "italic")).pack(anchor=tk.W)
            self.lbl_global_summary.config(text="Puntaje Total: 0 puntos  |  NOTA siempre /100")
            return

        try:
            obs_lines = int(self.spin_obs_lines.get())
        except Exception:
            obs_lines = 8

        report = height_calculator.analyze_exam_pagination(
            exam_items=self.exam_items,
            show_summary_table=self.var_show_summary.get(),
            summary_page=self._parse_selected_page(self.combo_summary_page.get()),
            show_observations=self.var_show_obs.get(),
            observations_lines=obs_lines,
            observations_page=self._parse_selected_page(self.combo_obs_page.get()),
            font_size_str=self.combo_size.get(),
            line_height_str=self.combo_lh.get()
        )

        total_pts = sum(float(it.get("custom_points") or it.get("points") or 0.0) for it in self.exam_items)
        pts_str = int(total_pts) if total_pts.is_integer() else round(total_pts, 1)

        self.lbl_global_summary.config(
            text=f"🎯 Puntos Totales: {pts_str} pts  |  Total Páginas: {report['total_pages']}  |  NOTA fija: /100  |  Preguntas: {len(self.exam_items)}"
        )

        for r in report["pages_report"]:
            row = ttk.Frame(self.page_meters_frame)
            row.pack(fill=tk.X, pady=2)

            pg_lbl = ttk.Label(row, text=f"Página {r['page']}:", width=9, font=("Segoe UI", 8, "bold"))
            pg_lbl.pack(side=tk.LEFT)

            prog = ttk.Progressbar(row, orient=tk.HORIZONTAL, length=140, mode="determinate")
            prog["maximum"] = 100
            prog["value"] = min(100, r["percentage"])
            prog.pack(side=tk.LEFT, padx=(0, 8))

            status_text = f"{r['percentage']}% ({r['used_px']}/{r['capacity_px']} px) [{r['status']}] - {r['item_count']} ítems"
            lbl_stat = tk.Label(row, text=status_text, fg=r["status_color"], font=("Segoe UI", 8, "bold"))
            lbl_stat.pack(side=tk.LEFT)

    def _open_add_questions_dialog(self):
        current_max_page = max([int(it.get("page_number", 1)) for it in self.exam_items], default=1)
        dlg = SelectQuestionsDialog(self, target_page=current_max_page)
        self.wait_window(dlg)

        if dlg.selected_questions:
            for q in dlg.selected_questions:
                self.add_question_to_exam(q, page_num=q.get("target_page", current_max_page))

    def add_question_to_exam(self, question_dict: Dict[str, Any], page_num: int = 1):
        new_item = {
            "question_id": question_dict["id"],
            "section_id": question_dict["category_id"],
            "category_name": question_dict.get("category_name", ""),
            "section_title": question_dict.get("section_title", ""),
            "question_title": question_dict.get("title", ""),
            "question_text": question_dict.get("question_text", ""),
            "question_type": question_dict.get("question_type", "single_choice"),
            "points": question_dict.get("points", 5.0),
            "estimated_height": question_dict.get("estimated_height", 80),
            "extra_data": question_dict.get("extra_data", {}),
            "page_number": page_num,
            "item_order": len(self.exam_items) + 1
        }
        self.exam_items.append(new_item)
        self.refresh_items_tree()

    def _remove_selected_item(self):
        selected = self.items_tree.selection()
        if not selected:
            messagebox.showwarning("Atención", "Seleccione uno o más ítems para quitar.")
            return

        indices = sorted([int(i) for i in selected], reverse=True)
        for idx in indices:
            if 0 <= idx < len(self.exam_items):
                del self.exam_items[idx]

        self.refresh_items_tree()

    def _move_item_up(self):
        selected = self.items_tree.selection()
        if not selected:
            messagebox.showinfo("Mover Pregunta", "Seleccione una pregunta en la lista para subirla.", parent=self)
            return
        idx = int(selected[0])
        if idx <= 0:
            return

        item_curr = self.exam_items[idx]
        item_prev = self.exam_items[idx - 1]

        # Si están en páginas distintas, intercambiamos sus números de página
        p_curr = int(item_curr.get("page_number", 1))
        p_prev = int(item_prev.get("page_number", 1))
        if p_curr != p_prev:
            item_curr["page_number"] = p_prev
            item_prev["page_number"] = p_curr

        # Intercambiar elementos en la lista
        self.exam_items[idx - 1], self.exam_items[idx] = self.exam_items[idx], self.exam_items[idx - 1]

        # Actualizar item_order secuencial
        for i, it in enumerate(self.exam_items, start=1):
            it["item_order"] = i

        self.refresh_items_tree()
        self.items_tree.selection_set(str(idx - 1))
        self.items_tree.see(str(idx - 1))

    def _move_item_down(self):
        selected = self.items_tree.selection()
        if not selected:
            messagebox.showinfo("Mover Pregunta", "Seleccione una pregunta en la lista para bajarla.", parent=self)
            return
        idx = int(selected[0])
        if idx >= len(self.exam_items) - 1:
            return

        item_curr = self.exam_items[idx]
        item_next = self.exam_items[idx + 1]

        # Si están en páginas distintas, intercambiamos sus números de página
        p_curr = int(item_curr.get("page_number", 1))
        p_next = int(item_next.get("page_number", 1))
        if p_curr != p_next:
            item_curr["page_number"] = p_next
            item_next["page_number"] = p_curr

        # Intercambiar elementos en la lista
        self.exam_items[idx], self.exam_items[idx + 1] = self.exam_items[idx + 1], self.exam_items[idx]

        # Actualizar item_order secuencial
        for i, it in enumerate(self.exam_items, start=1):
            it["item_order"] = i

        self.refresh_items_tree()
        self.items_tree.selection_set(str(idx + 1))
        self.items_tree.see(str(idx + 1))

    def _show_tree_context_menu(self, event):
        row_id = self.items_tree.identify_row(event.y)
        if row_id:
            self.items_tree.selection_set(row_id)
        if not self.items_tree.selection():
            return

        menu = tk.Menu(self, tearoff=0)
        menu.add_command(label="▲ Subir posición (Alt+Arriba)", command=self._move_item_up)
        menu.add_command(label="▼ Bajar posición (Alt+Abajo)", command=self._move_item_down)
        menu.add_separator()
        menu.add_command(label="📄 Asignar a otra página...", command=self._open_assign_page_dialog)
        menu.add_command(label="✏️ Editar puntaje / alto...", command=self._quick_edit_item)
        menu.add_separator()
        menu.add_command(label="🗑️ Quitar del examen", command=self._remove_selected_item)
        menu.tk_popup(event.x_root, event.y_root)

    def _open_assign_page_dialog(self):
        selected = self.items_tree.selection()
        if not selected:
            messagebox.showwarning("Atención", "Seleccione los ítems a los que desea reasignar la página.")
            return

        first_idx = int(selected[0])
        curr_page = self.exam_items[first_idx].get("page_number", 1)

        dlg = AssignPageDialog(self, current_page=curr_page)
        self.wait_window(dlg)

        if dlg.selected_page is not None:
            for item_id in selected:
                idx = int(item_id)
                self.exam_items[idx]["page_number"] = dlg.selected_page
            self.refresh_items_tree()

    def _auto_paginate(self):
        if not self.exam_items:
            return

        try:
            obs_lines = int(self.spin_obs_lines.get())
        except Exception:
            obs_lines = 8

        distributed = height_calculator.auto_distribute_items(
            items=self.exam_items,
            show_summary_table=self.var_show_summary.get(),
            summary_page=self._parse_selected_page(self.combo_summary_page.get()),
            show_observations=self.var_show_obs.get(),
            observations_lines=obs_lines,
            observations_page=self._parse_selected_page(self.combo_obs_page.get()),
            font_size_str=self.combo_size.get(),
            line_height_str=self.combo_lh.get()
        )
        self.exam_items = distributed
        self.refresh_items_tree()
        messagebox.showinfo("Auto-Paginación", "Preguntas distribuidas automáticamente según capacidad de página Carta.")

    def _quick_edit_item(self):
        selected = self.items_tree.selection()
        if not selected:
            return
        idx = int(selected[0])
        item = self.exam_items[idx]

        win = tk.Toplevel(self)
        win.title("Modificar Ítem en este Examen")
        win.resizable(False, False)
        center_window(win, 380, 240)
        win.transient(self)
        win.grab_set()

        f = ttk.Frame(win, padding="15")
        f.pack(fill=tk.BOTH, expand=True)

        ttk.Label(f, text=f"Pregunta: {item.get('question_title')}", font=("Segoe UI", 9, "bold")).pack(anchor=tk.W, pady=(0, 10))

        r1 = ttk.Frame(f)
        r1.pack(fill=tk.X, pady=4)
        ttk.Label(r1, text="Página Asignada:").pack(side=tk.LEFT, padx=(0, 8))
        spin_p = ttk.Spinbox(r1, from_=1, to=30, width=6)
        spin_p.set(str(item.get("page_number", 1)))
        spin_p.pack(side=tk.LEFT)

        r2 = ttk.Frame(f)
        r2.pack(fill=tk.X, pady=4)
        ttk.Label(r2, text="Puntos:").pack(side=tk.LEFT, padx=(0, 8))
        spin_pts = ttk.Spinbox(r2, from_=0.5, to=100.0, increment=0.5, width=8)
        spin_pts.set(str(item.get("custom_points") or item.get("points") or 5.0))
        spin_pts.pack(side=tk.LEFT)

        r3 = ttk.Frame(f)
        r3.pack(fill=tk.X, pady=4)
        ttk.Label(r3, text="Alto Est. (px):").pack(side=tk.LEFT, padx=(0, 8))
        spin_h = ttk.Spinbox(r3, from_=20, to=1200, increment=10, width=8)
        spin_h.set(str(item.get("custom_height") or item.get("estimated_height") or 80))
        spin_h.pack(side=tk.LEFT)

        btn_bar = ttk.Frame(f)
        btn_bar.pack(fill=tk.X, pady=(15, 0))
        ttk.Button(btn_bar, text="Cancelar", command=win.destroy).pack(side=tk.RIGHT, padx=(5, 0))

        def save():
            try:
                item["page_number"] = int(spin_p.get())
                item["custom_points"] = float(spin_pts.get())
                item["custom_height"] = int(spin_h.get())
                win.destroy()
                self.refresh_items_tree()
            except Exception as ex:
                messagebox.showerror("Error", f"Valores no válidos: {ex}", parent=win)

        ttk.Button(btn_bar, text="Aceptar", command=save).pack(side=tk.RIGHT)

    # =========================================================================
    # EXPORTACIÓN Y VISTA PREVIA
    # =========================================================================

    def _generate_current_html(self) -> str:
        exam_data = self._gather_exam_dict()
        return html_generator.generate_exam_html(exam_data, self.exam_items)

    def _preview_in_browser(self):
        if not self.exam_items:
            messagebox.showwarning("Atención", "Agregue al menos una pregunta antes de generar la vista previa.")
            return

        html_content = self._generate_current_html()
        temp_file = os.path.join(tempfile.gettempdir(), "examen_preview.html")
        with open(temp_file, "w", encoding="utf-8") as f:
            f.write(html_content)

        webbrowser.open(f"file:///{temp_file.replace(os.sep, '/')}")

    def _export_html(self):
        if not self.exam_items:
            messagebox.showwarning("Atención", "Agregue al menos una pregunta antes de exportar.")
            return

        default_name = f"{self.entry_evaluacion.get().strip().replace(' ', '_')}.html"
        save_path = filedialog.asksaveasfilename(
            defaultextension=".html",
            filetypes=[("Archivos HTML", "*.html"), ("Todos los archivos", "*.*")],
            initialfile=default_name,
            title="Guardar Examen en HTML"
        )
        if not save_path:
            return

        html_content = self._generate_current_html()
        with open(save_path, "w", encoding="utf-8") as f:
            f.write(html_content)

        if messagebox.askyesno("Exportación Exitosa", f"Examen exportado correctamente a:\n{save_path}\n\n¿Desea abrirlo en su navegador ahora mismo para imprimir?"):
            webbrowser.open(f"file:///{os.path.abspath(save_path).replace(os.sep, '/')}")
