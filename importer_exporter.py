"""
Módulo de Importación y Exportación de Datos.
Permite exportar e importar Categorías, Subcategorías, Banco de Preguntas y Exámenes
en formatos CSV, TXT y JSON con codificación UTF-8 compatible con Excel.
"""

import csv
import json
import os
import io
import base64
from typing import List, Dict, Any, Tuple, Optional
import database


# ============================================================================
# EXPORTACIÓN E IMPORTACIÓN DE CATEGORÍAS Y SUBCATEGORÍAS
# ============================================================================

def export_categories_to_csv(file_path: str, db_path: str = database.DB_FILE) -> int:
    """
    Exporta todas las categorías y sus subcategorías a un archivo CSV.
    Formato: Categoria, Subcategoria, Descripcion
    """
    categories = database.get_categories(db_path)
    subcategories = database.get_subcategories(db_path=db_path)

    subcats_by_cat = {}
    for sub in subcategories:
        subcats_by_cat.setdefault(sub["category_id"], []).append(sub)

    count = 0
    with open(file_path, mode="w", newline="", encoding="utf-8-sig") as f:
        writer = csv.writer(f)
        writer.writerow(["Categoria", "Subcategoria", "Descripcion"])
        for cat in categories:
            cat_subs = subcats_by_cat.get(cat["id"], [])
            if not cat_subs:
                writer.writerow([cat["name"], "", cat.get("description", "")])
                count += 1
            else:
                for sub in cat_subs:
                    writer.writerow([cat["name"], sub["name"], sub.get("description", "")])
                    count += 1
    return count


def import_categories_from_csv(file_path: str, db_path: str = database.DB_FILE) -> Tuple[int, int]:
    """
    Importa categorías y subcategorías desde un archivo CSV o TXT delimitado por comas o punto y coma.
    Retorna (num_categorias_creadas, num_subcategorias_creadas).
    """
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"No se encontró el archivo {file_path}")

    # Detectar delimitador
    with open(file_path, "r", encoding="utf-8-sig", errors="replace") as f:
        first_line = f.readline()
        delimiter = ";" if ";" in first_line else ","

    cats_created = 0
    subs_created = 0

    existing_cats = {c["name"].strip().lower(): c["id"] for c in database.get_categories(db_path)}

    with open(file_path, "r", encoding="utf-8-sig", errors="replace") as f:
        reader = csv.reader(f, delimiter=delimiter)
        header = None
        for row in reader:
            if not row or not any(row):
                continue
            if header is None:
                header = [h.strip().lower() for h in row]
                continue

            cat_name = row[0].strip() if len(row) > 0 else ""
            if not cat_name or cat_name.lower() in ("categoria", "categoría"):
                continue

            sub_name = row[1].strip() if len(row) > 1 else ""
            desc = row[2].strip() if len(row) > 2 else ""

            # Verificar si categoría existe
            cat_key = cat_name.lower()
            if cat_key not in existing_cats:
                cat_id = database.add_category(
                    name=cat_name,
                    section_title=cat_name,
                    description=desc if not sub_name else "",
                    db_path=db_path
                )
                existing_cats[cat_key] = cat_id
                cats_created += 1
            else:
                cat_id = existing_cats[cat_key]

            # Verificar subcategoría
            if sub_name:
                # Si viene con múltiples subcategorías separadas por ';'
                sub_list = [s.strip() for s in sub_name.split(";") if s.strip()]
                for s in sub_list:
                    existing_subs = {
                        sub["name"].strip().lower()
                        for sub in database.get_subcategories(category_id=cat_id, db_path=db_path)
                    }
                    if s.lower() not in existing_subs:
                        database.add_subcategory(category_id=cat_id, name=s, description=desc, db_path=db_path)
                        subs_created += 1

    return cats_created, subs_created


# ============================================================================
# EXPORTACIÓN E IMPORTACIÓN DE PREGUNTAS
# ============================================================================

def export_questions_to_csv(file_path: str, db_path: str = database.DB_FILE) -> int:
    """
    Exporta todas las preguntas del banco a un archivo CSV estructurado.
    """
    questions = database.get_questions(db_path=db_path)
    count = 0
    with open(file_path, mode="w", newline="", encoding="utf-8-sig") as f:
        writer = csv.writer(f)
        writer.writerow([
            "Tipo",
            "Categoria",
            "Subcategoria",
            "Titulo",
            "Puntos",
            "Alto_px",
            "Enunciado",
            "Detalles_JSON"
        ])
        for q in questions:
            writer.writerow([
                q["question_type"],
                q["category_name"],
                q.get("subcategory_name") or "",
                q["title"],
                q["points"],
                q["estimated_height"],
                q["question_text"],
                q.get("extra_data") or "{}"
            ])
            count += 1
    return count


def import_questions_from_csv(file_path: str, db_path: str = database.DB_FILE) -> int:
    """
    Importa preguntas al banco desde un archivo CSV.
    Crea las categorías y subcategorías que no existan automáticamente.
    """
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"No se encontró el archivo {file_path}")

    # Detectar delimitador
    with open(file_path, "r", encoding="utf-8-sig", errors="replace") as f:
        first_line = f.readline()
        delimiter = ";" if ";" in first_line else ","

    imported_count = 0
    with open(file_path, "r", encoding="utf-8-sig", errors="replace") as f:
        reader = csv.reader(f, delimiter=delimiter)
        header = None
        for row in reader:
            if not row or not any(row):
                continue
            if header is None:
                header = [h.strip().lower() for h in row]
                continue

            if len(row) < 7:
                continue

            q_type = row[0].strip()
            cat_name = row[1].strip()
            subcat_name = row[2].strip() if len(row) > 2 else ""
            title = row[3].strip() if len(row) > 3 else ""
            try:
                points = float(row[4].strip())
            except Exception:
                points = 5.0
            try:
                height = int(row[5].strip())
            except Exception:
                height = 80
            text = row[6].strip() if len(row) > 6 else ""
            extra_data = row[7].strip() if len(row) > 7 else "{}"

            if not cat_name or not title or not text:
                continue

            # Obtener o crear Categoría
            cat_id = None
            for c in database.get_categories(db_path):
                if c["name"].strip().lower() == cat_name.lower():
                    cat_id = c["id"]
                    break
            if not cat_id:
                cat_id = database.add_category(cat_name, cat_name, "", db_path=db_path)

            # Obtener o crear Subcategoría si fue indicada
            subcat_id = None
            if subcat_name:
                for s in database.get_subcategories(category_id=cat_id, db_path=db_path):
                    if s["name"].strip().lower() == subcat_name.lower():
                        subcat_id = s["id"]
                        break
                if not subcat_id:
                    subcat_id = database.add_subcategory(cat_id, subcat_name, "", db_path=db_path)

            # Validar JSON de extra_data
            try:
                json.loads(extra_data)
            except Exception:
                extra_data = "{}"

            database.save_question(
                category_id=cat_id,
                subcategory_id=subcat_id,
                question_type=q_type,
                title=title,
                question_text=text,
                points=points,
                estimated_height=height,
                extra_data=extra_data,
                db_path=db_path
            )
            imported_count += 1

    return imported_count


# ============================================================================
# EXPORTACIÓN E IMPORTACIÓN DE EXÁMENES COMPLETOS
# ============================================================================

def export_exam_to_json(exam_id: int, file_path: str, db_path: str = database.DB_FILE) -> bool:
    """
    Exporta un examen completo con toda su configuración e ítems asignados a un archivo JSON.
    """
    exam = database.get_exam_by_id(exam_id, db_path=db_path)
    if not exam:
        return False

    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(exam, f, ensure_ascii=False, indent=2)
    return True


def import_exam_from_json(file_path: str, db_path: str = database.DB_FILE) -> int:
    """
    Importa un examen completo desde un archivo JSON.
    Crea las categorías e ítems correspondientes si no existen.
    """
    with open(file_path, "r", encoding="utf-8", errors="replace") as f:
        exam_data = json.load(f)

    # Limpiar ID del examen importado para que cree un nuevo registro
    exam_data_clean = dict(exam_data)
    exam_data_clean["id"] = None

    items = exam_data.get("items", [])
    clean_items = []

    for item in items:
        # Asegurar categoría
        cat_name = item.get("category_name") or item.get("section_title") or "General"
        cat_id = None
        for c in database.get_categories(db_path):
            if c["name"].strip().lower() == cat_name.strip().lower():
                cat_id = c["id"]
                break
        if not cat_id:
            cat_id = database.add_category(cat_name, cat_name, "", db_path=db_path)

        # Guardar pregunta en el banco si no existe una idéntica
        q_id = item.get("question_id")
        q_exists = database.get_question_by_id(q_id, db_path=db_path) if q_id else None
        if not q_exists:
            q_id = database.save_question(
                category_id=cat_id,
                subcategory_id=None,
                question_type=item.get("question_type", "single_choice"),
                title=item.get("question_title", "Pregunta importada"),
                question_text=item.get("question_text", ""),
                points=float(item.get("points", 5.0)),
                estimated_height=int(item.get("estimated_height", 80)),
                extra_data=item.get("extra_data") if isinstance(item.get("extra_data"), str) else json.dumps(item.get("extra_data", {})),
                db_path=db_path
            )

        clean_items.append({
            "question_id": q_id,
            "section_id": cat_id,
            "item_order": item.get("item_order", len(clean_items) + 1),
            "page_number": item.get("page_number", 1),
            "custom_points": item.get("custom_points"),
            "custom_height": item.get("custom_height"),
            "custom_text": item.get("custom_text")
        })

    new_exam_id = database.save_exam_full(exam_data_clean, clean_items, db_path=db_path)
    return new_exam_id


# ============================================================================
# EXPORTACIÓN E IMPORTACIÓN DE INDICACIONES
# ============================================================================

def export_instructions_to_csv(file_path: str, db_path: str = database.DB_FILE) -> int:
    """
    Exporta el banco de indicaciones generales a un archivo CSV.
    """
    instructions = database.get_instructions(db_path=db_path)
    count = 0
    with open(file_path, mode="w", newline="", encoding="utf-8-sig") as f:
        writer = csv.writer(f)
        writer.writerow(["Titulo", "Contenido", "Por_Defecto"])
        for ins in instructions:
            writer.writerow([ins["title"], ins["content"], 1 if ins["is_default"] else 0])
            count += 1
    return count


def import_instructions_from_csv(file_path: str, db_path: str = database.DB_FILE) -> int:
    """
    Importa indicaciones generales desde un archivo CSV.
    """
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"No se encontró el archivo {file_path}")

    with open(file_path, "r", encoding="utf-8-sig", errors="replace") as f:
        first_line = f.readline()
        delimiter = ";" if ";" in first_line else ","

    count = 0
    with open(file_path, "r", encoding="utf-8-sig", errors="replace") as f:
        reader = csv.reader(f, delimiter=delimiter)
        header = None
        for row in reader:
            if not row or not any(row):
                continue
            if header is None:
                header = [h.strip().lower() for h in row]
                continue
            title = row[0].strip() if len(row) > 0 else ""
            content = row[1].strip() if len(row) > 1 else ""
            is_def = 1 if len(row) > 2 and row[2].strip() in ("1", "si", "sí", "true") else 0
            if title and content:
                database.save_instruction(title=title, content=content, is_default=is_def, db_path=db_path)
                count += 1
    return count


# ============================================================================
# UTILIDAD DE IMÁGENES A BASE64
# ============================================================================

def file_to_base64(image_path: str) -> Optional[str]:
    """
    Lee un archivo de imagen en disco y retorna la cadena Data URL Base64
    lista para incrustar directamente en la etiqueta <img src="..."> del HTML.
    """
    if not os.path.exists(image_path):
        return None

    ext = os.path.splitext(image_path)[1].lower().replace(".", "")
    mime_type = "image/png"
    if ext in ("jpg", "jpeg"):
        mime_type = "image/jpeg"
    elif ext == "gif":
        mime_type = "image/gif"
    elif ext == "svg":
        mime_type = "image/svg+xml"
    elif ext == "webp":
        mime_type = "image/webp"

    try:
        with open(image_path, "rb") as f:
            encoded = base64.b64encode(f.read()).decode("utf-8")
            return f"data:{mime_type};base64,{encoded}"
    except Exception:
        return None
