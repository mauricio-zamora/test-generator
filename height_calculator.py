"""
Módulo de Cálculo de Alturas y Motor de Paginación.
Estima el espacio vertical en píxeles (a 96 DPI) para páginas tamaño Carta (8.5 x 11 pulgadas)
y analiza si las preguntas caben cómodamente o desbordan la página al imprimir.
Soporta todos los tipos de preguntas: selección, falso/verdadero, desarrollo,
escritura de código en blanco, análisis de código, preguntas con 1 y 2 imágenes, y asociación.
"""

import math
import json
import re
from typing import List, Dict, Any, Tuple

# Constantes de dimensiones estándar para Carta a 96 DPI
PAGE_TOTAL_HEIGHT = 1056
PAGE_PADDING_TOP = 48       # 0.5 pulgada
PAGE_PADDING_BOTTOM = 86    # 0.9 pulgada
PAGE_PRINTABLE_HEIGHT = PAGE_TOTAL_HEIGHT - PAGE_PADDING_TOP - PAGE_PADDING_BOTTOM  # 922 px
PAGE_FOOTER_HEIGHT = 35     # Pie de página con firma y carné

# Encabezados y bloques fijos de la Página 1
HEADER_TABLE_HEIGHT = 115
STUDENT_INFO_HEIGHT = 45
INSTRUCTIONS_BASE_HEIGHT = 65

# Elementos finales configurables
GRADING_SUMMARY_HEIGHT = 160
SECTION_TITLE_HEIGHT = 36   # Alto del título de sección


def estimate_item_height(
    question_type: str,
    question_text: str,
    extra_data_dict_or_str: Any,
    font_size_px: float = 12.0,
    line_height_multiplier: float = 1.4
) -> int:
    """
    Estima el alto en píxeles que ocupará una pregunta renderizada en HTML.
    """
    extra = extra_data_dict_or_str
    if isinstance(extra, str):
        try:
            extra = json.loads(extra) if extra else {}
        except Exception:
            extra = {}
    elif not isinstance(extra, dict):
        extra = {}

    scale = font_size_px / 12.0
    text_line_h = 17.0 * scale * (line_height_multiplier / 1.4)
    approx_chars_per_line = int(88 / scale)

    raw_q_text = question_text or ""

    # Altura de tablas HTML: contar filas <tr>
    table_rows = len(re.findall(r'<tr\b', raw_q_text, re.IGNORECASE))
    table_height = (table_rows * int(30 * scale) + 14) if table_rows > 0 else 0

    # Altura de bloques de código <pre>
    pre_blocks = re.findall(r'<pre[^>]*>(.*?)</pre>', raw_q_text, re.DOTALL | re.IGNORECASE)
    pre_lines_count = sum(len(b.strip().splitlines()) for b in pre_blocks)
    pre_height = (pre_lines_count * int(18 * scale) + 16) if pre_blocks else 0

    # Texto restante fuera de tablas y bloques de código
    text_sans_tables = re.sub(r'<table\b.*?</table>', '', raw_q_text, flags=re.DOTALL | re.IGNORECASE)
    text_sans_code = re.sub(r'<pre\b.*?</pre>', '', text_sans_tables, flags=re.DOTALL | re.IGNORECASE)

    # Limpiar etiquetas HTML para conteo de caracteres
    plain_text = re.sub(r'<[^>]+>', ' ', text_sans_code)
    plain_text = " ".join(plain_text.split())

    num_text_lines = max(1, math.ceil(len(plain_text) / max(30, approx_chars_per_line))) if plain_text else (0 if (table_rows > 0 or pre_blocks) else 1)
    question_text_height = int(num_text_lines * text_line_h) + table_height + pre_height + 6

    if question_type in ("single_choice", "multiple_choice"):
        options = extra.get("options", [])
        num_options = len(options)
        grid_rows = max(1, math.ceil(num_options / 2))
        options_height = int(grid_rows * (18 * scale + 5))
        return max(50, question_text_height + options_height + 12)

    elif question_type == "true_false":
        statements = extra.get("statements", [])
        if statements:
            rows_height = len(statements) * int(42 * scale)
        else:
            rows_height = int(28 * scale)
        return max(50, question_text_height + rows_height + 12)

    elif question_type == "development":
        lines_count = int(extra.get("lines_count", 10))
        lines_height = (lines_count * 22 + 2) if lines_count > 0 else 0
        extra_h = (8 + lines_height) if lines_count > 0 else 0
        return max(40, question_text_height + extra_h + 12)

    elif question_type == "code_writing":
        # Recuadro en blanco sin renglones impresos
        lines_count = int(extra.get("lines_count", 12))
        box_height = (lines_count * 22 + 2) if lines_count > 0 else 0
        extra_h = (8 + box_height) if lines_count > 0 else 0
        return max(40, question_text_height + extra_h + 12)

    elif question_type == "code_analysis":
        code = extra.get("code", "")
        code_lines = len(code.splitlines()) if code else 4
        code_box_height = int(code_lines * 15 + 18)
        sub_prompt = extra.get("sub_prompt", "")
        sub_prompt_lines = max(1, math.ceil(len(sub_prompt) / 45))
        sub_prompt_height = int(sub_prompt_lines * text_line_h)
        container_height = max(code_box_height, sub_prompt_height) + 8
        lines_count = int(extra.get("lines_count", 5))
        lines_height = (lines_count * 22 + 2) if lines_count > 0 else 0
        extra_h = (8 + lines_height) if lines_count > 0 else 0
        return max(80, question_text_height + container_height + extra_h + 12)

    elif question_type == "single_image":
        text_before = extra.get("text_before", "")
        t_before_lines = max(0, math.ceil(len(text_before) / approx_chars_per_line)) if text_before else 0
        t_before_h = int(t_before_lines * text_line_h)

        # Altura estimada de imagen según ancho porcentual o alto fijo
        w_pct = float(extra.get("image_width_percent", 70))
        img_h = int(220 * (w_pct / 100.0))

        text_after = extra.get("text_after", "")
        t_after_lines = max(0, math.ceil(len(text_after) / approx_chars_per_line)) if text_after else 0
        t_after_h = int(t_after_lines * text_line_h)

        lines_count = int(extra.get("lines_count", 0))
        lines_h = (lines_count * 22 + 2) if lines_count > 0 else 0

        return max(120, question_text_height + t_before_h + img_h + t_after_h + lines_h + 20)

    elif question_type == "double_image":
        text_before = extra.get("text_before", "")
        t_before_lines = max(0, math.ceil(len(text_before) / approx_chars_per_line)) if text_before else 0
        t_before_h = int(t_before_lines * text_line_h)

        w1_pct = float(extra.get("image1_width_percent", 50))
        img1_h = int(180 * (w1_pct / 100.0))

        text_after1 = extra.get("text_after_img1", "")
        t_after1_lines = max(0, math.ceil(len(text_after1) / approx_chars_per_line)) if text_after1 else 0
        t_after1_h = int(t_after1_lines * text_line_h)

        w2_pct = float(extra.get("image2_width_percent", 50))
        img2_h = int(180 * (w2_pct / 100.0))

        text_after2 = extra.get("text_after_img2", "")
        t_after2_lines = max(0, math.ceil(len(text_after2) / approx_chars_per_line)) if text_after2 else 0
        t_after2_h = int(t_after2_lines * text_line_h)

        lines_count = int(extra.get("lines_count", 0))
        lines_h = (lines_count * 22 + 2) if lines_count > 0 else 0

        layout = extra.get("layout", "vertical")
        if layout == "side_by_side":
            images_h = max(img1_h, img2_h)
        else:
            images_h = img1_h + img2_h

        return max(160, question_text_height + t_before_h + images_h + t_after1_h + t_after2_h + lines_h + 24)

    elif question_type == "association":
        pairs = extra.get("pairs", [])
        distractors = extra.get("extra_distractors", [])
        total_rows = len(pairs) + len(distractors)
        table_height = 28 + (total_rows * 32) + 10
        return max(100, question_text_height + table_height + 12)

    else:
        return max(60, question_text_height + 40)


def get_page_capacity(page_number: int) -> int:
    """
    Retorna la capacidad bruta disponible para preguntas en una página determinada.
    """
    if page_number == 1:
        # Página 1: Descuenta encabezado institucional, datos de estudiante e instrucciones
        usable = PAGE_PRINTABLE_HEIGHT - HEADER_TABLE_HEIGHT - STUDENT_INFO_HEIGHT - INSTRUCTIONS_BASE_HEIGHT - PAGE_FOOTER_HEIGHT
        return usable  # Aprox 662 px
    else:
        # Otras páginas
        return PAGE_PRINTABLE_HEIGHT - PAGE_FOOTER_HEIGHT  # Aprox 887 px


def analyze_exam_pagination(
    exam_items: List[Dict[str, Any]],
    show_summary_table: bool = True,
    summary_page: int = 0,
    show_observations: bool = True,
    observations_lines: int = 8,
    observations_page: int = 0,
    font_size_str: str = "12px",
    line_height_str: str = "1.4"
) -> Dict[str, Any]:
    """
    Analiza la ocupación de cada página considerando la ubicación exacta
    elegida para el Resumen de Calificación y las Observaciones del Profesor.
    """
    try:
        font_size_px = float(font_size_str.replace("px", "").replace("pt", "").strip())
    except Exception:
        font_size_px = 12.0

    try:
        line_height_val = float(line_height_str.strip())
    except Exception:
        line_height_val = 1.4

    # Determinar total de páginas
    page_numbers = set(int(item.get("page_number", 1)) for item in exam_items)
    if show_summary_table and summary_page > 0:
        page_numbers.add(summary_page)
    if show_observations and observations_page > 0:
        page_numbers.add(observations_page)

    max_page = max(page_numbers) if page_numbers else 1

    # Páginas efectivas donde se mostrarán el resumen y las observaciones
    actual_summary_page = max_page if summary_page == 0 else summary_page
    actual_obs_page = max_page if observations_page == 0 else observations_page

    # Agrupar ítems por página
    items_by_page: Dict[int, List[Dict[str, Any]]] = {}
    for p in range(1, max_page + 1):
        items_by_page[p] = []

    for item in exam_items:
        p = int(item.get("page_number", 1))
        items_by_page.setdefault(p, []).append(item)

    pages_report = []

    for p in range(1, max_page + 1):
        capacity = get_page_capacity(p)
        used_px = 0
        p_items = items_by_page.get(p, [])
        page_sections_started = set()

        for it in p_items:
            sec_id = it.get("section_id", it.get("category_id"))
            if sec_id and (sec_id not in page_sections_started):
                used_px += SECTION_TITLE_HEIGHT
                page_sections_started.add(sec_id)

            custom_h = it.get("custom_height")
            if custom_h and int(custom_h) > 0:
                h = int(custom_h)
            else:
                h = estimate_item_height(
                    it.get("question_type", "single_choice"),
                    it.get("question_text", ""),
                    it.get("extra_data", {}),
                    font_size_px=font_size_px,
                    line_height_multiplier=line_height_val
                )
            used_px += h

        # Sumar Resumen de Calificación si está asignado a esta página
        if show_summary_table and p == actual_summary_page:
            used_px += GRADING_SUMMARY_HEIGHT

        # Sumar Observaciones del Profesor si están asignadas a esta página
        if show_observations and p == actual_obs_page:
            obs_box_h = (int(observations_lines * 22) + 36) if observations_lines > 0 else 24
            used_px += obs_box_h

        percentage = round((used_px / capacity) * 100, 1) if capacity > 0 else 0

        if percentage <= 94.0:
            status = "OPTIMO"
            status_color = "#2e7d32"  # Verde
        elif percentage <= 104.0:
            status = "AJUSTADO"
            status_color = "#e65100"  # Naranja
        else:
            status = "DESBORDE"
            status_color = "#c62828"  # Rojo

        pages_report.append({
            "page": p,
            "used_px": used_px,
            "capacity_px": capacity,
            "percentage": percentage,
            "item_count": len(p_items),
            "status": status,
            "status_color": status_color
        })

    return {
        "total_pages": max_page,
        "pages_report": pages_report,
        "has_overflow": any(r["status"] == "DESBORDE" for r in pages_report)
    }


def auto_distribute_items(
    items: List[Dict[str, Any]],
    show_summary_table: bool = True,
    summary_page: int = 0,
    show_observations: bool = True,
    observations_lines: int = 8,
    observations_page: int = 0,
    font_size_str: str = "12px",
    line_height_str: str = "1.4"
) -> List[Dict[str, Any]]:
    """
    Distribuye automáticamente los ítems en páginas evitando sobrepasar la capacidad recomendada.
    """
    try:
        font_size_px = float(font_size_str.replace("px", "").replace("pt", "").strip())
    except Exception:
        font_size_px = 12.0

    try:
        line_height_val = float(line_height_str.strip())
    except Exception:
        line_height_val = 1.4

    current_page = 1
    current_page_used = 0
    page_sections_started = set()
    assigned_items = []

    for item in items:
        sec_id = item.get("section_id", item.get("category_id"))
        sec_header_cost = 0
        if sec_id and (sec_id not in page_sections_started):
            sec_header_cost = SECTION_TITLE_HEIGHT

        custom_h = item.get("custom_height")
        if custom_h and int(custom_h) > 0:
            item_h = int(custom_h)
        else:
            item_h = estimate_item_height(
                item.get("question_type", "single_choice"),
                item.get("question_text", ""),
                item.get("extra_data", {}),
                font_size_px=font_size_px,
                line_height_multiplier=line_height_val
            )

        total_item_cost = sec_header_cost + item_h
        page_limit = 660 if current_page == 1 else 870

        if current_page_used > 0 and (current_page_used + total_item_cost > page_limit):
            current_page += 1
            current_page_used = 0
            page_sections_started = set()
            sec_header_cost = SECTION_TITLE_HEIGHT if sec_id else 0
            total_item_cost = sec_header_cost + item_h

        if sec_id:
            page_sections_started.add(sec_id)

        current_page_used += total_item_cost

        updated_item = dict(item)
        updated_item["page_number"] = current_page
        assigned_items.append(updated_item)

    return assigned_items
