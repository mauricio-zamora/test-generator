"""
Módulo de Base de Datos SQLite para el Generador de Exámenes.
Gestiona Categorías, Subcategorías, Banco de Preguntas,
Indicaciones Generales y Exámenes Guardados.
"""

import sqlite3
import json
import os
from typing import List, Dict, Any, Optional

DB_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "exam_generator.db")


def get_connection(db_path: str = DB_FILE) -> sqlite3.Connection:
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn


def init_database(db_path: str = DB_FILE, seed: bool = True):
    """Crea las tablas necesarias si no existen y asegura las columnas actualizadas."""
    conn = get_connection(db_path)
    cursor = conn.cursor()

    # Tabla de Categorías (temáticas, la numeración de sección 'Parte I, II, ...' es automática)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS categories (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE,
            section_title TEXT NOT NULL,
            description TEXT,
            default_order INTEGER DEFAULT 1
        );
    """)

    # Tabla de Subcategorías
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS subcategories (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            category_id INTEGER NOT NULL,
            name TEXT NOT NULL,
            description TEXT,
            FOREIGN KEY (category_id) REFERENCES categories (id) ON DELETE CASCADE,
            UNIQUE(category_id, name)
        );
    """)

    # Tabla de Preguntas / Ítems
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS questions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            category_id INTEGER NOT NULL,
            subcategory_id INTEGER,
            question_type TEXT NOT NULL, 
            -- Tipos: single_choice, multiple_choice, true_false, development,
            -- code_writing, code_analysis, single_image, double_image, association
            title TEXT NOT NULL,
            question_text TEXT NOT NULL,
            points REAL NOT NULL DEFAULT 5.0,
            estimated_height INTEGER DEFAULT 100,
            extra_data TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (category_id) REFERENCES categories (id) ON DELETE RESTRICT,
            FOREIGN KEY (subcategory_id) REFERENCES subcategories (id) ON DELETE SET NULL
        );
    """)

    # Tabla de Indicaciones Generales reutilizables
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS instructions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL UNIQUE,
            content TEXT NOT NULL,
            is_default INTEGER DEFAULT 0
        );
    """)

    # Tabla de Exámenes
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS exams (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            institution TEXT NOT NULL,
            course_code TEXT NOT NULL,
            course_name TEXT NOT NULL,
            career TEXT NOT NULL,
            professor TEXT NOT NULL,
            group_name TEXT NOT NULL,
            exam_date TEXT NOT NULL,
            period TEXT NOT NULL,
            duration TEXT NOT NULL,
            instructions_text TEXT,
            font_family TEXT DEFAULT 'Arial, sans-serif',
            font_size TEXT DEFAULT '12px',
            line_height TEXT DEFAULT '1.4',
            show_grading_summary INTEGER DEFAULT 1,
            summary_page INTEGER DEFAULT 0,
            show_observations INTEGER DEFAULT 1,
            observations_lines INTEGER DEFAULT 8,
            observations_page INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    """)

    # Tabla de Ítems del Examen (preguntas agregadas y ordenadas por página)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS exam_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            exam_id INTEGER NOT NULL,
            question_id INTEGER NOT NULL,
            section_id INTEGER NOT NULL,
            item_order INTEGER NOT NULL,
            page_number INTEGER NOT NULL DEFAULT 1,
            custom_points REAL,
            custom_height INTEGER,
            custom_text TEXT,
            FOREIGN KEY (exam_id) REFERENCES exams (id) ON DELETE CASCADE,
            FOREIGN KEY (question_id) REFERENCES questions (id) ON DELETE CASCADE,
            FOREIGN KEY (section_id) REFERENCES categories (id) ON DELETE RESTRICT
        );
    """)

    # Migración: Verificar si existen las nuevas columnas en exams
    cursor.execute("PRAGMA table_info(exams)")
    cols = [r["name"] for r in cursor.fetchall()]
    if "summary_page" not in cols:
        cursor.execute("ALTER TABLE exams ADD COLUMN summary_page INTEGER DEFAULT 0")
    if "observations_lines" not in cols:
        cursor.execute("ALTER TABLE exams ADD COLUMN observations_lines INTEGER DEFAULT 8")
    if "observations_page" not in cols:
        cursor.execute("ALTER TABLE exams ADD COLUMN observations_page INTEGER DEFAULT 0")

    conn.commit()

    # Si se solicita y la base está vacía, sembrar datos de muestra iniciales
    if seed:
        cursor.execute("SELECT COUNT(*) FROM categories")
        if cursor.fetchone()[0] == 0:
            seed_sample_data(conn)

    conn.close()


def reset_database(empty: bool = True, db_path: str = DB_FILE):
    """
    Vacía o reinicia por completo la base de datos eliminando todas las tablas.
    Si empty=True, queda 100% limpia sin registros.
    """
    conn = get_connection(db_path)
    cur = conn.cursor()
    cur.execute("PRAGMA foreign_keys = OFF;")
    cur.execute("DROP TABLE IF EXISTS exam_items;")
    cur.execute("DROP TABLE IF EXISTS exams;")
    cur.execute("DROP TABLE IF EXISTS questions;")
    cur.execute("DROP TABLE IF EXISTS subcategories;")
    cur.execute("DROP TABLE IF EXISTS categories;")
    cur.execute("DROP TABLE IF EXISTS instructions;")
    cur.execute("PRAGMA foreign_keys = ON;")
    conn.commit()
    conn.close()
    init_database(db_path, seed=not empty)


def seed_sample_data(conn: sqlite3.Connection):
    """Siembra los datos exactos del archivo Quiz_en_Papel_01.html como plantilla inicial."""
    cursor = conn.cursor()

    # 1. Indicaciones generales iniciales
    instructions_seed = [
        (
            "Instrucciones Estándar (Pruebas Escritas UCR)",
            "Lea con atención cada enunciado antes de responder. Utilice bolígrafo de tinta azul o negra para las respuestas definitivas. Los círculos representan opciones de selección única y las casillas cuadradas indican que la pregunta admite selección múltiple (puede marcar más de una opción). No se permite el uso de dispositivos electrónicos con acceso a internet durante la prueba. <b>No se permiten reclamos en lápiz.</b>",
            1
        ),
        (
            "Instrucciones Examen Parcial / Final",
            "Dispone de 120 minutos para resolver la prueba. Escriba con letra clara y legible. Se permite el uso de calculadora científica no programable. Apague y guarde cualquier dispositivo móvil antes de iniciar.",
            0
        ),
        (
            "Instrucciones Cortas / Quiz Rápido",
            "Trabajo estrictamente individual. Responda directamente en el espacio asignado. No desengrape las hojas del examen.",
            0
        )
    ]
    cursor.executemany(
        "INSERT INTO instructions (title, content, is_default) VALUES (?, ?, ?)",
        instructions_seed
    )

    # 2. Categorías (Secciones temáticas - sin prefijo 'Parte I', el sistema lo numera automáticamente)
    categories_seed = [
        ("Selección Única y Múltiple", "Selección Única y Múltiple", "Preguntas de opción simple y múltiple", 1),
        ("Desarrollo", "Desarrollo", "Preguntas abiertas con renglones de respuesta", 2),
        ("Identificación de Errores", "Identificación de Errores en Código", "Análisis de código fuente y detección de errores", 3),
        ("Asociación de Conceptos", "Asociación de Conceptos", "Apareamiento entre dos columnas de conceptos y definiciones", 4),
    ]
    cursor.executemany(
        "INSERT INTO categories (name, section_title, description, default_order) VALUES (?, ?, ?, ?)",
        categories_seed
    )

    cat_map = {}
    for row in cursor.execute("SELECT name, id FROM categories"):
        cat_map[row[0]] = row[1]

    # 3. Subcategorías
    subcategories_seed = [
        (cat_map["Selección Única y Múltiple"], "Cadenas (str)"),
        (cat_map["Selección Única y Múltiple"], "Estructuras de Datos (list, dict, set)"),
        (cat_map["Selección Única y Múltiple"], "Tipado (typing)"),
        (cat_map["Desarrollo"], "Colecciones"),
        (cat_map["Desarrollo"], "Inmutabilidad y Cadenas"),
        (cat_map["Identificación de Errores"], "Sintaxis"),
        (cat_map["Identificación de Errores"], "Lógica de Diccionarios"),
        (cat_map["Asociación de Conceptos"], "Métodos y Estructuras"),
    ]
    cursor.executemany(
        "INSERT INTO subcategories (category_id, name) VALUES (?, ?)",
        subcategories_seed
    )

    subcat_map = {}
    for row in cursor.execute("SELECT name, id FROM subcategories"):
        subcat_map[row[0]] = row[1]

    # 4. Preguntas del documento de muestra Quiz_en_Papel_01.html
    questions_seed = [
        (
            cat_map["Selección Única y Múltiple"],
            subcat_map["Cadenas (str)"],
            "single_choice",
            "Método .lower() en cadenas",
            "¿Cuál es el resultado de ejecutar <code>\"Hola Mundo\".lower()</code> en Python?",
            5.0,
            75,
            json.dumps({
                "options": [
                    "a) \"HOLA MUNDO\"",
                    "b) \"hola mundo\"",
                    "c) \"Hola Mundo\"",
                    "d) Genera un error"
                ],
                "correct_option": 1
            })
        ),
        (
            cat_map["Selección Única y Múltiple"],
            subcat_map["Cadenas (str)"],
            "single_choice",
            "Eliminar espacios con .strip()",
            "Dada la variable <code>texto: str = \"  python  \"</code>, ¿qué método elimina los espacios en blanco al inicio y al final de la cadena?",
            5.0,
            75,
            json.dumps({
                "options": [
                    "a) texto.trim()",
                    "b) texto.clean()",
                    "c) texto.strip()",
                    "d) texto.cut()"
                ],
                "correct_option": 2
            })
        ),
        (
            cat_map["Selección Única y Múltiple"],
            subcat_map["Estructuras de Datos (list, dict, set)"],
            "single_choice",
            "Diferencia entre list y set",
            "¿Cuál es la principal diferencia entre una <code>list</code> y un <code>set</code> en Python?",
            5.0,
            85,
            json.dumps({
                "options": [
                    "a) El set permite duplicados y la lista no.",
                    "b) El set no mantiene orden ni permite duplicados.",
                    "c) La lista no permite acceder por índice.",
                    "d) No existen diferencias entre ambos."
                ],
                "correct_option": 1
            })
        ),
        (
            cat_map["Selección Única y Múltiple"],
            subcat_map["Estructuras de Datos (list, dict, set)"],
            "single_choice",
            "Indexación negativa en listas",
            "Si <code>numeros: list[int] = [4, 8, 15, 16]</code>, ¿qué expresión obtiene correctamente el último elemento de la lista?",
            5.0,
            75,
            json.dumps({
                "options": [
                    "a) numeros[-1]",
                    "b) numeros[last]",
                    "c) numeros[len(numeros)]",
                    "d) numeros.end()"
                ],
                "correct_option": 0
            })
        ),
        (
            cat_map["Selección Única y Múltiple"],
            subcat_map["Estructuras de Datos (list, dict, set)"],
            "single_choice",
            "Llaves de diccionario con .keys()",
            "Dado <code>datos: dict[str, int] = {\"a\": 1, \"b\": 2}</code>, ¿qué método devuelve únicamente las llaves del diccionario?",
            5.0,
            75,
            json.dumps({
                "options": [
                    "a) datos.values()",
                    "b) datos.items()",
                    "c) datos.keys()",
                    "d) datos.get()"
                ],
                "correct_option": 2
            })
        ),
        (
            cat_map["Selección Única y Múltiple"],
            subcat_map["Cadenas (str)"],
            "multiple_choice",
            "Verificación de cadenas sin modificarlas",
            "De los siguientes métodos de cadenas (<code>str</code>), seleccione los <u>dos</u> que sirven para verificar el contenido de una cadena sin modificarla:",
            5.0,
            80,
            json.dumps({
                "options": [
                    "a) startswith()",
                    "b) replace()",
                    "c) isdigit()",
                    "d) split()"
                ],
                "correct_options": [0, 2]
            })
        ),
        (
            cat_map["Selección Única y Múltiple"],
            subcat_map["Estructuras de Datos (list, dict, set)"],
            "multiple_choice",
            "Métodos de modificación in-place en listas",
            "De los siguientes métodos aplicables a una lista (<code>list</code>), seleccione los <u>dos</u> que modifican la lista original en el mismo lugar (in-place):",
            5.0,
            80,
            json.dumps({
                "options": [
                    "a) append()",
                    "b) sort()",
                    "c) copy()",
                    "d) count()"
                ],
                "correct_options": [0, 1]
            })
        ),
        (
            cat_map["Selección Única y Múltiple"],
            subcat_map["Estructuras de Datos (list, dict, set)"],
            "multiple_choice",
            "Afirmaciones sobre sets y diccionarios",
            "Sobre los conjuntos (<code>set</code>) y diccionarios (<code>dict</code>) en Python, seleccione las <u>dos</u> afirmaciones correctas:",
            5.0,
            80,
            json.dumps({
                "options": [
                    "a) Un set puede contener elementos duplicados.",
                    "b) Las llaves de un dict deben ser únicas.",
                    "c) El método union() combina dos sets sin duplicar elementos.",
                    "d) Un dict se accede únicamente por índice numérico."
                ],
                "correct_options": [1, 2]
            })
        ),
        (
            cat_map["Selección Única y Múltiple"],
            subcat_map["Cadenas (str)"],
            "multiple_choice",
            "Slicing y split en cadenas",
            "Si <code>frase: str = \"Curso de Python\"</code>, seleccione las <u>dos</u> expresiones que devuelven correctamente la palabra <code>\"Python\"</code>:",
            5.0,
            80,
            json.dumps({
                "options": [
                    "a) frase.split()[-1]",
                    "b) frase[9:]",
                    "c) frase[0:6]",
                    "d) frase.upper()[9:]"
                ],
                "correct_options": [0, 1]
            })
        ),
        (
            cat_map["Selección Única y Múltiple"],
            subcat_map["Tipado (typing)"],
            "multiple_choice",
            "Anotaciones de tipo (typing)",
            "Sobre la anotación de tipos (<code>typing</code>) en Python, seleccione las <u>dos</u> afirmaciones correctas:",
            5.0,
            85,
            json.dumps({
                "options": [
                    "a) <code>nombre: str = \"Ana\"</code> es una anotación de tipo válida.",
                    "b) <code>edades: list[int]</code> indica una lista de enteros.",
                    "c) Las anotaciones de tipo son obligatorias para ejecutar el código.",
                    "d) Python lanza un error si el valor no coincide con el tipo anotado."
                ],
                "correct_options": [0, 1]
            })
        ),
        (
            cat_map["Desarrollo"],
            subcat_map["Colecciones"],
            "development",
            "Comparativa list[int] vs set[int]",
            "Explique con sus propias palabras la diferencia entre una <code>list[int]</code> y un <code>set[int]</code> en Python, mencionando al menos dos características distintivas de cada estructura.",
            8.0,
            260,
            json.dumps({
                "lines_count": 10,
                "lines_class": "lines-10"
            })
        ),
        (
            cat_map["Desarrollo"],
            subcat_map["Colecciones"],
            "development",
            "Propósito y uso de dict[str, int]",
            "Describa el propósito de un <code>dict[str, int]</code> en Python y explique cómo se accede y se actualiza el valor asociado a una llave existente. Incluya un ejemplo breve.",
            8.0,
            260,
            json.dumps({
                "lines_count": 10,
                "lines_class": "lines-10"
            })
        ),
        (
            cat_map["Desarrollo"],
            subcat_map["Inmutabilidad y Cadenas"],
            "development",
            "Inmutabilidad de cadenas str",
            "Explique qué significa que las cadenas (<code>str</code>) en Python sean inmutables. ¿Qué sucede al \"modificar\" una cadena con un método como <code>.replace()</code>?",
            8.0,
            260,
            json.dumps({
                "lines_count": 10,
                "lines_class": "lines-10"
            })
        ),
        (
            cat_map["Identificación de Errores"],
            subcat_map["Sintaxis"],
            "code_analysis",
            "Falta de dos puntos en for",
            "El siguiente código pretende construir una lista con los nombres en mayúscula a partir de una lista de cadenas. Indique cuál es el error y por qué impide su correcta ejecución.",
            8.0,
            330,
            json.dumps({
                "code": "def convertir_mayusculas(nombres: list[str]) -> list[str]:\n    resultado: list[str] = []\n    for nombre in nombres\n        resultado.append(nombre.upper())\n    return resultado\n\nprint(convertir_mayusculas([\"ana\", \"luis\"]))",
                "sub_prompt": "¿Qué está mal en el código anterior? Explique la causa exacta del error.",
                "lines_count": 5,
                "lines_class": "lines-5"
            })
        ),
        (
            cat_map["Identificación de Errores"],
            subcat_map["Lógica de Diccionarios"],
            "code_analysis",
            "Error lógico en conteo con diccionario",
            "El siguiente código pretende contar cuántas veces aparece cada palabra de una lista usando un diccionario. Indique cuál es el error lógico o de sintaxis presente.",
            8.0,
            330,
            json.dumps({
                "code": "def contar_palabras(palabras: list[str]) -> dict[str, int]:\n    conteo: dict[str, int] = {}\n    for palabra in palabras:\n        if palabra not in conteo:\n            conteo[palabra] = 0\n        conteo[palabra] = 1\n    return conteo\n\nprint(contar_palabras([\"sol\", \"luna\", \"sol\"]))",
                "sub_prompt": "¿Qué está mal en el código anterior? Explique la causa exacta del error.",
                "lines_count": 5,
                "lines_class": "lines-5"
            })
        ),
        (
            cat_map["Asociación de Conceptos"],
            subcat_map["Métodos y Estructuras"],
            "association",
            "Asociación de Conceptos Python",
            "Asocie las definiciones de la <strong>Columna A</strong> escribiendo la letra correspondiente en el espacio entre paréntesis de la <strong>Columna B</strong>. Cada ítem vale 2 puntos. Las opciones de la derecha pueden usarse una vez, varias veces o ninguna.",
            10.0,
            240,
            json.dumps({
                "pairs": [
                    {
                        "letter": "A",
                        "definition": "Método de <code>str</code> que une los elementos de una lista de cadenas usando un separador.",
                        "concept": "<code>.join()</code>"
                    },
                    {
                        "letter": "B",
                        "definition": "Estructura de datos que almacena pares llave-valor, donde las llaves son únicas.",
                        "concept": "<code>set</code>"
                    },
                    {
                        "letter": "C",
                        "definition": "Colección desordenada que no permite elementos duplicados.",
                        "concept": "<code>dict</code>"
                    },
                    {
                        "letter": "D",
                        "definition": "Método de <code>list</code> que agrega un elemento al final de la lista.",
                        "concept": "<code>.append()</code>"
                    },
                    {
                        "letter": "E",
                        "definition": "Anotación de tipo (<code>typing</code>) que indica una lista de enteros.",
                        "concept": "<code>list[int]</code>"
                    }
                ],
                "extra_distractors": ["<code>.keys()</code>"]
            })
        ),
    ]

    cursor.executemany("""
        INSERT INTO questions (category_id, subcategory_id, question_type, title, question_text, points, estimated_height, extra_data)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, questions_seed)

    # 5. Crear el Examen Muestra por Defecto
    cursor.execute("""
        INSERT INTO exams (
            title, institution, course_code, course_name, career, professor,
            group_name, exam_date, period, duration, instructions_text,
            font_family, font_size, line_height, show_grading_summary, summary_page,
            show_observations, observations_lines, observations_page
        ) VALUES (
            'Quiz en Papel #01',
            'Universidad de Costa Rica — Escuela de Ingeniería Industrial',
            'II-1119',
            'Fundamentos de Tecnología Digital',
            'Ingeniería Industrial',
            'Profesor del Curso',
            '01',
            '______/______/2026',
            'I Ciclo Lectivo 2026',
            '45 minutos',
            'Lea con atención cada enunciado antes de responder. Utilice bolígrafo de tinta azul o negra para las respuestas definitivas. Los círculos representan opciones de selección única y las casillas cuadradas indican que la pregunta admite selección múltiple (puede marcar más de una opción). No se permite el uso de dispositivos electrónicos con acceso a internet durante la prueba. <b>No se permiten reclamos en lápiz.</b>',
            'Arial, sans-serif',
            '12px',
            '1.4',
            1,
            4,
            1,
            10,
            4
        )
    """)
    exam_id = cursor.lastrowid

    page_assignments = [
        (1, 1, 1), (2, 1, 1), (3, 1, 1), (4, 1, 1), (5, 1, 1), (6, 1, 1), (7, 1, 1),
        (8, 1, 2), (9, 1, 2), (10, 1, 2), (11, 2, 2), (12, 2, 2),
        (13, 2, 3), (14, 3, 3), (15, 3, 3),
        (16, 4, 4)
    ]

    for order_idx, (q_id, sec_id, pg) in enumerate(page_assignments, start=1):
        cursor.execute("""
            INSERT INTO exam_items (exam_id, question_id, section_id, item_order, page_number)
            VALUES (?, ?, ?, ?, ?)
        """, (exam_id, q_id, sec_id, order_idx, pg))

    conn.commit()


# ============================================================================
# FUNCIONES CRUD
# ============================================================================

def get_categories(db_path: str = DB_FILE) -> List[Dict[str, Any]]:
    conn = get_connection(db_path)
    cur = conn.cursor()
    cur.execute("SELECT * FROM categories ORDER BY default_order, id")
    rows = [dict(r) for r in cur.fetchall()]
    conn.close()
    return rows


def add_category(name: str, section_title: str = "", description: str = "", order: int = 1, db_path: str = DB_FILE) -> int:
    conn = get_connection(db_path)
    cur = conn.cursor()
    sec_t = section_title if section_title else name
    cur.execute("INSERT INTO categories (name, section_title, description, default_order) VALUES (?, ?, ?, ?)",
                (name, sec_t, description, order))
    cat_id = cur.lastrowid
    conn.commit()
    conn.close()
    return cat_id


def update_category(cat_id: int, name: str, section_title: str, description: str, order: int, db_path: str = DB_FILE):
    conn = get_connection(db_path)
    cur = conn.cursor()
    sec_t = section_title if section_title else name
    cur.execute("UPDATE categories SET name = ?, section_title = ?, description = ?, default_order = ? WHERE id = ?",
                (name, sec_t, description, order, cat_id))
    conn.commit()
    conn.close()


def delete_category(cat_id: int, db_path: str = DB_FILE):
    conn = get_connection(db_path)
    cur = conn.cursor()
    cur.execute("DELETE FROM categories WHERE id = ?", (cat_id,))
    conn.commit()
    conn.close()


def get_subcategories(category_id: Optional[int] = None, db_path: str = DB_FILE) -> List[Dict[str, Any]]:
    conn = get_connection(db_path)
    cur = conn.cursor()
    if category_id:
        cur.execute("SELECT * FROM subcategories WHERE category_id = ? ORDER BY name", (category_id,))
    else:
        cur.execute("SELECT * FROM subcategories ORDER BY name")
    rows = [dict(r) for r in cur.fetchall()]
    conn.close()
    return rows


def add_subcategory(category_id: int, name: str, description: str = "", db_path: str = DB_FILE) -> int:
    conn = get_connection(db_path)
    cur = conn.cursor()
    cur.execute("INSERT INTO subcategories (category_id, name, description) VALUES (?, ?, ?)",
                (category_id, name, description))
    sub_id = cur.lastrowid
    conn.commit()
    conn.close()
    return sub_id


def delete_subcategory(sub_id: int, db_path: str = DB_FILE):
    conn = get_connection(db_path)
    cur = conn.cursor()
    cur.execute("DELETE FROM subcategories WHERE id = ?", (sub_id,))
    conn.commit()
    conn.close()


def get_questions(category_id: Optional[int] = None, subcategory_id: Optional[int] = None, search_query: str = "", db_path: str = DB_FILE) -> List[Dict[str, Any]]:
    conn = get_connection(db_path)
    cur = conn.cursor()
    sql = """
        SELECT q.*, c.name as category_name, c.section_title, s.name as subcategory_name
        FROM questions q
        JOIN categories c ON q.category_id = c.id
        LEFT JOIN subcategories s ON q.subcategory_id = s.id
        WHERE 1=1
    """
    params = []
    if category_id:
        sql += " AND q.category_id = ?"
        params.append(category_id)
    if subcategory_id:
        sql += " AND q.subcategory_id = ?"
        params.append(subcategory_id)
    if search_query:
        sql += " AND (q.title LIKE ? OR q.question_text LIKE ?)"
        term = f"%{search_query}%"
        params.extend([term, term])

    sql += " ORDER BY c.default_order, q.category_id, q.id"
    cur.execute(sql, params)
    rows = [dict(r) for r in cur.fetchall()]
    conn.close()
    return rows


def get_question_by_id(question_id: int, db_path: str = DB_FILE) -> Optional[Dict[str, Any]]:
    conn = get_connection(db_path)
    cur = conn.cursor()
    cur.execute("""
        SELECT q.*, c.name as category_name, c.section_title, s.name as subcategory_name
        FROM questions q
        JOIN categories c ON q.category_id = c.id
        LEFT JOIN subcategories s ON q.subcategory_id = s.id
        WHERE q.id = ?
    """, (question_id,))
    row = cur.fetchone()
    conn.close()
    return dict(row) if row else None


def save_question(
    category_id: int,
    subcategory_id: Optional[int],
    question_type: str,
    title: str,
    question_text: str,
    points: float,
    estimated_height: int,
    extra_data: str,
    question_id: Optional[int] = None,
    db_path: str = DB_FILE
) -> int:
    conn = get_connection(db_path)
    cur = conn.cursor()
    if question_id:
        cur.execute("""
            UPDATE questions SET
                category_id = ?, subcategory_id = ?, question_type = ?,
                title = ?, question_text = ?, points = ?,
                estimated_height = ?, extra_data = ?
            WHERE id = ?
        """, (category_id, subcategory_id, question_type, title, question_text, points, estimated_height, extra_data, question_id))
        q_id = question_id
    else:
        cur.execute("""
            INSERT INTO questions (category_id, subcategory_id, question_type, title, question_text, points, estimated_height, extra_data)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (category_id, subcategory_id, question_type, title, question_text, points, estimated_height, extra_data))
        q_id = cur.lastrowid
    conn.commit()
    conn.close()
    return q_id


def delete_question(question_id: int, db_path: str = DB_FILE):
    conn = get_connection(db_path)
    cur = conn.cursor()
    cur.execute("DELETE FROM questions WHERE id = ?", (question_id,))
    conn.commit()
    conn.close()


def get_instructions(db_path: str = DB_FILE) -> List[Dict[str, Any]]:
    conn = get_connection(db_path)
    cur = conn.cursor()
    cur.execute("SELECT * FROM instructions ORDER BY is_default DESC, title")
    rows = [dict(r) for r in cur.fetchall()]
    conn.close()
    return rows


def save_instruction(title: str, content: str, is_default: int = 0, instruction_id: Optional[int] = None, db_path: str = DB_FILE) -> int:
    conn = get_connection(db_path)
    cur = conn.cursor()
    if instruction_id:
        cur.execute("UPDATE instructions SET title = ?, content = ?, is_default = ? WHERE id = ?",
                    (title, content, is_default, instruction_id))
        ins_id = instruction_id
    else:
        cur.execute("INSERT INTO instructions (title, content, is_default) VALUES (?, ?, ?)",
                    (title, content, is_default))
        ins_id = cur.lastrowid
    conn.commit()
    conn.close()
    return ins_id


def delete_instruction(instruction_id: int, db_path: str = DB_FILE):
    conn = get_connection(db_path)
    cur = conn.cursor()
    cur.execute("DELETE FROM instructions WHERE id = ?", (instruction_id,))
    conn.commit()
    conn.close()


def get_exams(db_path: str = DB_FILE) -> List[Dict[str, Any]]:
    conn = get_connection(db_path)
    cur = conn.cursor()
    cur.execute("SELECT * FROM exams ORDER BY updated_at DESC")
    rows = [dict(r) for r in cur.fetchall()]
    conn.close()
    return rows


def get_exam_by_id(exam_id: int, db_path: str = DB_FILE) -> Optional[Dict[str, Any]]:
    conn = get_connection(db_path)
    cur = conn.cursor()
    cur.execute("SELECT * FROM exams WHERE id = ?", (exam_id,))
    row = cur.fetchone()
    if not row:
        conn.close()
        return None
    exam_dict = dict(row)

    cur.execute("""
        SELECT ei.*, q.title as question_title, q.question_text, q.question_type,
               q.points as original_points, q.estimated_height as original_height,
               q.extra_data, c.name as category_name, c.section_title
        FROM exam_items ei
        JOIN questions q ON ei.question_id = q.id
        JOIN categories c ON ei.section_id = c.id
        WHERE ei.exam_id = ?
        ORDER BY ei.page_number, ei.item_order
    """, (exam_id,))
    exam_dict["items"] = [dict(r) for r in cur.fetchall()]
    conn.close()
    return exam_dict


def save_exam_full(exam_data: Dict[str, Any], items_data: List[Dict[str, Any]], db_path: str = DB_FILE) -> int:
    """Guarda o actualiza un examen completo junto con sus opciones y sus ítems asignados."""
    conn = get_connection(db_path)
    cur = conn.cursor()

    exam_id = exam_data.get("id")
    if exam_id:
        cur.execute("""
            UPDATE exams SET
                title = ?, institution = ?, course_code = ?, course_name = ?,
                career = ?, professor = ?, group_name = ?, exam_date = ?,
                period = ?, duration = ?, instructions_text = ?,
                font_family = ?, font_size = ?, line_height = ?,
                show_grading_summary = ?, summary_page = ?,
                show_observations = ?, observations_lines = ?, observations_page = ?,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
        """, (
            exam_data.get("title", "Examen"),
            exam_data.get("institution", ""),
            exam_data.get("course_code", ""),
            exam_data.get("course_name", ""),
            exam_data.get("career", ""),
            exam_data.get("professor", ""),
            exam_data.get("group_name", ""),
            exam_data.get("exam_date", ""),
            exam_data.get("period", ""),
            exam_data.get("duration", ""),
            exam_data.get("instructions_text", ""),
            exam_data.get("font_family", "Arial, sans-serif"),
            exam_data.get("font_size", "12px"),
            exam_data.get("line_height", "1.4"),
            1 if exam_data.get("show_grading_summary", True) else 0,
            int(exam_data.get("summary_page", 0)),
            1 if exam_data.get("show_observations", True) else 0,
            int(exam_data.get("observations_lines", 8)),
            int(exam_data.get("observations_page", 0)),
            exam_id
        ))
        cur.execute("DELETE FROM exam_items WHERE exam_id = ?", (exam_id,))
    else:
        cur.execute("""
            INSERT INTO exams (
                title, institution, course_code, course_name, career, professor,
                group_name, exam_date, period, duration, instructions_text,
                font_family, font_size, line_height,
                show_grading_summary, summary_page,
                show_observations, observations_lines, observations_page
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            exam_data.get("title", "Examen"),
            exam_data.get("institution", ""),
            exam_data.get("course_code", ""),
            exam_data.get("course_name", ""),
            exam_data.get("career", ""),
            exam_data.get("professor", ""),
            exam_data.get("group_name", ""),
            exam_data.get("exam_date", ""),
            exam_data.get("period", ""),
            exam_data.get("duration", ""),
            exam_data.get("instructions_text", ""),
            exam_data.get("font_family", "Arial, sans-serif"),
            exam_data.get("font_size", "12px"),
            exam_data.get("line_height", "1.4"),
            1 if exam_data.get("show_grading_summary", True) else 0,
            int(exam_data.get("summary_page", 0)),
            1 if exam_data.get("show_observations", True) else 0,
            int(exam_data.get("observations_lines", 8)),
            int(exam_data.get("observations_page", 0)),
        ))
        exam_id = cur.lastrowid

    # Insertar ítems
    for idx, item in enumerate(items_data, start=1):
        cur.execute("""
            INSERT INTO exam_items (
                exam_id, question_id, section_id, item_order, page_number,
                custom_points, custom_height, custom_text
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            exam_id,
            item["question_id"],
            item.get("section_id", item.get("category_id")),
            item.get("item_order", idx),
            item.get("page_number", 1),
            item.get("custom_points"),
            item.get("custom_height"),
            item.get("custom_text")
        ))

    conn.commit()
    conn.close()
    return exam_id


def delete_exam(exam_id: int, db_path: str = DB_FILE):
    conn = get_connection(db_path)
    cur = conn.cursor()
    cur.execute("DELETE FROM exams WHERE id = ?", (exam_id,))
    conn.commit()
    conn.close()
