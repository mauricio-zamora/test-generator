# Generador de Exámenes Impresos en Papel (Formato Carta)

Aplicación de escritorio profesional desarrollada en **Python (Tkinter)** con persistencia en **SQLite** para la creación, parametrización, paginación visual y exportación a **HTML listo para impresión** de exámenes académicos en tamaño Carta (8.5 x 11 pulgadas).

---

## 🚀 Novedades y Características Avanzadas

### 1. Secciones de Cierre Personalizables y Flexibles
- **Resumen de Calificación**:
  - Activación / desactivación con casilla.
  - Selección de en **qué página** ubicarlo: *Última Página (Automático)* o una página específica (*Página 1, 2, 3, etc.*).
- **Observaciones del Profesor**:
  - Activación / desactivación con casilla.
  - Control de la **cantidad exacta de renglones** reglamentarios (ej. 4, 8, 10, 15 renglones).
  - Selección de en **qué página** ubicarlo (*Última Página* o página específica).

### 2. Numeración Romana Automática de Secciones
- Las categorías ya no requieren tener "Parte I:" escrito manualmente en el nombre.
- El sistema asigna automáticamente la numeración romana (`Parte I: ...`, `Parte II: ...`, `Parte III: ...`) según el orden en que las preguntas aparecen en el examen.
- Si una sección continúa en la siguiente página, se titula automáticamente `Parte X: [Nombre] (continuación)`.
- En la tabla de **Resumen de Calificación**, las secciones se listan ordenadas con su numeración romana respectiva.

### 3. Calificación Fija sobre 100 vs. Puntos Totales
- En el encabezado institucional de la Página 1, el recuadro superior derecho muestra siempre:
  - **`NOTA: / 100`** (escala de 0 a 100).
  - **`Puntos: ______ / [Puntos Totales Reales]`** (suma dinámica de los puntos asignados a las preguntas).
- En la tabla de resumen de calificación final, la suma de puntos máximos refleja el total real de puntos del examen.

### 4. Nuevos Tipos de Preguntas e Ítems
1. **Selección Única**: Círculos radiales simulados (`○ a) ...`).
2. **Selección Múltiple**: Casillas cuadradas simuladas (`□ a) ...`).
3. **Falso y Verdadero**: Formato idéntico a selección (enunciado primero y opciones Verdadero / Falso abajo para marcar), para enunciado individual o lista de afirmaciones.
4. **Desarrollo (con Renglones)**: Renglones reglamentarios a 22px de espaciado con líneas horizontales impresas.
5. **Escritura de Código Fuente (Recuadro en Blanco)**: Recuadro en blanco con altura equivalente a N renglones, **sin líneas horizontales impresas**, diseñado para que el estudiante escriba código con sangría clara y limpia.
6. **Identificación de Errores / Código**: Caja de código Python en `<pre class="python-code-box">` + pregunta de análisis + renglones de respuesta.
7. **Pregunta con 1 Imagen**:
   - Texto antes y después de la imagen.
   - Ajuste de tamaño porcentual (% de ancho de página) o en píxeles.
   - La imagen se almacena y se incrusta automáticamente en **Base64** dentro del HTML.
   - Renglones de respuesta opcionales.
8. **Pregunta con 2 Imágenes**:
   - Permite dos imágenes con texto antes, intermedio y después.
   - Disposición configurable: *Lado a lado (horizontal)* o *Una debajo de otra (vertical)*.
   - Tamaños porcentuales editables e incrustación en **Base64**.
9. **Asociación de Conceptos**: Tabla de dos columnas (Columna A - Vínculo `( )` - Columna B) con soporte para distractores.

### 5. Importación y Exportación Masiva (CSV / TXT / JSON)
- **Categorías y Subcategorías**:
  - Exportar a CSV con codificación `UTF-8 con BOM` (compatible nativamente con Microsoft Excel).
  - Importar desde archivos CSV o TXT delimitados por comas o punto y coma.
- **Banco de Preguntas**:
  - Exportar todas las preguntas del banco a CSV estructurado.
  - Importar preguntas desde CSV/TXT (crea automáticamente las categorías o subcategorías faltantes).
- **Exámenes Completos**:
  - Exportar un examen completo con su encabezado, tipografía, páginas asignadas e ítems a formato JSON.
  - Importar un examen desde archivo JSON para cargarlo de inmediato en pantalla.

### 6. Reset de la Aplicación y Datos de Ejemplo
- **⚠️ Resetear Aplicación (Dejar en Blanco)**:
  - Disponible desde el menú `Base de Datos -> Resetear Aplicación (Dejar en Blanco)`.
  - Vacía por completo las tablas de la base de datos SQLite para empezar desde cero sin registros de prueba.
- **📥 Cargar Datos de Ejemplo**:
  - Disponible desde el menú `Base de Datos -> Cargar Datos de Ejemplo`.
  - Recarga al instante el examen y las 16 preguntas reales del quiz de cátedra.
- **📁 Carpeta `ejemplos_importacion/`**:
  - Contiene archivos de muestra listos para usar o editar en Excel / Bloc de Notas:
    - `categorias_subcategorias_ejemplo.csv`
    - `preguntas_ejemplo.csv`
    - `indicaciones_ejemplo.csv`
    - `examen_ejemplo.json`

---

## 🏃‍♂️ Cómo Ejecutar la Aplicación

Abra una terminal en la carpeta del proyecto y ejecute:

```powershell
python main.py
```

o bien:

```powershell
python app.py
```

Para ejecutar las pruebas automatizadas:

```powershell
python test_app.py
```
