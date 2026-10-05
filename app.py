"""
Ventana Principal de la Aplicación Generadora de Exámenes.
Integra todas las pestañas, barra de menús, importación/exportación masiva,
opción de resetear la aplicación (dejar en blanco) y carga de datos de ejemplo.
"""

import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import os
import sys

import database
import importer_exporter
from ui_exam_tab import ExamTab
from ui_questions_tab import QuestionsTab
from ui_categories_tab import CategoriesTab
from ui_instructions_tab import InstructionsTab


class ExamGeneratorApp(tk.Tk):
    def __init__(self):
        super().__init__()

        # Configuración de Ventana Principal
        self.title("Generador de Exámenes Impresos en Papel (Tamaño Carta)")
        self.geometry("1300x840")
        self.minsize(1080, 700)

        # Configurar estilo visual moderno
        self._configure_styles()

        # Inicializar base de datos
        database.init_database()

        # Barra de menús superior
        self._build_menu()

        # Barra de estado inferior
        self.status_bar = ttk.Frame(self, relief=tk.SUNKEN, padding=(8, 3))
        self.status_bar.pack(side=tk.BOTTOM, fill=tk.X)
        self.lbl_status = ttk.Label(
            self.status_bar,
            text="Listo. Formato optimizado para impresión en tamaño Carta (8.5 x 11 in).",
            font=("Segoe UI", 9)
        )
        self.lbl_status.pack(side=tk.LEFT)

        # Contenedor de Pestañas (Notebook)
        self.notebook = ttk.Notebook(self)
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=8)

        # 1. Pestaña: Generador de Examen
        self.exam_tab = ExamTab(self.notebook)

        # 2. Pestaña: Banco de Preguntas
        self.questions_tab = QuestionsTab(
            self.notebook,
            on_add_to_exam=self._on_add_question_to_exam,
            on_data_changed=self._on_questions_changed
        )

        # 3. Pestaña: Categorías y Secciones
        self.categories_tab = CategoriesTab(
            self.notebook,
            on_data_changed=self._on_categories_changed
        )

        # 4. Pestaña: Indicaciones Generales
        self.instructions_tab = InstructionsTab(
            self.notebook,
            on_data_changed=self._on_instructions_changed
        )

        # Añadir al Notebook
        self.notebook.add(self.exam_tab, text=" 📝 Generador de Examen ")
        self.notebook.add(self.questions_tab, text=" 📚 Banco de Preguntas ")
        self.notebook.add(self.categories_tab, text=" 🗂️ Categorías y Secciones ")
        self.notebook.add(self.instructions_tab, text=" 📋 Indicaciones Generales ")

    def _configure_styles(self):
        style = ttk.Style(self)
        available_themes = style.theme_names()
        if "vista" in available_themes:
            style.theme_use("vista")
        elif "clam" in available_themes:
            style.theme_use("clam")

        style.configure(".", font=("Segoe UI", 9))
        style.configure("TNotebook.Tab", font=("Segoe UI", 9, "bold"), padding=(12, 6))
        style.configure("TLabelframe.Label", font=("Segoe UI", 9, "bold"), foreground="#1a365d")
        style.configure("Treeview.Heading", font=("Segoe UI", 9, "bold"))

    def _build_menu(self):
        menubar = tk.Menu(self)
        self.config(menu=menubar)

        # Menú Archivo
        menu_archivo = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Archivo", menu=menu_archivo)
        menu_archivo.add_command(label="➕ Nuevo Examen", command=lambda: self.exam_tab._new_blank_exam())
        menu_archivo.add_command(label="📂 Cargar Examen...", command=lambda: self.exam_tab._show_load_exam_dialog())
        menu_archivo.add_command(label="💾 Guardar Examen", command=lambda: self.exam_tab._save_exam_to_db())
        menu_archivo.add_separator()
        menu_archivo.add_command(label="👁️ Vista Previa en Navegador", command=lambda: self.exam_tab._preview_in_browser())
        menu_archivo.add_command(label="📄 Exportar a HTML...", command=lambda: self.exam_tab._export_html())
        menu_archivo.add_separator()
        menu_archivo.add_command(label="Salir", command=self.quit)

        # Menú Importar / Exportar
        menu_impexp = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Importar / Exportar", menu=menu_impexp)
        menu_impexp.add_command(label="📥 Importar Preguntas (CSV)...", command=lambda: self.questions_tab._import_questions_csv())
        menu_impexp.add_command(label="📤 Exportar Preguntas (CSV)...", command=lambda: self.questions_tab._export_questions_csv())
        menu_impexp.add_separator()
        menu_impexp.add_command(label="📥 Importar Categorías (CSV)...", command=lambda: self.categories_tab._import_csv())
        menu_impexp.add_command(label="📤 Exportar Categorías (CSV)...", command=lambda: self.categories_tab._export_csv())
        menu_impexp.add_separator()
        menu_impexp.add_command(label="📥 Importar Examen Completo (JSON)...", command=lambda: self.exam_tab._import_exam_json())
        menu_impexp.add_command(label="📤 Exportar Examen Completo (JSON)...", command=lambda: self.exam_tab._export_exam_json())

        # Menú Base de Datos / Mantenimiento
        menu_db = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Base de Datos", menu=menu_db)
        menu_db.add_command(label="📥 Cargar Datos de Ejemplo (de archivos de muestra)", command=self._load_sample_data_dialog)
        menu_db.add_command(label="📁 Abrir Carpeta de Ejemplos de Importación...", command=self._open_examples_folder)
        menu_db.add_separator()
        menu_db.add_command(label="⚠️ Resetear Aplicación (Dejar en Blanco)", command=self._reset_application)

    def _open_examples_folder(self):
        folder = os.path.join(os.path.dirname(os.path.abspath(__file__)), "ejemplos_importacion")
        if not os.path.exists(folder):
            os.makedirs(folder, exist_ok=True)
        os.startfile(folder)

    def _reset_application(self):
        confirm = messagebox.askyesno(
            "⚠️ Confirmar Reset de Aplicación",
            "¿Está seguro de que desea resetear la aplicación por completo?\n\n"
            "Esta acción vaciará todas las preguntas, categorías, subcategorías, indicaciones y exámenes guardados, "
            "dejando la aplicación 100% en blanco para que pueda empezar desde cero.\n\n"
            "(Siempre puede recargar los datos de prueba desde 'Base de Datos -> Cargar Datos de Ejemplo')",
            icon="warning"
        )
        if not confirm:
            return

        database.reset_database(empty=True)
        self.exam_tab._new_blank_exam()
        self.questions_tab.refresh_data()
        self.categories_tab.refresh_data()
        self.instructions_tab.refresh_data()
        self.lbl_status.config(text="Aplicación reseteada. Base de datos vacía.")
        messagebox.showinfo("Reset Completo", "La aplicación ha sido reseteada. Todas las tablas están en blanco.")

    def _load_sample_data_dialog(self):
        confirm = messagebox.askyesno(
            "Cargar Datos de Ejemplo",
            "¿Desea cargar los datos de ejemplo del Quiz de Cátedra?\n\n"
            "Se añadirán las categorías, subcategorías, las 16 preguntas reales y las plantillas de indicaciones."
        )
        if not confirm:
            return

        conn = database.get_connection()
        database.seed_sample_data(conn)
        conn.close()

        self.questions_tab.refresh_data()
        self.categories_tab.refresh_data()
        self.instructions_tab.refresh_data()
        self.exam_tab.load_default_or_first_exam()
        self.lbl_status.config(text="Datos de ejemplo cargados con éxito.")
        messagebox.showinfo("Éxito", "Datos de ejemplo cargados correctamente.")

    def _on_add_question_to_exam(self, question_dict):
        self.exam_tab.add_question_to_exam(question_dict)
        self.lbl_status.config(text=f"Pregunta '{question_dict['title']}' añadida al examen actual.")

    def _on_questions_changed(self):
        self.lbl_status.config(text="Banco de preguntas actualizado.")

    def _on_categories_changed(self):
        self.questions_tab.refresh_data()
        self.lbl_status.config(text="Categorías actualizadas.")

    def _on_instructions_changed(self):
        self.exam_tab._refresh_instructions_combo()
        self.lbl_status.config(text="Plantillas de indicaciones actualizadas.")


def main():
    app = ExamGeneratorApp()
    app.mainloop()


if __name__ == "__main__":
    main()
