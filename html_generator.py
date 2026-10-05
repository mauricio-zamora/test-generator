"""
Generador de Documentos HTML para Impresión de Exámenes en Tamaño Carta.
Produce código HTML y CSS idéntico en calidad, estructura y presentación
al documento de referencia Quiz_en_Papel_01.html, con numeración romana automática
de secciones, nota fija sobre 100 y soporte para todos los tipos de preguntas nuevos.
"""

import json
import re
import os
from typing import Dict, Any, List, Optional
import importer_exporter


def to_roman(n: int) -> str:
    """Convierte un entero a número romano para la numeración de partes del examen."""
    val = [
        1000, 900, 500, 400,
        100, 90, 50, 40,
        10, 9, 5, 4,
        1
    ]
    syb = [
        "M", "CM", "D", "CD",
        "C", "XC", "L", "XL",
        "X", "IX", "V", "IV",
        "I"
    ]
    roman_num = ""
    i = 0
    while n > 0:
        for _ in range(n // val[i]):
            roman_num += syb[i]
            n -= val[i]
        i += 1
    return roman_num or "I"


def clean_section_name(name: str) -> str:
    """Remueve cualquier prefijo existente como 'Parte I:', 'Parte 1 -', etc."""
    return re.sub(r'^(Parte\s+[IVX0-9]+[:\s\-\.]*|\d+[\.\-\)]\s*)', '', name, flags=re.IGNORECASE).strip()


def generate_exam_html(exam_data: Dict[str, Any], items: List[Dict[str, Any]]) -> str:
    """
    Genera el documento HTML completo a partir de los datos del examen y sus ítems asignados.
    """
    title = exam_data.get("title", "Examen en Papel")
    institution = exam_data.get("institution", "Universidad de Costa Rica — Escuela de Ingeniería Industrial")
    course_code = exam_data.get("course_code", "II-1119")
    course_name = exam_data.get("course_name", "Fundamentos de Tecnología Digital")
    career = exam_data.get("career", "Ingeniería Industrial")
    professor = exam_data.get("professor", "Profesor del Curso")
    group_name = exam_data.get("group_name", "01")
    exam_date = exam_data.get("exam_date", "______/______/2026")
    period = exam_data.get("period", "I Ciclo Lectivo 2026")
    duration = exam_data.get("duration", "45 minutos")
    instructions_text = exam_data.get("instructions_text", "")

    # Tipografía parametrizable
    font_family = exam_data.get("font_family", "Arial, sans-serif")
    font_size = exam_data.get("font_size", "12px")
    line_height = exam_data.get("line_height", "1.4")

    # Secciones finales configurables
    show_grading_summary = bool(exam_data.get("show_grading_summary", True))
    summary_page_cfg = int(exam_data.get("summary_page", 0))

    show_observations = bool(exam_data.get("show_observations", True))
    observations_lines = int(exam_data.get("observations_lines", 8))
    observations_page_cfg = int(exam_data.get("observations_page", 0))

    # Agrupar ítems por página
    items_by_page: Dict[int, List[Dict[str, Any]]] = {}
    for item in items:
        p = int(item.get("page_number", 1))
        items_by_page.setdefault(p, []).append(item)

    # Determinar páginas máximas
    existing_pages = set(items_by_page.keys())
    if show_grading_summary and summary_page_cfg > 0:
        existing_pages.add(summary_page_cfg)
    if show_observations and observations_page_cfg > 0:
        existing_pages.add(observations_page_cfg)

    total_pages = max(existing_pages) if existing_pages else 1

    # Páginas efectivas para Resumen y Observaciones
    actual_summary_page = total_pages if summary_page_cfg == 0 else summary_page_cfg
    actual_obs_page = total_pages if observations_page_cfg == 0 else observations_page_cfg

    # Asegurar que todas las páginas existan en el diccionario
    for p in range(1, total_pages + 1):
        if p not in items_by_page:
            items_by_page[p] = []

    # Mapeo y orden dinámico de secciones con números romanos
    ordered_section_ids = []
    section_names = {}
    section_points: Dict[int, float] = {}
    total_points = 0.0

    for item in items:
        sec_id = item.get("section_id", item.get("category_id", 1))
        raw_name = item.get("category_name") or item.get("section_title") or f"Sección {sec_id}"
        clean_name = clean_section_name(raw_name)

        if sec_id not in ordered_section_ids:
            ordered_section_ids.append(sec_id)
            section_names[sec_id] = clean_name

        pts = float(item.get("custom_points") or item.get("points") or 0.0)
        section_points[sec_id] = section_points.get(sec_id, 0.0) + pts
        total_points += pts

    # Títulos finales con numeración romana automática: "Parte I: Selección Única y Múltiple"
    section_titles = {}
    for idx, s_id in enumerate(ordered_section_ids, start=1):
        roman = to_roman(idx)
        c_name = section_names.get(s_id, f"Sección {idx}")
        section_titles[s_id] = f"Parte {roman}: {c_name}"

    total_points_int_or_float = int(total_points) if total_points.is_integer() else round(total_points, 1)

    # Reglas CSS de numeración de páginas
    page_counter_css = []
    for p in range(1, total_pages + 1):
        page_counter_css.append(f'.page-{p} .page-number::after {{ content: "Página {p} de {total_pages}"; }}')
    page_counter_rules = "\n        ".join(page_counter_css)

    # Construcción de páginas HTML
    pages_html = []
    global_question_number = 1
    seen_sections_in_exam = set()

    for page_num in range(1, total_pages + 1):
        page_items = items_by_page.get(page_num, [])
        page_content = []

        # Encabezado institucional solo en Página 1
        if page_num == 1:
            page_content.append(f"""
        <!-- ENCABEZADO INSTITUCIONAL -->
        <table class="header-table">
            <tr>
                <td class="institution-title" colspan="3">
                    {institution}
                </td>
            </tr>
            <tr>
                <td style="width: 45%;"><strong>Curso:</strong> {course_code} {course_name}</td>
                <td style="width: 35%;"><strong>Carrera:</strong> {career}</td>
                <td style="width: 20%;" rowspan="3">
                    <table style="width:100%; height:100%; text-align:center; border-collapse:collapse;">
                        <tr><td style="border:none; background-color:#f5f5f5; font-weight:bold; font-size:11px;">NOTA</td></tr>
                        <tr><td style="border:none; font-size:20px; padding:6px 0 2px 0;">/100</td></tr>
                        <tr><td style="border:none; font-size:9px; padding:0 0 6px 0;">Puntos: ______ / {total_points_int_or_float}</td></tr>
                    </table>
                </td>
            </tr>
            <tr>
                <td><strong>Evaluación:</strong> {title}</td>
                <td><strong>Fecha:</strong> {exam_date}</td>
            </tr>
            <tr>
                <td><strong>Periodo:</strong> {period}</td>
                <td><strong>Duración Máxima:</strong> {duration}</td>
            </tr>
        </table>

        <!-- DATOS DEL ESTUDIANTE -->
        <table class="student-info">
            <tr>
                <td style="width: 10%;"><strong>Nombre:</strong></td>
                <td class="line-input" style="width: 38%;"></td>
                <td style="width: 10%; text-align: right;"><strong>Apellidos:</strong></td>
                <td class="line-input" style="width: 28%;"></td>
                <td style="width: 4%;"></td>
            </tr>
            <tr>
                <td style="width: 10%;"><strong>Carné:</strong></td>
                <td class="line-input" style="width: 38%;"></td>
                <td style="width: 10%; text-align: right;"><strong>Grupo:</strong></td>
                <td class="line-input" style="width: 28%;">{group_name}</td>
                <td style="width: 4%;"></td>
            </tr>
        </table>
""")
            if instructions_text.strip():
                page_content.append(f"""
        <!-- INSTRUCCIONES GENERALES -->
        <div class="instructions">
            <h4>Instrucciones Generales:</h4>
            <p style="margin: 0; font-size: 11px;">
                {instructions_text}
            </p>
        </div>
""")

        # Renderizar ítems de esta página
        current_page_section = None
        for item in page_items:
            sec_id = item.get("section_id", item.get("category_id", 1))
            sec_title = section_titles.get(sec_id, f"Sección {sec_id}")
            sec_pts = section_points.get(sec_id, 0.0)
            sec_pts_str = int(sec_pts) if sec_pts.is_integer() else round(sec_pts, 1)

            # Si cambia la sección en esta página o es la primera vez que se muestra
            if sec_id != current_page_section:
                continuation_note = " (continuación)" if sec_id in seen_sections_in_exam else ""
                page_content.append(f"""
        <div class="section-title">
            <h3>{sec_title}{continuation_note}</h3>
            <span class="section-total">Total sección: {sec_pts_str} puntos</span>
        </div>
""")
                current_page_section = sec_id
                seen_sections_in_exam.add(sec_id)

            item_html = render_single_item(item, global_question_number)
            page_content.append(item_html)
            global_question_number += 1

        # Resumen de Calificación en la página especificada
        if show_grading_summary and page_num == actual_summary_page:
            summary_rows = []
            for s_id in ordered_section_ids:
                s_title = section_titles.get(s_id, f"Sección {s_id}")
                s_pts = section_points.get(s_id, 0.0)
                s_pts_display = int(s_pts) if s_pts.is_integer() else round(s_pts, 1)
                summary_rows.append(f"""
                <tr>
                    <td style="border: 1px solid #000; padding: 6px;">{s_title}</td>
                    <td style="border: 1px solid #000; padding: 6px; text-align: center;">{s_pts_display}</td>
                    <td style="border: 1px solid #000; padding: 6px;"></td>
                </tr>""")

            summary_table_html = f"""
        <div style="margin-top: 18px; border-top: 1px solid #000; padding-top: 8px;">
            <h3 style="margin: 0 0 6px 0; font-size: 13px; text-transform: uppercase;">Resumen de Calificación</h3>
            <table style="width: 100%; border-collapse: collapse;">
                <thead>
                    <tr style="background-color: #f5f5f5; font-weight: bold;">
                        <td style="border: 1px solid #000; padding: 5px; text-align: left;">Sección</td>
                        <td style="border: 1px solid #000; padding: 5px; text-align: center; width: 25%;">Puntaje Máximo</td>
                        <td style="border: 1px solid #000; padding: 5px; text-align: center; width: 25%;">Puntaje Obtenido</td>
                    </tr>
                </thead>
                <tbody>
                    {"".join(summary_rows)}
                    <tr style="font-weight: bold; background-color: #fcfcfc;">
                        <td style="border: 1px solid #000; padding: 5px;">Total</td>
                        <td style="border: 1px solid #000; padding: 5px; text-align: center;">{total_points_int_or_float}</td>
                        <td style="border: 1px solid #000; padding: 5px;"></td>
                    </tr>
                </tbody>
            </table>
        </div>
"""
            page_content.append(summary_table_html)

        # Observaciones del Profesor en la página especificada
        if show_observations and page_num == actual_obs_page:
            lines_h = int(observations_lines * 22) + 2
            page_content.append(f"""
        <div style="margin-top: 14px;">
            <h3 style="margin: 0 0 6px 0; font-size: 13px; text-transform: uppercase;">Observaciones del Profesor</h3>
            <div class="development-box lines-pattern" style="height: {lines_h}px;"></div>
        </div>
""")

        # Pie de página para cada hoja
        page_html = f"""
    <!-- ============ PÁGINA {page_num} ============ -->
    <div class="page page-{page_num}">
        {"".join(page_content)}
        <div class="page-footer">
            <div class="footer-student-verify">
                <span>Estudiante: <span class="footer-line" style="width: 220px;"></span></span>
                <span>Carné: <span class="footer-line" style="width: 90px;"></span></span>
            </div>
            <span class="page-number"></span>
        </div>
    </div>
"""
        pages_html.append(page_html)

    # Documento completo ensamblado
    full_html = f"""<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{course_code} {course_name} - {title}</title>
    <style>
        /* --- ESTILOS GENERALES (PANTALLA) --- */
        body {{
            font-family: {font_family};
            font-size: {font_size};
            line-height: {line_height};
            color: #111;
            margin: 0;
            padding: 20px;
            background-color: #f0f2f5;
        }}

        /* Contenedor tamaño Carta Estándar (8.5 x 11 pulgadas) */
        .page {{
            background: white;
            width: 8.5in;
            height: 11in;
            margin: 0 auto 20px auto;
            padding: 0.5in 0.6in 0.9in 0.6in;
            box-shadow: 0 0 10px rgba(0,0,0,0.15);
            box-sizing: border-box;
            position: relative;
            page-break-after: always;
            break-after: page;
        }}

        /* --- ENCABEZADO E INFORMACIÓN DEL CURSO --- */
        .header-table {{
            width: 100%;
            border-collapse: collapse;
            margin-bottom: 12px;
        }}
        .header-table td {{
            border: 1px solid #000;
            padding: 5px 8px;
            vertical-align: top;
        }}
        .institution-title {{
            text-align: center;
            font-weight: bold;
            font-size: 13px;
            text-transform: uppercase;
            background-color: #f5f5f5;
        }}

        /* Datos del Estudiante */
        .student-info {{
            width: 100%;
            margin-bottom: 12px;
            border-collapse: collapse;
        }}
        .student-info td {{
            padding: 4px 2px;
        }}
        .line-input {{
            border-bottom: 1px solid #000;
        }}

        /* Instrucciones */
        .instructions {{
            border: 1px dashed #000;
            padding: 8px;
            margin-bottom: 15px;
            background-color: #fafafa;
            text-align: justify;
        }}
        .instructions h4 {{
            margin: 0 0 4px 0;
            font-size: 12px;
            text-transform: uppercase;
        }}

        /* --- TÍTULOS DE SECCIÓN CON PUNTAJE --- */
        .section-title {{
            display: flex;
            justify-content: space-between;
            align-items: baseline;
            border-bottom: 2px solid #000;
            margin: 14px 0 10px 0;
            padding-bottom: 3px;
        }}
        .section-title h3 {{
            margin: 0;
            font-size: 13px;
            text-transform: uppercase;
        }}
        .section-title .section-total {{
            font-size: 11px;
            font-weight: bold;
            white-space: nowrap;
        }}

        /* --- FORMATOS DE PREGUNTAS --- */
        .question-block {{
            margin-bottom: 12px;
            page-break-inside: avoid;
            break-inside: avoid;
        }}
        .question-text {{
            font-weight: bold;
            margin-bottom: 6px;
        }}
        .question-points {{
            font-weight: normal;
            font-style: italic;
            font-size: 10.5px;
            color: #333;
        }}

        /* Selección Única y Múltiple (2 Columnas) */
        .options-grid {{
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 5px 15px;
            padding-left: 15px;
        }}
        .option-item {{
            display: flex;
            align-items: center;
        }}
        .checkbox-sim {{
            width: 12px;
            height: 12px;
            border: 1px solid #000;
            display: inline-block;
            margin-right: 8px;
            border-radius: 2px;
            flex-shrink: 0;
        }}
        .radio-sim {{
            border-radius: 50%;
        }}

        /* Falso y Verdadero */
        .tf-container {{
            margin-top: 6px;
            padding-left: 10px;
        }}
        .tf-item {{
            display: flex;
            align-items: center;
            margin-bottom: 5px;
        }}
        .tf-badges {{
            display: inline-flex;
            gap: 10px;
            align-items: center;
            margin-right: 12px;
            font-size: 11px;
        }}
        .tf-circle {{
            display: inline-block;
            width: 14px;
            height: 14px;
            border: 1px solid #000;
            border-radius: 50%;
            vertical-align: middle;
            margin-right: 3px;
        }}

        /* Bloques de Código (<pre><code>) */
        .code-question-container {{
            display: flex;
            gap: 15px;
            align-items: flex-start;
            margin-top: 8px;
        }}
        .python-code-box {{
            background-color: #f8f9fa;
            border: 1px solid #999;
            padding: 8px 12px;
            font-family: "Courier New", Courier, monospace;
            font-size: 11px;
            line-height: 1.35;
            margin: 0;
            white-space: pre;
        }}
        .code-question-content {{
            flex: 1;
        }}

        /* --- ZONAS DE RESPUESTA --- */
        .development-box {{
            margin-top: 8px;
            width: 100%;
            border: 1px solid #000;
            box-sizing: border-box;
        }}

        .lines-pattern {{
            background-image: linear-gradient(#bbb 1px, transparent 1px);
            background-size: 100% 22px;
            line-height: 22px;
            print-color-adjust: exact;
            -webkit-print-color-adjust: exact;
        }}

        .lines-5 {{ height: 111px; }}
        .lines-6 {{ height: 133px; }}
        .lines-8 {{ height: 177px; }}
        .lines-10 {{ height: 221px; }}

        /* Recuadro de código sin renglones */
        .code-writing-box {{
            background-color: #fff;
            border: 1px solid #000;
        }}

        /* --- IMÁGENES --- */
        .question-image {{
            border: 1px solid #ccc;
            border-radius: 2px;
            height: auto;
            display: block;
        }}

        /* --- ASOCIACIÓN / APAREAMIENTO --- */
        .association-table {{
            width: 100%;
            border-collapse: collapse;
            margin-top: 10px;
        }}
        .association-table th {{
            border: 1px solid #000;
            padding: 6px;
        }}
        .association-table td {{
            padding: 7px 5px;
            vertical-align: middle;
            border-bottom: 1px dashed #ccc;
        }}
        .col-left {{ width: 48%; }}
        .col-center {{ width: 8%; text-align: center; }}
        .col-right {{ width: 44%; }}
        .paren-sim {{
            display: inline-block;
            width: 28px;
            border-bottom: 1px solid #000;
            text-align: center;
        }}

        /* --- PIE DE PÁGINA --- */
        .page-footer {{
            position: absolute;
            bottom: 0.3in;
            left: 0.6in;
            right: 0.6in;
            border-top: 1px solid #000;
            padding-top: 6px;
            font-size: 10px;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }}
        .footer-student-verify {{
            display: flex;
            gap: 15px;
            width: 78%;
        }}
        .footer-line {{
            display: inline-block;
            border-bottom: 1px dashed #666;
            height: 14px;
        }}

        /* --- CONFIGURACIÓN ESTRICTA DE IMPRESIÓN --- */
        @media print {{
            body {{
                background-color: #fff;
                padding: 0;
                margin: 0;
            }}
            .page {{
                width: 8.5in;
                height: 11in;
                margin: 0;
                padding: 0.5in 0.6in 0.9in 0.6in;
                box-shadow: none;
                page-break-after: always;
                break-after: page;
            }}
            .instructions {{
                background-color: #fff;
            }}
            .lines-pattern {{
                print-color-adjust: exact;
                -webkit-print-color-adjust: exact;
            }}
        }}

        @page {{
            size: letter;
            margin: 0;
        }}

        /* Numeración automática de páginas */
        {page_counter_rules}
    </style>
</head>
<body>

{"".join(pages_html)}

</body>
</html>
"""
    return full_html


def resolve_image_src(img_data: Optional[str]) -> str:
    """
    Retorna la fuente de imagen lista para HTML.
    Si ya es Data URL Base64 la devuelve intacta, o si es ruta a archivo en disco
    la convierte a Data URL Base64.
    """
    if not img_data:
        return ""
    if img_data.startswith("data:"):
        return img_data
    if os.path.exists(img_data):
        b64 = importer_exporter.file_to_base64(img_data)
        if b64:
            return b64
    return img_data


def render_single_item(item: Dict[str, Any], question_num: int) -> str:
    """
    Renderiza el bloque HTML para un ítem según su tipo.
    """
    q_type = item.get("question_type", "single_choice")
    text = item.get("custom_text") or item.get("question_text", "")
    pts = float(item.get("custom_points") or item.get("points") or 0.0)
    pts_str = int(pts) if pts.is_integer() else round(pts, 1)

    extra = item.get("extra_data", {})
    if isinstance(extra, str):
        try:
            extra = json.loads(extra) if extra else {}
        except Exception:
            extra = {}

    if q_type == "single_choice":
        options = extra.get("options", [])
        pts_label = f"({pts_str} puntos — Selección única)"
        opts_html = []
        for opt in options:
            opts_html.append(f'<div class="option-item"><span class="checkbox-sim radio-sim"></span> {opt}</div>')
        return f"""
        <div class="question-block">
            <div class="question-text">{question_num}. {text} <span class="question-points">{pts_label}</span></div>
            <div class="options-grid">
                {"".join(opts_html)}
            </div>
        </div>
"""

    elif q_type == "multiple_choice":
        options = extra.get("options", [])
        pts_label = f"({pts_str} puntos — Selección múltiple)"
        opts_html = []
        for opt in options:
            opts_html.append(f'<div class="option-item"><span class="checkbox-sim"></span> {opt}</div>')
        return f"""
        <div class="question-block">
            <div class="question-text">{question_num}. {text} <span class="question-points">{pts_label}</span></div>
            <div class="options-grid">
                {"".join(opts_html)}
            </div>
        </div>
"""

    elif q_type == "true_false":
        statements = extra.get("statements", [])
        pts_label = f"({pts_str} puntos — Falso o Verdadero)"
        if statements:
            rows_html = []
            for st in statements:
                rows_html.append(f"""
                <div class="tf-item">
                    <div class="tf-badges">
                        <span><span class="tf-circle"></span><strong>V</strong></span>
                        <span><span class="tf-circle"></span><strong>F</strong></span>
                    </div>
                    <div>{st}</div>
                </div>""")
            return f"""
        <div class="question-block">
            <div class="question-text">{question_num}. {text} <span class="question-points">{pts_label}</span></div>
            <div class="tf-container">
                {"".join(rows_html)}
            </div>
        </div>
"""
        else:
            return f"""
        <div class="question-block">
            <div class="question-text">
                <span style="margin-right: 10px;">
                    <span class="tf-circle"></span><strong>V</strong> &nbsp;
                    <span class="tf-circle"></span><strong>F</strong>
                </span>
                {question_num}. {text} <span class="question-points">{pts_label}</span>
            </div>
        </div>
"""

    elif q_type == "development":
        lines_count = int(extra.get("lines_count", 10))
        lines_class = f"lines-{lines_count}" if lines_count in (5, 6, 8, 10) else ""
        style_attr = f' style="height: {lines_count * 22 + 1}px;"' if not lines_class else ""
        pts_label = f"({pts_str} puntos)"
        return f"""
        <div class="question-block">
            <div class="question-text">{question_num}. {text} <span class="question-points">{pts_label}</span></div>
            <div class="development-box lines-pattern {lines_class}"{style_attr}></div>
        </div>
"""

    elif q_type == "code_writing":
        # Espacio para escribir código en blanco (SIN renglones impresos)
        lines_count = int(extra.get("lines_count", 12))
        box_h = lines_count * 22 + 1
        pts_label = f"({pts_str} puntos)"
        return f"""
        <div class="question-block">
            <div class="question-text">{question_num}. {text} <span class="question-points">{pts_label}</span></div>
            <div class="development-box code-writing-box" style="height: {box_h}px;"></div>
        </div>
"""

    elif q_type == "code_analysis":
        code = extra.get("code", "")
        sub_prompt = extra.get("sub_prompt", "")
        lines_count = int(extra.get("lines_count", 5))
        lines_class = f"lines-{lines_count}" if lines_count in (5, 6, 8, 10) else ""
        style_attr = f' style="height: {lines_count * 22 + 1}px;"' if not lines_class else ""
        pts_label = f"({pts_str} puntos)"
        return f"""
        <div class="question-block">
            <div class="question-text">{question_num}. {text} <span class="question-points">{pts_label}</span></div>
            <div class="code-question-container">
<pre class="python-code-box">{code}</pre>
                <div class="code-question-content">
                    <div class="question-text" style="font-weight: normal; padding-left: 5px;">
                        {sub_prompt}
                    </div>
                </div>
            </div>
            <div class="development-box lines-pattern {lines_class}"{style_attr}></div>
        </div>
"""

    elif q_type == "single_image":
        text_before = extra.get("text_before", "")
        img_src = resolve_image_src(extra.get("image_base64") or extra.get("image_path"))
        width_pct = extra.get("image_width_percent", 70)
        align = extra.get("image_align", "center")
        text_after = extra.get("text_after", "")
        lines_count = int(extra.get("lines_count", 0))

        content_parts = []
        if text_before:
            content_parts.append(f'<div style="margin: 4px 0 6px 0;">{text_before}</div>')
        if img_src:
            content_parts.append(f'<div style="text-align: {align}; margin: 8px 0;"><img src="{img_src}" class="question-image" style="max-width: {width_pct}%; margin: 0 auto;"></div>')
        if text_after:
            content_parts.append(f'<div style="margin: 6px 0 6px 0;">{text_after}</div>')
        if lines_count > 0:
            lines_class = f"lines-{lines_count}" if lines_count in (5, 6, 8, 10) else ""
            style_attr = f' style="height: {lines_count * 22 + 1}px;"' if not lines_class else ""
            content_parts.append(f'<div class="development-box lines-pattern {lines_class}"{style_attr}></div>')

        pts_label = f"({pts_str} puntos)"
        return f"""
        <div class="question-block">
            <div class="question-text">{question_num}. {text} <span class="question-points">{pts_label}</span></div>
            {"".join(content_parts)}
        </div>
"""

    elif q_type == "double_image":
        text_before = extra.get("text_before", "")
        img1_src = resolve_image_src(extra.get("image1_base64") or extra.get("image1_path"))
        width1_pct = extra.get("image1_width_percent", 48)
        text_after1 = extra.get("text_after_img1", "")

        img2_src = resolve_image_src(extra.get("image2_base64") or extra.get("image2_path"))
        width2_pct = extra.get("image2_width_percent", 48)
        text_after2 = extra.get("text_after_img2", "")

        layout = extra.get("layout", "side_by_side")
        lines_count = int(extra.get("lines_count", 0))

        content_parts = []
        if text_before:
            content_parts.append(f'<div style="margin: 4px 0 6px 0;">{text_before}</div>')

        if layout == "side_by_side":
            imgs_html = f"""
            <div style="display: flex; gap: 15px; justify-content: center; align-items: flex-start; margin: 8px 0;">
                <div style="width: {width1_pct}%; text-align: center;">
                    {f'<img src="{img1_src}" class="question-image" style="width: 100%;">' if img1_src else ''}
                    {f'<div style="margin-top: 4px; font-size: 11px;">{text_after1}</div>' if text_after1 else ''}
                </div>
                <div style="width: {width2_pct}%; text-align: center;">
                    {f'<img src="{img2_src}" class="question-image" style="width: 100%;">' if img2_src else ''}
                    {f'<div style="margin-top: 4px; font-size: 11px;">{text_after2}</div>' if text_after2 else ''}
                </div>
            </div>
"""
            content_parts.append(imgs_html)
        else:
            # Vertical
            if img1_src:
                content_parts.append(f'<div style="text-align: center; margin: 8px 0;"><img src="{img1_src}" class="question-image" style="max-width: {width1_pct}%;"></div>')
            if text_after1:
                content_parts.append(f'<div style="margin: 4px 0 6px 0;">{text_after1}</div>')
            if img2_src:
                content_parts.append(f'<div style="text-align: center; margin: 8px 0;"><img src="{img2_src}" class="question-image" style="max-width: {width2_pct}%;"></div>')
            if text_after2:
                content_parts.append(f'<div style="margin: 4px 0 6px 0;">{text_after2}</div>')

        if lines_count > 0:
            lines_class = f"lines-{lines_count}" if lines_count in (5, 6, 8, 10) else ""
            style_attr = f' style="height: {lines_count * 22 + 1}px;"' if not lines_class else ""
            content_parts.append(f'<div class="development-box lines-pattern {lines_class}"{style_attr}></div>')

        pts_label = f"({pts_str} puntos)"
        return f"""
        <div class="question-block">
            <div class="question-text">{question_num}. {text} <span class="question-points">{pts_label}</span></div>
            {"".join(content_parts)}
        </div>
"""

    elif q_type == "association":
        pairs = extra.get("pairs", [])
        distractors = extra.get("extra_distractors", [])
        pts_label = f"({pts_str} puntos)"
        rows_html = []
        for pair in pairs:
            letter = pair.get("letter", "")
            definition = pair.get("definition", "")
            concept = pair.get("concept", "")
            rows_html.append(f"""
                <tr>
                    <td class="col-left"><strong>{letter}.</strong> {definition}</td>
                    <td class="col-center">( <span class="paren-sim"></span> )</td>
                    <td class="col-right">{concept}</td>
                </tr>""")

        for dist in distractors:
            rows_html.append(f"""
                <tr>
                    <td class="col-left"></td>
                    <td class="col-center">( <span class="paren-sim"></span> )</td>
                    <td class="col-right">{dist}</td>
                </tr>""")

        return f"""
        <div class="question-block">
            <p style="margin: 0 0 6px 0;">{text} <span class="question-points">{pts_label}</span></p>
            <table class="association-table">
                <thead>
                    <tr style="background-color: #f5f5f5; font-weight: bold;">
                        <th style="text-align: left;">Columna A (Definición)</th>
                        <th style="text-align: center;">Vínculo</th>
                        <th style="text-align: left;">Columna B (Concepto)</th>
                    </tr>
                </thead>
                <tbody>
                    {"".join(rows_html)}
                </tbody>
            </table>
        </div>
"""

    else:
        return f"""
        <div class="question-block">
            <div class="question-text">{question_num}. {text} <span class="question-points">({pts_str} puntos)</span></div>
        </div>
"""
