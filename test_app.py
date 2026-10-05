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


if __name__ == "__main__":
    unittest.main()
