"""
Diálogos auxiliares y ventanas emergentes para la interfaz gráfica Tkinter.
Incluye soporte para preguntas de selección, falso y verdadero, desarrollo,
escritura de código en blanco, análisis de código, 1 imagen, 2 imágenes y asociación.
"""

import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import json
import os
import re
from typing import Optional, Dict, Any, List

import database
import height_calculator
import importer_exporter



def center_window(window: tk.Wm, width: Optional[int] = None, height: Optional[int] = None):
    """
    Centra una ventana respecto a la pantalla del monitor.
    """
    window.update_idletasks()
    w = width if width is not None else window.winfo_reqwidth()
    h = height if height is not None else window.winfo_reqheight()
    screen_w = window.winfo_screenwidth()
    screen_h = window.winfo_screenheight()
    x = max(0, (screen_w - w) // 2)
    y = max(0, (screen_h - h) // 2)
    window.geometry(f"{w}x{h}+{x}+{y}")


class QuestionEditorDialog(tk.Toplevel):
    """
    Diálogo para crear o editar una pregunta completa del banco,
    con editores dinámicos para todos los tipos de preguntas soportados.
    """
    def __init__(self, parent, question_id: Optional[int] = None, initial_category_id: Optional[int] = None):
        super().__init__(parent)
        self.question_id = question_id
        self.initial_category_id = initial_category_id
        self.result = False

        # Datos en memoria para imágenes en base64
        self.img1_b64 = None
        self.img2_b64 = None

        self.title("Editar Pregunta" if question_id else "Nueva Pregunta")
        self.minsize(800, 650)
        center_window(self, 920, 800)
        self.transient(parent)
        self.grab_set()

        self.categories = database.get_categories()
        self.subcategories = database.get_subcategories()

        self._build_ui()
        if question_id:
            self._load_question(question_id)
        elif initial_category_id:
            self.cat_combo.set(self._get_cat_name(initial_category_id))
            self._on_category_changed()

    def _get_cat_name(self, cat_id: int) -> str:
        for c in self.categories:
            if c["id"] == cat_id:
                return c["name"]
        return ""

    def _build_ui(self):
        container = ttk.Frame(self, padding="15")
        container.pack(fill=tk.BOTH, expand=True)

        # Fila 1: Categoría y Subcategoría
        row1 = ttk.Frame(container)
        row1.pack(fill=tk.X, pady=(0, 10))

        ttk.Label(row1, text="Categoría (Sección):", font=("Segoe UI", 9, "bold")).grid(row=0, column=0, sticky=tk.W, padx=(0, 5))
        self.cat_combo = ttk.Combobox(row1, state="readonly", width=28)
        self.cat_combo["values"] = [c["name"] for c in self.categories]
        self.cat_combo.grid(row=0, column=1, sticky=tk.W, padx=(0, 15))
        self.cat_combo.bind("<<ComboboxSelected>>", self._on_category_changed)

        ttk.Label(row1, text="Subcategoría:", font=("Segoe UI", 9, "bold")).grid(row=0, column=2, sticky=tk.W, padx=(0, 5))
        self.subcat_combo = ttk.Combobox(row1, state="readonly", width=25)
        self.subcat_combo.grid(row=0, column=3, sticky=tk.W)

        # Fila 2: Tipo de Pregunta, Puntos y Alto Estimado
        row2 = ttk.Frame(container)
        row2.pack(fill=tk.X, pady=(0, 10))

        ttk.Label(row2, text="Tipo de Pregunta:", font=("Segoe UI", 9, "bold")).grid(row=0, column=0, sticky=tk.W, padx=(0, 5))
        self.type_combo = ttk.Combobox(row2, state="readonly", width=30)
        self.type_combo["values"] = [
            "Selección Única",
            "Selección Múltiple",
            "Falso y Verdadero",
            "Desarrollo (con Renglones)",
            "Escritura de Código (Recuadro en Blanco)",
            "Identificación de Errores / Código",
            "Pregunta con 1 Imagen",
            "Pregunta con 2 Imágenes",
            "Asociación de Conceptos"
        ]
        self.type_combo.current(0)
        self.type_combo.grid(row=0, column=1, sticky=tk.W, padx=(0, 15))
        self.type_combo.bind("<<ComboboxSelected>>", self._on_type_changed)

        ttk.Label(row2, text="Puntos:", font=("Segoe UI", 9, "bold")).grid(row=0, column=2, sticky=tk.W, padx=(0, 5))
        self.points_spin = ttk.Spinbox(row2, from_=0.5, to=100.0, increment=0.5, width=7)
        self.points_spin.set("5.0")
        self.points_spin.grid(row=0, column=3, sticky=tk.W, padx=(0, 15))

        ttk.Label(row2, text="Alto Est. (px):", font=("Segoe UI", 9, "bold")).grid(row=0, column=4, sticky=tk.W, padx=(0, 5))
        self.height_spin = ttk.Spinbox(row2, from_=30, to=3000, increment=10, width=7)
        self.height_spin.set("80")
        self.height_spin.grid(row=0, column=5, sticky=tk.W)

        # Fila 3: Título corto / Resumen
        row3 = ttk.Frame(container)
        row3.pack(fill=tk.X, pady=(0, 10))
        ttk.Label(row3, text="Título / Resumen del Ítem:", font=("Segoe UI", 9, "bold")).pack(anchor=tk.W, pady=(0, 2))
        self.title_entry = ttk.Entry(row3)
        self.title_entry.pack(fill=tk.X)

        # Fila 4: Enunciado de la Pregunta (con Scrollbar y tamaño dinámico amplio)
        self.row4 = ttk.Frame(container)
        self.row4.pack(fill=tk.BOTH, expand=True, pady=(0, 8))

        row4_hdr = ttk.Frame(self.row4)
        row4_hdr.pack(fill=tk.X, pady=(0, 3))
        ttk.Label(
            row4_hdr,
            text="Enunciado de la Pregunta / Instrucciones (admite <table>, <pre>, <code>, <b>, <u>, etc.):",
            font=("Segoe UI", 9, "bold")
        ).pack(side=tk.LEFT)

        text_container = ttk.Frame(self.row4)
        text_container.pack(fill=tk.BOTH, expand=True)

        text_scroll = ttk.Scrollbar(text_container, orient=tk.VERTICAL)
        self.text_widget = tk.Text(
            text_container,
            height=12,
            font=("Segoe UI", 10),
            wrap=tk.WORD,
            yscrollcommand=text_scroll.set
        )
        text_scroll.config(command=self.text_widget.yview)
        text_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        self.text_widget.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.text_widget.bind("<KeyRelease>", lambda e: self._on_text_modified())

        # Contenedor para Editor Dinámico según el Tipo
        self.dynamic_frame = ttk.LabelFrame(container, text="Detalles Específicos del Tipo de Pregunta", padding="10")
        self.dynamic_frame.pack(fill=tk.X, expand=False, pady=(0, 10))

        # Barra de botones inferior
        btn_bar = ttk.Frame(container)
        btn_bar.pack(fill=tk.X)

        self.btn_auto_height = ttk.Button(btn_bar, text="🔄 Recalcular Alto", command=self._recalculate_height)
        self.btn_auto_height.pack(side=tk.LEFT)

        ttk.Button(btn_bar, text="Cancelar", command=self.destroy).pack(side=tk.RIGHT, padx=(5, 0))
        ttk.Button(btn_bar, text="💾 Guardar Pregunta", command=self._save_question).pack(side=tk.RIGHT)

        if self.categories:
            self.cat_combo.current(0)
            self._on_category_changed()
        self._on_type_changed()

    def _on_category_changed(self, event=None):
        cat_name = self.cat_combo.get()
        cat_id = None
        for c in self.categories:
            if c["name"] == cat_name:
                cat_id = c["id"]
                break
        if cat_id:
            subcats = [s["name"] for s in self.subcategories if s["category_id"] == cat_id]
            self.subcat_combo["values"] = subcats
            if subcats:
                self.subcat_combo.current(0)
            else:
                self.subcat_combo.set("")
        else:
            self.subcat_combo["values"] = []
            self.subcat_combo.set("")

    def _clear_dynamic_frame(self):
        for widget in self.dynamic_frame.winfo_children():
            widget.destroy()

    def _on_text_modified(self):
        # Auto-sugerir título si el campo de título está vacío
        if not self.title_entry.get().strip():
            raw_text = self.text_widget.get("1.0", tk.END).strip()
            if raw_text:
                suggested = self._extract_title_from_text(raw_text)
                if suggested:
                    self.title_entry.delete(0, tk.END)
                    self.title_entry.insert(0, suggested)
        self._recalculate_height()

    def _extract_title_from_text(self, text: str) -> str:
        if not text:
            return ""
        # Buscar patrones como <strong>Ejercicio 1...</strong> o similar
        m = re.search(r'<strong>\s*(Ejercicio\s+\d+[^<]*|Problema\s+\d+[^<]*)\s*</strong>', text, re.IGNORECASE)
        if m:
            clean = re.sub(r'<[^>]+>', '', m.group(1)).strip()
            return clean[:60]
        # Si no, tomar la primera oración limpia
        clean = re.sub(r'<[^>]+>', ' ', text)
        clean = " ".join(clean.split())
        if clean:
            first = clean.split(".")[0].strip()
            return first[:55] if first else clean[:55]
        return ""

    def _on_type_changed(self, event=None):
        self._clear_dynamic_frame()
        q_type = self._get_internal_type()

        # Configurar proporción visual según el tipo de pregunta
        if q_type in ("development", "code_writing"):
            # Para desarrollo y escritura de código solo hay controles compactos (spinbox)
            # Todo el espacio expansible se asigna al cuadro de texto del enunciado
            self.dynamic_frame.pack_configure(fill=tk.X, expand=False)
            self.row4.pack_configure(fill=tk.BOTH, expand=True)
            self.text_widget.config(height=14)
        elif q_type in ("single_choice", "multiple_choice", "true_false"):
            self.dynamic_frame.pack_configure(fill=tk.BOTH, expand=True)
            self.row4.pack_configure(fill=tk.BOTH, expand=True)
            self.text_widget.config(height=8)
        else:
            self.dynamic_frame.pack_configure(fill=tk.BOTH, expand=True)
            self.row4.pack_configure(fill=tk.BOTH, expand=True)
            self.text_widget.config(height=7)

        if q_type in ("single_choice", "multiple_choice"):
            self._build_choice_ui()
        elif q_type == "true_false":
            self._build_true_false_ui()
        elif q_type == "development":
            self._build_development_ui()
        elif q_type == "code_writing":
            self._build_code_writing_ui()
        elif q_type == "code_analysis":
            self._build_code_ui()
        elif q_type == "single_image":
            self._build_single_image_ui()
        elif q_type == "double_image":
            self._build_double_image_ui()
        elif q_type == "association":
            self._build_association_ui()

        self._recalculate_height()

    def _get_internal_type(self) -> str:
        name = self.type_combo.get().lower()
        if "única" in name or "unica" in name:
            return "single_choice"
        elif "múltiple" in name or "multiple" in name:
            return "multiple_choice"
        elif "falso" in name:
            return "true_false"
        elif "desarrollo" in name or "renglon" in name or "development" in name:
            return "development"
        elif "recuadro" in name or "escritura" in name:
            return "code_writing"
        elif "errores" in name or "código" in name or "codigo" in name:
            return "code_analysis"
        elif "1 imagen" in name:
            return "single_image"
        elif "2 im" in name:
            return "double_image"
        elif "asociación" in name or "asociacion" in name:
            return "association"
        return "single_choice"

    # --- Selección ---
    def _build_choice_ui(self):
        ttk.Label(self.dynamic_frame, text="Opciones de Selección (una por renglón, ej: a) Opción 1):").pack(anchor=tk.W, pady=(0, 4))
        self.options_text = tk.Text(self.dynamic_frame, height=5, font=("Segoe UI", 9), wrap=tk.WORD)
        self.options_text.pack(fill=tk.BOTH, expand=True)
        default_opts = "a) Opción A\nb) Opción B\nc) Opción C\nd) Opción D"
        self.options_text.insert("1.0", default_opts)
        self.options_text.bind("<KeyRelease>", lambda e: self._recalculate_height())

    # --- Falso y Verdadero ---
    def _build_true_false_ui(self):
        ttk.Label(self.dynamic_frame, text="Sub-enunciados (opcional, uno por renglón si la pregunta evalúa varias afirmaciones):").pack(anchor=tk.W, pady=(0, 4))
        self.tf_text = tk.Text(self.dynamic_frame, height=4, font=("Segoe UI", 9), wrap=tk.WORD)
        self.tf_text.pack(fill=tk.BOTH, expand=True)
        self.tf_text.bind("<KeyRelease>", lambda e: self._recalculate_height())
        ttk.Label(self.dynamic_frame, text="💡 Si deja este campo vacío, la pregunta se evalúa directamente con el enunciado principal y opciones Verdadero / Falso.", font=("Segoe UI", 8, "italic")).pack(anchor=tk.W, pady=(4, 0))

    # --- Desarrollo con Renglones ---
    def _build_development_ui(self):
        row = ttk.Frame(self.dynamic_frame)
        row.pack(anchor=tk.W, pady=5)
        ttk.Label(row, text="Cantidad de Renglones para Responder:").pack(side=tk.LEFT, padx=(0, 10))
        self.lines_spin = ttk.Spinbox(row, from_=0, to=40, increment=1, width=8)
        self.lines_spin.set("10")
        self.lines_spin.pack(side=tk.LEFT)
        self.lines_spin.bind("<KeyRelease>", lambda e: self._recalculate_height())
        self.lines_spin.bind("<<Increment>>", lambda e: self.after(50, self._recalculate_height))
        self.lines_spin.bind("<<Decrement>>", lambda e: self.after(50, self._recalculate_height))

        ttk.Label(
            self.dynamic_frame,
            text="💡 Ingrese 0 si la pregunta ya incluye una tabla o recuadro propio para responder en papel, o un número (ej. 6, 8, 10) para generar renglones reglamentarios impresos.",
            font=("Segoe UI", 8, "italic")
        ).pack(anchor=tk.W, pady=(4, 0))

    # --- Escritura de Código (Recuadro en Blanco) ---
    def _build_code_writing_ui(self):
        row = ttk.Frame(self.dynamic_frame)
        row.pack(anchor=tk.W, pady=5)
        ttk.Label(row, text="Espacio para escribir código (en equivalencia de renglones):").pack(side=tk.LEFT, padx=(0, 10))
        self.code_write_lines_spin = ttk.Spinbox(row, from_=0, to=40, increment=1, width=8)
        self.code_write_lines_spin.set("12")
        self.code_write_lines_spin.pack(side=tk.LEFT)
        self.code_write_lines_spin.bind("<KeyRelease>", lambda e: self._recalculate_height())

        ttk.Label(self.dynamic_frame, text="✨ Se genera un recuadro limpio con borde simple SIN líneas horizontales, ideal para que el estudiante escriba código con indentación clara.", font=("Segoe UI", 8, "italic")).pack(anchor=tk.W, pady=(8, 0))

    # --- Código / Errores ---
    def _build_code_ui(self):
        ttk.Label(self.dynamic_frame, text="Bloque de Código Fuente:").pack(anchor=tk.W, pady=(0, 2))
        self.code_text = tk.Text(self.dynamic_frame, height=5, font=("Consolas", 9), wrap=tk.NONE)
        self.code_text.pack(fill=tk.X, pady=(0, 4))
        self.code_text.bind("<KeyRelease>", lambda e: self._recalculate_height())

        ttk.Label(self.dynamic_frame, text="Pregunta / Sub-indicación sobre el código:").pack(anchor=tk.W, pady=(0, 2))
        self.sub_prompt_entry = ttk.Entry(self.dynamic_frame)
        self.sub_prompt_entry.pack(fill=tk.X, pady=(0, 4))
        self.sub_prompt_entry.insert(0, "¿Qué está mal en el código anterior? Explique la causa exacta del error.")

        row = ttk.Frame(self.dynamic_frame)
        row.pack(anchor=tk.W)
        ttk.Label(row, text="Renglones de respuesta:").pack(side=tk.LEFT, padx=(0, 10))
        self.code_lines_spin = ttk.Spinbox(row, from_=0, to=20, increment=1, width=8)
        self.code_lines_spin.set("5")
        self.code_lines_spin.pack(side=tk.LEFT)
        self.code_lines_spin.bind("<KeyRelease>", lambda e: self._recalculate_height())

    # --- Pregunta con 1 Imagen ---
    def _build_single_image_ui(self):
        # Texto antes
        ttk.Label(self.dynamic_frame, text="Texto antes de la imagen (opcional):").pack(anchor=tk.W, pady=(0, 2))
        self.img1_before_entry = ttk.Entry(self.dynamic_frame)
        self.img1_before_entry.pack(fill=tk.X, pady=(0, 6))

        # Selector de imagen
        row_img = ttk.Frame(self.dynamic_frame)
        row_img.pack(fill=tk.X, pady=(0, 6))
        ttk.Label(row_img, text="Archivo de Imagen:").pack(side=tk.LEFT, padx=(0, 5))
        self.img1_path_entry = ttk.Entry(row_img)
        self.img1_path_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 5))
        ttk.Button(row_img, text="📁 Examinar...", command=lambda: self._browse_image(1)).pack(side=tk.LEFT)

        # Ancho porcentual y alineación
        row_cfg = ttk.Frame(self.dynamic_frame)
        row_cfg.pack(fill=tk.X, pady=(0, 6))
        ttk.Label(row_cfg, text="Ancho de la imagen (% del ancho de página):").pack(side=tk.LEFT, padx=(0, 5))
        self.img1_width_spin = ttk.Spinbox(row_cfg, from_=10, to=100, increment=5, width=6)
        self.img1_width_spin.set("70")
        self.img1_width_spin.pack(side=tk.LEFT, padx=(0, 15))

        ttk.Label(row_cfg, text="Renglones de respuesta:").pack(side=tk.LEFT, padx=(0, 5))
        self.img1_lines_spin = ttk.Spinbox(row_cfg, from_=0, to=25, increment=1, width=6)
        self.img1_lines_spin.set("5")
        self.img1_lines_spin.pack(side=tk.LEFT)

        # Texto después
        ttk.Label(self.dynamic_frame, text="Texto después de la imagen (ej: pregunta o indicación):").pack(anchor=tk.W, pady=(0, 2))
        self.img1_after_entry = ttk.Entry(self.dynamic_frame)
        self.img1_after_entry.pack(fill=tk.X)

    # --- Pregunta con 2 Imágenes ---
    def _build_double_image_ui(self):
        # Texto antes
        ttk.Label(self.dynamic_frame, text="Texto antes de las imágenes:").pack(anchor=tk.W, pady=(0, 2))
        self.img2_before_entry = ttk.Entry(self.dynamic_frame)
        self.img2_before_entry.pack(fill=tk.X, pady=(0, 6))

        # Imagen 1
        r_img1 = ttk.Frame(self.dynamic_frame)
        r_img1.pack(fill=tk.X, pady=(0, 4))
        ttk.Label(r_img1, text="Imagen 1:").pack(side=tk.LEFT, padx=(0, 4))
        self.img2_path1_entry = ttk.Entry(r_img1)
        self.img2_path1_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 4))
        ttk.Button(r_img1, text="📁 Examinar...", command=lambda: self._browse_image(1, double=True)).pack(side=tk.LEFT, padx=(0, 8))
        ttk.Label(r_img1, text="Ancho %:").pack(side=tk.LEFT)
        self.img2_w1_spin = ttk.Spinbox(r_img1, from_=10, to=100, increment=5, width=5)
        self.img2_w1_spin.set("48")
        self.img2_w1_spin.pack(side=tk.LEFT)

        ttk.Label(self.dynamic_frame, text="Texto después de Imagen 1 / Intermedio:").pack(anchor=tk.W, pady=(0, 2))
        self.img2_after1_entry = ttk.Entry(self.dynamic_frame)
        self.img2_after1_entry.pack(fill=tk.X, pady=(0, 6))

        # Imagen 2
        r_img2 = ttk.Frame(self.dynamic_frame)
        r_img2.pack(fill=tk.X, pady=(0, 4))
        ttk.Label(r_img2, text="Imagen 2:").pack(side=tk.LEFT, padx=(0, 4))
        self.img2_path2_entry = ttk.Entry(r_img2)
        self.img2_path2_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 4))
        ttk.Button(r_img2, text="📁 Examinar...", command=lambda: self._browse_image(2, double=True)).pack(side=tk.LEFT, padx=(0, 8))
        ttk.Label(r_img2, text="Ancho %:").pack(side=tk.LEFT)
        self.img2_w2_spin = ttk.Spinbox(r_img2, from_=10, to=100, increment=5, width=5)
        self.img2_w2_spin.set("48")
        self.img2_w2_spin.pack(side=tk.LEFT)

        ttk.Label(self.dynamic_frame, text="Texto después de Imagen 2:").pack(anchor=tk.W, pady=(0, 2))
        self.img2_after2_entry = ttk.Entry(self.dynamic_frame)
        self.img2_after2_entry.pack(fill=tk.X, pady=(0, 6))

        # Layout y renglones
        r_cfg = ttk.Frame(self.dynamic_frame)
        r_cfg.pack(fill=tk.X)
        ttk.Label(r_cfg, text="Disposición:").pack(side=tk.LEFT, padx=(0, 4))
        self.img2_layout_combo = ttk.Combobox(r_cfg, state="readonly", width=22)
        self.img2_layout_combo["values"] = ["Lado a lado (Horizontal)", "Una debajo de otra (Vertical)"]
        self.img2_layout_combo.current(0)
        self.img2_layout_combo.pack(side=tk.LEFT, padx=(0, 15))

        ttk.Label(r_cfg, text="Renglones de respuesta:").pack(side=tk.LEFT, padx=(0, 4))
        self.img2_lines_spin = ttk.Spinbox(r_cfg, from_=0, to=25, increment=1, width=6)
        self.img2_lines_spin.set("5")
        self.img2_lines_spin.pack(side=tk.LEFT)

    def _browse_image(self, target_idx: int, double: bool = False):
        path = filedialog.askopenfilename(
            title="Seleccionar Imagen",
            filetypes=[("Imágenes", "*.png;*.jpg;*.jpeg;*.gif;*.svg;*.webp"), ("Todos los archivos", "*.*")],
            parent=self
        )
        if not path:
            return

        b64 = importer_exporter.file_to_base64(path)
        if not b64:
            messagebox.showerror("Error", "No se pudo leer la imagen seleccionada.", parent=self)
            return

        if not double:
            self.img1_path_entry.delete(0, tk.END)
            self.img1_path_entry.insert(0, path)
            self.img1_b64 = b64
        else:
            if target_idx == 1:
                self.img2_path1_entry.delete(0, tk.END)
                self.img2_path1_entry.insert(0, path)
                self.img1_b64 = b64
            else:
                self.img2_path2_entry.delete(0, tk.END)
                self.img2_path2_entry.insert(0, path)
                self.img2_b64 = b64

        self._recalculate_height()

    # --- Asociación ---
    def _build_association_ui(self):
        ttk.Label(self.dynamic_frame, text="Pares de Asociación (Formato: Letra | Definición Columna A | Concepto Columna B):").pack(anchor=tk.W, pady=(0, 2))
        self.assoc_text = tk.Text(self.dynamic_frame, height=5, font=("Segoe UI", 9), wrap=tk.NONE)
        self.assoc_text.pack(fill=tk.BOTH, expand=True, pady=(0, 4))
        sample_assoc = "A | Definición concepto 1 | Concepto 1\nB | Definición concepto 2 | Concepto 2\nC | Definición concepto 3 | Concepto 3"
        self.assoc_text.insert("1.0", sample_assoc)
        self.assoc_text.bind("<KeyRelease>", lambda e: self._recalculate_height())

        ttk.Label(self.dynamic_frame, text="Distractores en Columna B (separados por coma, opcional):").pack(anchor=tk.W, pady=(0, 2))
        self.distractors_entry = ttk.Entry(self.dynamic_frame)
        self.distractors_entry.pack(fill=tk.X)

    def _recalculate_height(self):
        q_type = self._get_internal_type()
        text = self.text_widget.get("1.0", tk.END).strip()
        extra_data = self._gather_extra_data()
        h = height_calculator.estimate_item_height(q_type, text, extra_data)
        self.height_spin.set(str(h))

    def _gather_extra_data(self) -> Dict[str, Any]:
        q_type = self._get_internal_type()
        data = {}
        if q_type in ("single_choice", "multiple_choice"):
            if hasattr(self, "options_text"):
                opts = [line.strip() for line in self.options_text.get("1.0", tk.END).splitlines() if line.strip()]
                data["options"] = opts
        elif q_type == "true_false":
            if hasattr(self, "tf_text"):
                stmts = [line.strip() for line in self.tf_text.get("1.0", tk.END).splitlines() if line.strip()]
                data["statements"] = stmts
        elif q_type == "development":
            if hasattr(self, "lines_spin"):
                try:
                    c = int(self.lines_spin.get())
                except Exception:
                    c = 10
                data["lines_count"] = c
                data["lines_class"] = f"lines-{c}" if c in (5, 6, 8, 10) else ""
        elif q_type == "code_writing":
            if hasattr(self, "code_write_lines_spin"):
                try:
                    c = int(self.code_write_lines_spin.get())
                except Exception:
                    c = 12
                data["lines_count"] = c
        elif q_type == "code_analysis":
            code = self.code_text.get("1.0", tk.END).rstrip() if hasattr(self, "code_text") else ""
            sub_prompt = self.sub_prompt_entry.get().strip() if hasattr(self, "sub_prompt_entry") else ""
            try:
                c = int(self.code_lines_spin.get())
            except Exception:
                c = 5
            data["code"] = code
            data["sub_prompt"] = sub_prompt
            data["lines_count"] = c
            data["lines_class"] = f"lines-{c}" if c in (5, 6, 8, 10) else ""
        elif q_type == "single_image":
            data["text_before"] = self.img1_before_entry.get().strip() if hasattr(self, "img1_before_entry") else ""
            data["image_path"] = self.img1_path_entry.get().strip() if hasattr(self, "img1_path_entry") else ""
            data["image_base64"] = self.img1_b64
            try:
                data["image_width_percent"] = float(self.img1_width_spin.get())
            except Exception:
                data["image_width_percent"] = 70
            try:
                data["lines_count"] = int(self.img1_lines_spin.get())
            except Exception:
                data["lines_count"] = 0
            data["text_after"] = self.img1_after_entry.get().strip() if hasattr(self, "img1_after_entry") else ""
        elif q_type == "double_image":
            data["text_before"] = self.img2_before_entry.get().strip() if hasattr(self, "img2_before_entry") else ""
            data["image1_path"] = self.img2_path1_entry.get().strip() if hasattr(self, "img2_path1_entry") else ""
            data["image1_base64"] = self.img1_b64
            try:
                data["image1_width_percent"] = float(self.img2_w1_spin.get())
            except Exception:
                data["image1_width_percent"] = 48
            data["text_after_img1"] = self.img2_after1_entry.get().strip() if hasattr(self, "img2_after1_entry") else ""
            data["image2_path"] = self.img2_path2_entry.get().strip() if hasattr(self, "img2_path2_entry") else ""
            data["image2_base64"] = self.img2_b64
            try:
                data["image2_width_percent"] = float(self.img2_w2_spin.get())
            except Exception:
                data["image2_width_percent"] = 48
            data["text_after_img2"] = self.img2_after2_entry.get().strip() if hasattr(self, "img2_after2_entry") else ""
            layout_val = "side_by_side" if "Horizontal" in self.img2_layout_combo.get() else "vertical"
            data["layout"] = layout_val
            try:
                data["lines_count"] = int(self.img2_lines_spin.get())
            except Exception:
                data["lines_count"] = 0
        elif q_type == "association":
            pairs = []
            if hasattr(self, "assoc_text"):
                for line in self.assoc_text.get("1.0", tk.END).splitlines():
                    if "|" in line:
                        parts = [p.strip() for p in line.split("|")]
                        if len(parts) >= 3:
                            pairs.append({"letter": parts[0], "definition": parts[1], "concept": parts[2]})
            distractors = []
            if hasattr(self, "distractors_entry"):
                d_str = self.distractors_entry.get().strip()
                if d_str:
                    distractors = [d.strip() for d in d_str.split(",") if d.strip()]
            data["pairs"] = pairs
            data["extra_distractors"] = distractors
        return data

    def _load_question(self, q_id: int):
        q = database.get_question_by_id(q_id)
        if not q:
            return

        self.cat_combo.set(q["category_name"])
        self._on_category_changed()
        if q["subcategory_name"]:
            self.subcat_combo.set(q["subcategory_name"])

        t = q["question_type"]
        type_names = {
            "single_choice": "Selección Única",
            "multiple_choice": "Selección Múltiple",
            "true_false": "Falso y Verdadero",
            "development": "Desarrollo (con Renglones)",
            "code_writing": "Escritura de Código (Recuadro en Blanco)",
            "code_analysis": "Identificación de Errores / Código",
            "single_image": "Pregunta con 1 Imagen",
            "double_image": "Pregunta con 2 Imágenes",
            "association": "Asociación de Conceptos"
        }
        self.type_combo.set(type_names.get(t, "Selección Única"))
        self._on_type_changed()

        self.title_entry.delete(0, tk.END)
        self.title_entry.insert(0, q["title"])

        self.text_widget.delete("1.0", tk.END)
        self.text_widget.insert("1.0", q["question_text"])

        self.points_spin.set(str(q["points"]))
        self.height_spin.set(str(q["estimated_height"]))

        extra = {}
        if q["extra_data"]:
            try:
                extra = json.loads(q["extra_data"])
            except Exception:
                extra = {}

        if t in ("single_choice", "multiple_choice") and hasattr(self, "options_text"):
            self.options_text.delete("1.0", tk.END)
            self.options_text.insert("1.0", "\n".join(extra.get("options", [])))
        elif t == "true_false" and hasattr(self, "tf_text"):
            self.tf_text.delete("1.0", tk.END)
            self.tf_text.insert("1.0", "\n".join(extra.get("statements", [])))
        elif t == "development" and hasattr(self, "lines_spin"):
            self.lines_spin.set(str(extra.get("lines_count", 10)))
        elif t == "code_writing" and hasattr(self, "code_write_lines_spin"):
            self.code_write_lines_spin.set(str(extra.get("lines_count", 12)))
        elif t == "code_analysis":
            if hasattr(self, "code_text"):
                self.code_text.delete("1.0", tk.END)
                self.code_text.insert("1.0", extra.get("code", ""))
            if hasattr(self, "sub_prompt_entry"):
                self.sub_prompt_entry.delete(0, tk.END)
                self.sub_prompt_entry.insert(0, extra.get("sub_prompt", ""))
            if hasattr(self, "code_lines_spin"):
                self.code_lines_spin.set(str(extra.get("lines_count", 5)))
        elif t == "single_image":
            if hasattr(self, "img1_before_entry"):
                self.img1_before_entry.delete(0, tk.END)
                self.img1_before_entry.insert(0, extra.get("text_before", ""))
            if hasattr(self, "img1_path_entry"):
                self.img1_path_entry.delete(0, tk.END)
                self.img1_path_entry.insert(0, extra.get("image_path", ""))
            self.img1_b64 = extra.get("image_base64")
            if hasattr(self, "img1_width_spin"):
                self.img1_width_spin.set(str(extra.get("image_width_percent", 70)))
            if hasattr(self, "img1_lines_spin"):
                self.img1_lines_spin.set(str(extra.get("lines_count", 0)))
            if hasattr(self, "img1_after_entry"):
                self.img1_after_entry.delete(0, tk.END)
                self.img1_after_entry.insert(0, extra.get("text_after", ""))
        elif t == "double_image":
            if hasattr(self, "img2_before_entry"):
                self.img2_before_entry.delete(0, tk.END)
                self.img2_before_entry.insert(0, extra.get("text_before", ""))
            if hasattr(self, "img2_path1_entry"):
                self.img2_path1_entry.delete(0, tk.END)
                self.img2_path1_entry.insert(0, extra.get("image1_path", ""))
            self.img1_b64 = extra.get("image1_base64")
            if hasattr(self, "img2_w1_spin"):
                self.img2_w1_spin.set(str(extra.get("image1_width_percent", 48)))
            if hasattr(self, "img2_after1_entry"):
                self.img2_after1_entry.delete(0, tk.END)
                self.img2_after1_entry.insert(0, extra.get("text_after_img1", ""))
            if hasattr(self, "img2_path2_entry"):
                self.img2_path2_entry.delete(0, tk.END)
                self.img2_path2_entry.insert(0, extra.get("image2_path", ""))
            self.img2_b64 = extra.get("image2_base64")
            if hasattr(self, "img2_w2_spin"):
                self.img2_w2_spin.set(str(extra.get("image2_width_percent", 48)))
            if hasattr(self, "img2_after2_entry"):
                self.img2_after2_entry.delete(0, tk.END)
                self.img2_after2_entry.insert(0, extra.get("text_after_img2", ""))
            if hasattr(self, "img2_layout_combo"):
                val = "Una debajo de otra (Vertical)" if extra.get("layout") == "vertical" else "Lado a lado (Horizontal)"
                self.img2_layout_combo.set(val)
            if hasattr(self, "img2_lines_spin"):
                self.img2_lines_spin.set(str(extra.get("lines_count", 0)))
        elif t == "association":
            if hasattr(self, "assoc_text"):
                self.assoc_text.delete("1.0", tk.END)
                lines = []
                for p in extra.get("pairs", []):
                    lines.append(f"{p.get('letter', '')} | {p.get('definition', '')} | {p.get('concept', '')}")
                self.assoc_text.insert("1.0", "\n".join(lines))
            if hasattr(self, "distractors_entry"):
                self.distractors_entry.delete(0, tk.END)
                self.distractors_entry.insert(0, ", ".join(extra.get("extra_distractors", [])))

    def _save_question(self):
        cat_name = self.cat_combo.get().strip()
        cat_id = None
        for c in self.categories:
            if c["name"] == cat_name:
                cat_id = c["id"]
                break

        if not cat_id and self.categories:
            # Si no se seleccionó pero hay categorías, usar la primera por defecto
            cat_id = self.categories[0]["id"]
            self.cat_combo.set(self.categories[0]["name"])
            self._on_category_changed()
        elif not cat_id:
            messagebox.showerror("Error", "Debe seleccionar una categoría válida.", parent=self)
            return

        subcat_name = self.subcat_combo.get().strip()
        subcat_id = None
        for s in self.subcategories:
            if s["category_id"] == cat_id and s["name"] == subcat_name:
                subcat_id = s["id"]
                break

        text = self.text_widget.get("1.0", tk.END).strip()
        if not text:
            messagebox.showerror("Error", "Debe ingresar el enunciado de la pregunta.", parent=self)
            return

        title = self.title_entry.get().strip()
        if not title:
            # Auto-generar título amigable a partir del texto para no bloquear
            title = self._extract_title_from_text(text) or "Pregunta de Desarrollo"
            self.title_entry.delete(0, tk.END)
            self.title_entry.insert(0, title)

        try:
            points = float(self.points_spin.get())
        except Exception:
            points = 5.0

        try:
            height = int(self.height_spin.get())
        except Exception:
            height = 80

        q_type = self._get_internal_type()
        extra_data = json.dumps(self._gather_extra_data(), ensure_ascii=False)

        database.save_question(
            category_id=cat_id,
            subcategory_id=subcat_id,
            question_type=q_type,
            title=title,
            question_text=text,
            points=points,
            estimated_height=height,
            extra_data=extra_data,
            question_id=self.question_id
        )

        self.result = True
        self.destroy()


class SelectQuestionsDialog(tk.Toplevel):
    """
    Diálogo para seleccionar una o varias preguntas del banco y agregarlas al examen.
    """
    def __init__(self, parent, target_page: int = 1):
        super().__init__(parent)
        self.target_page = target_page
        self.selected_questions: List[Dict[str, Any]] = []

        self.title("Seleccionar Preguntas del Banco")
        center_window(self, 900, 560)
        self.transient(parent)
        self.grab_set()

        self._build_ui()
        self._load_questions()

    def _build_ui(self):
        main = ttk.Frame(self, padding="12")
        main.pack(fill=tk.BOTH, expand=True)

        filter_frame = ttk.Frame(main)
        filter_frame.pack(fill=tk.X, pady=(0, 10))

        ttk.Label(filter_frame, text="Categoría:").pack(side=tk.LEFT, padx=(0, 4))
        self.cat_filter = ttk.Combobox(filter_frame, state="readonly", width=22)
        cats = ["Todas"] + [c["name"] for c in database.get_categories()]
        self.cat_filter["values"] = cats
        self.cat_filter.current(0)
        self.cat_filter.pack(side=tk.LEFT, padx=(0, 10))
        self.cat_filter.bind("<<ComboboxSelected>>", lambda e: self._load_questions())

        ttk.Label(filter_frame, text="Buscar:").pack(side=tk.LEFT, padx=(0, 4))
        self.search_entry = ttk.Entry(filter_frame, width=25)
        self.search_entry.pack(side=tk.LEFT, padx=(0, 10))
        self.search_entry.bind("<KeyRelease>", lambda e: self._load_questions())

        ttk.Label(filter_frame, text="Agregar en Página:").pack(side=tk.LEFT, padx=(10, 4))
        self.page_spin = ttk.Spinbox(filter_frame, from_=1, to=20, width=5)
        self.page_spin.set(str(self.target_page))
        self.page_spin.pack(side=tk.LEFT)

        columns = ("id", "title", "category", "type", "points", "height")
        self.tree = ttk.Treeview(main, columns=columns, show="headings", selectmode="extended")
        self.tree.heading("id", text="ID")
        self.tree.heading("title", text="Título / Pregunta")
        self.tree.heading("category", text="Categoría (Sección)")
        self.tree.heading("type", text="Tipo")
        self.tree.heading("points", text="Puntos")
        self.tree.heading("height", text="Alto (px)")

        self.tree.column("id", width=40, anchor=tk.CENTER)
        self.tree.column("title", width=340)
        self.tree.column("category", width=180)
        self.tree.column("type", width=130)
        self.tree.column("points", width=60, anchor=tk.CENTER)
        self.tree.column("height", width=70, anchor=tk.CENTER)

        scrollbar = ttk.Scrollbar(main, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)

        self.tree.pack(side=tk.TOP, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        btn_bar = ttk.Frame(main)
        btn_bar.pack(fill=tk.X, pady=(10, 0))

        ttk.Label(btn_bar, text="💡 Puede seleccionar múltiples preguntas usando Ctrl o Shift.", font=("Segoe UI", 8, "italic")).pack(side=tk.LEFT)
        ttk.Button(btn_bar, text="Cancelar", command=self.destroy).pack(side=tk.RIGHT, padx=(5, 0))
        ttk.Button(btn_bar, text="➕ Agregar al Examen", command=self._confirm_selection).pack(side=tk.RIGHT)

    def _load_questions(self):
        for item in self.tree.get_children():
            self.tree.delete(item)

        selected_cat = self.cat_filter.get()
        cat_id = None
        if selected_cat != "Todas":
            for c in database.get_categories():
                if c["name"] == selected_cat:
                    cat_id = c["id"]
                    break

        query = self.search_entry.get().strip()
        questions = database.get_questions(category_id=cat_id, search_query=query)

        type_names = {
            "single_choice": "Selección Única",
            "multiple_choice": "Selección Múltiple",
            "true_false": "Falso y Verdadero",
            "development": "Desarrollo",
            "code_writing": "Escritura de Código",
            "code_analysis": "Código / Errores",
            "single_image": "1 Imagen",
            "double_image": "2 Imágenes",
            "association": "Asociación"
        }

        for q in questions:
            self.tree.insert("", tk.END, values=(
                q["id"],
                q["title"],
                q["category_name"],
                type_names.get(q["question_type"], q["question_type"]),
                q["points"],
                q["estimated_height"]
            ))

    def _confirm_selection(self):
        selected_items = self.tree.selection()
        if not selected_items:
            messagebox.showwarning("Atención", "Seleccione al menos una pregunta para agregar.", parent=self)
            return

        try:
            pg = int(self.page_spin.get())
        except Exception:
            pg = 1

        self.selected_questions = []
        for item_id in selected_items:
            q_id = int(self.tree.item(item_id, "values")[0])
            q = database.get_question_by_id(q_id)
            if q:
                q["target_page"] = pg
                self.selected_questions.append(q)

        self.destroy()


class AssignPageDialog(tk.Toplevel):
    """
    Diálogo para cambiar la página asignada a uno o varios ítems del examen.
    """
    def __init__(self, parent, current_page: int = 1):
        super().__init__(parent)
        self.selected_page = None

        self.title("Asignar Página")
        self.resizable(False, False)
        center_window(self, 320, 180)
        self.transient(parent)
        self.grab_set()

        frame = ttk.Frame(self, padding="20")
        frame.pack(fill=tk.BOTH, expand=True)

        ttk.Label(frame, text="Mover el(los) ítem(s) seleccionado(s) a:", font=("Segoe UI", 9, "bold")).pack(pady=(0, 10))

        row = ttk.Frame(frame)
        row.pack(pady=(0, 15))
        ttk.Label(row, text="Página:").pack(side=tk.LEFT, padx=(0, 8))
        self.page_spin = ttk.Spinbox(row, from_=1, to=30, width=8)
        self.page_spin.set(str(current_page))
        self.page_spin.pack(side=tk.LEFT)

        btn_bar = ttk.Frame(frame)
        btn_bar.pack(fill=tk.X)
        ttk.Button(btn_bar, text="Cancelar", command=self.destroy).pack(side=tk.RIGHT, padx=(5, 0))
        ttk.Button(btn_bar, text="Aceptar", command=self._confirm).pack(side=tk.RIGHT)

    def _confirm(self):
        try:
            self.selected_page = int(self.page_spin.get())
        except Exception:
            self.selected_page = 1
        self.destroy()
