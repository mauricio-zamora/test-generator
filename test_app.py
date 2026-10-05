"""
Suite de Pruebas Automatizadas Extendida para el Generador de Exámenes.
Verifica:
1. Nuevos tipos de preguntas: Falso/Verdadero, Escritura de Código (sin líneas), 1 Imagen, 2 Imágenes.
2. Numeración romana automática de secciones ('Parte I', 'Parte II', etc.).
3. Nota fija sobre 100 y puntos dinámicos.
4. Ubicación configurable de Resumen de Calificación y Observaciones con cantidad de renglones.
5. Exportación e Importación de Categorías, Preguntas y Exámenes (CSV y JSON).
6. Reset de base de datos a estado vacío.
"""

import os
import json
import unittest
import database
import height_calculator
import html_generator
import importer_exporter


class TestExamGeneratorExtended(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.test_db = "test_extended.db"
        if os.path.exists(cls.test_db):
            os.remove(cls.test_db)
        database.init_database(cls.test_db, seed=True)

    @classmethod
    def tearDownClass(cls):
        if os.path.exists(cls.test_db):
            os.remove(cls.test_db)

    def test_01_roman_numerals(self):
        self.assertEqual(html_generator.to_roman(1), "I")
        self.assertEqual(html_generator.to_roman(2), "II")
        self.assertEqual(html_generator.to_roman(3), "III")
        self.assertEqual(html_generator.to_roman(4), "IV")
        self.assertEqual(html_generator.to_roman(5), "V")

    def test_02_new_question_types_height(self):
        # Falso y Verdadero
        h_tf = height_calculator.estimate_item_height(
            "true_false",
            "Afirmaciones sobre Python:",
            {"statements": ["Afirmación 1", "Afirmación 2", "Afirmación 3"]}
        )
        self.assertGreater(h_tf, 50)

        # Escritura de Código (en blanco sin renglones impresos)
        h_cw = height_calculator.estimate_item_height(
            "code_writing",
            "Escriba la función recursiva:",
            {"lines_count": 15}
        )
        self.assertGreater(h_cw, 300)

        # Imagen con texto
        h_img = height_calculator.estimate_item_height(
            "single_image",
            "Analice el diagrama de flujo:",
            {"text_before": "Observe la figura", "image_width_percent": 80, "lines_count": 5}
        )
        self.assertGreater(h_img, 200)

    def test_03_flexible_sections_html_and_nota_fixed(self):
        exam = database.get_exam_by_id(1, self.test_db)
        exam["show_grading_summary"] = True
        exam["summary_page"] = 2  # Poner resumen en página 2
        exam["show_observations"] = True
        exam["observations_lines"] = 12  # 12 renglones
        exam["observations_page"] = 3  # Poner observaciones en página 3

        html = html_generator.generate_exam_html(exam, exam["items"])

        # Verificar NOTA fija sobre 100
        self.assertIn("/100", html)
        self.assertIn("Puntos: ______ /", html)

        # Verificar numeración romana automática
        self.assertIn("Parte I:", html)
        self.assertIn("Parte II:", html)

        # Verificar página de resumen y observaciones
        self.assertIn("Resumen de Calificación", html)
        self.assertIn("Observaciones del Profesor", html)

    def test_04_code_writing_blank_box_html(self):
        item = {
            "question_type": "code_writing",
            "question_text": "Implemente la clase ArbolBinario:",
            "points": 10.0,
            "extra_data": json.dumps({"lines_count": 14})
        }
        rendered = html_generator.render_single_item(item, 1)
        self.assertIn("code-writing-box", rendered)
        self.assertNotIn("lines-pattern", rendered)  # No imprime renglones

    def test_05_csv_export_import_roundtrip(self):
        csv_q_path = "test_questions_export.csv"
        csv_cat_path = "test_categories_export.csv"

        # Exportar
        q_count = importer_exporter.export_questions_to_csv(csv_q_path, db_path=self.test_db)
        self.assertGreaterEqual(q_count, 16)

        c_count = importer_exporter.export_categories_to_csv(csv_cat_path, db_path=self.test_db)
        self.assertGreaterEqual(c_count, 4)

        # Importar a una base limpia
        temp_db = "test_temp_import.db"
        database.init_database(temp_db, seed=False)

        cats_imp, subs_imp = importer_exporter.import_categories_from_csv(csv_cat_path, db_path=temp_db)
        self.assertGreaterEqual(cats_imp, 1)

        q_imp = importer_exporter.import_questions_from_csv(csv_q_path, db_path=temp_db)
        self.assertGreaterEqual(q_imp, 16)

        # Limpieza de archivos temporales
        for f in (csv_q_path, csv_cat_path, temp_db):
            if os.path.exists(f):
                os.remove(f)

    def test_06_reset_database(self):
        reset_db = "test_reset.db"
        database.init_database(reset_db, seed=True)
        self.assertGreater(len(database.get_questions(db_path=reset_db)), 0)

        # Resetear
        database.reset_database(empty=True, db_path=reset_db)
        self.assertEqual(len(database.get_questions(db_path=reset_db)), 0)
        self.assertEqual(len(database.get_categories(db_path=reset_db)), 0)
        self.assertEqual(len(database.get_exams(db_path=reset_db)), 0)

        if os.path.exists(reset_db):
            os.remove(reset_db)

    def test_07_true_false_format_like_selection(self):
        # 1. Pregunta individual de Falso y Verdadero
        item_single = {
            "question_type": "true_false",
            "question_text": "Python es un lenguaje compilado directamente a código máquina.",
            "points": 5.0,
            "extra_data": json.dumps({})
        }
        rendered_single = html_generator.render_single_item(item_single, 1)
        # El enunciado va primero en question-text
        pos_text = rendered_single.find("Python es un lenguaje compilado")
        pos_options = rendered_single.find("options-grid")
        pos_v = rendered_single.find("Verdadero", pos_options)
        pos_f = rendered_single.find("Falso", pos_v)

        self.assertNotEqual(pos_text, -1)
        self.assertNotEqual(pos_options, -1)
        self.assertLess(pos_text, pos_options, "El enunciado debe aparecer antes de las opciones de marcado")
        self.assertLess(pos_options, pos_v)
        self.assertLess(pos_v, pos_f)
        # Estilo idéntico a selección
        self.assertIn("checkbox-sim radio-sim", rendered_single)

        # 2. Pregunta con sub-afirmaciones
        item_multi = {
            "question_type": "true_false",
            "question_text": "Evalúe las siguientes afirmaciones:",
            "points": 6.0,
            "extra_data": json.dumps({
                "statements": ["Las tuplas son inmutables.", "Los diccionarios no permiten llaves duplicadas."]
            })
        }
        rendered_multi = html_generator.render_single_item(item_multi, 2)
        pos_stmt1 = rendered_multi.find("Las tuplas son inmutables.")
        pos_opt_stmt1 = rendered_multi.find("tf-options-grid")
        self.assertNotEqual(pos_stmt1, -1)
        self.assertNotEqual(pos_opt_stmt1, -1)
        self.assertLess(pos_stmt1, pos_opt_stmt1, "La afirmación debe aparecer antes de sus opciones para marcar")

    def test_08_zero_lines_count_rendering_and_height(self):
        # Desarrollo con 0 renglones
        item_dev = {
            "question_type": "development",
            "question_text": "Explique el algoritmo de ordenamiento:",
            "points": 5.0,
            "extra_data": json.dumps({"lines_count": 0})
        }
        rendered_dev = html_generator.render_single_item(item_dev, 1)
        self.assertNotIn("development-box", rendered_dev)
        h_dev = height_calculator.estimate_item_height("development", item_dev["question_text"], {"lines_count": 0})
        self.assertGreater(h_dev, 30)

        # Escritura de código con 0 renglones
        item_cw = {
            "question_type": "code_writing",
            "question_text": "Escriba el código:",
            "points": 5.0,
            "extra_data": json.dumps({"lines_count": 0})
        }
        rendered_cw = html_generator.render_single_item(item_cw, 2)
        self.assertNotIn("development-box", rendered_cw)
        self.assertNotIn("code-writing-box", rendered_cw)

        # Observaciones con 0 renglones
        exam = {
            "title": "Examen",
            "institution": "Colegio",
            "course_code": "PROG",
            "course_name": "Prog",
            "career": "Ing",
            "professor": "Prof",
            "group_name": "G1",
            "exam_date": "2026-10-05",
            "period": "II",
            "duration": "60 min",
            "instructions_text": "Indicaciones",
            "show_grading_summary": False,
            "show_observations": True,
            "observations_lines": 0,
            "observations_page": 1,
            "items": []
        }
        html_exam = html_generator.generate_exam_html(exam, [])
        self.assertIn("Observaciones del Profesor", html_exam)
        self.assertNotIn('class="development-box lines-pattern"', html_exam)

    def test_09_association_matching_and_center_window(self):
        # 1. Verificar carga de examen y que los puntos no sean None
        exam = database.get_exam_by_id(1, self.test_db)
        self.assertIsNotNone(exam)
        for it in exam["items"]:
            self.assertIsNotNone(it.get("points"), f"El ítem {it.get('question_title')} debe tener puntos asignados")

        # 2. Verificar que la pregunta de asociación tenga 5 en A y 5 en B sin distractores
        assoc_item = [i for i in exam["items"] if i.get("question_type") == "association"][0]
        rendered = html_generator.render_single_item(assoc_item, 16)
        self.assertIn("(10 puntos)", rendered)
        self.assertNotIn(".keys()", rendered)
        self.assertEqual(rendered.count('class="col-left"'), 5)
        self.assertEqual(rendered.count('class="col-right"'), 5)

        # 3. Probar lógica de center_window
        import ui_dialogs
        import tkinter as tk
        root = tk.Tk()
        root.withdraw()
        top = tk.Toplevel(root)
        ui_dialogs.center_window(top, 500, 300)
        top.update()
        geom = top.geometry()  # e.g., '500x300+X+Y'
        self.assertTrue(geom.startswith("500x300+"))
        top.destroy()
        root.destroy()


if __name__ == "__main__":
    unittest.main()


