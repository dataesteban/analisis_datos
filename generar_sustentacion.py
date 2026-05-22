"""
generar_sustentacion.py
Genera sustentacion.docx en la misma carpeta.
Requiere: pip install python-docx
"""
from docx import Document
from docx.shared import Pt, RGBColor, Cm, Inches, Emu
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_ALIGN_VERTICAL, WD_TABLE_ALIGNMENT
from docx.oxml.ns import qn
from docx.oxml import OxmlElement
import os

# ── Colores ────────────────────────────────────────────────────
BLUE   = RGBColor(0x1E, 0x3A, 0x5F)
ACCENT = RGBColor(0x25, 0x63, 0xEB)
GREEN  = RGBColor(0x16, 0xA3, 0x4A)
RED    = RGBColor(0xDC, 0x26, 0x26)
AMBER  = RGBColor(0xD9, 0x77, 0x06)
GRAY   = RGBColor(0x6B, 0x72, 0x80)
WHITE  = RGBColor(0xFF, 0xFF, 0xFF)
LIGHT  = RGBColor(0xEF, 0xF6, 0xFF)
DARK   = RGBColor(0x0F, 0x17, 0x2A)


def rgb_hex(color: RGBColor) -> str:
    return f"{color[0]:02X}{color[1]:02X}{color[2]:02X}"


def set_cell_bg(cell, color: RGBColor):
    tc = cell._tc
    tcPr = tc.get_or_add_tcPr()
    shd = OxmlElement('w:shd')
    shd.set(qn('w:val'), 'clear')
    shd.set(qn('w:color'), 'auto')
    shd.set(qn('w:fill'), rgb_hex(color))
    tcPr.append(shd)


def set_cell_border(cell, top=True, bottom=True, left=True, right=True, color="CCCCCC"):
    tc = cell._tc
    tcPr = tc.get_or_add_tcPr()
    tcBorders = OxmlElement('w:tcBorders')
    for side, active in [('top', top), ('bottom', bottom), ('left', left), ('right', right)]:
        border = OxmlElement(f'w:{side}')
        if active:
            border.set(qn('w:val'), 'single')
            border.set(qn('w:sz'), '4')
            border.set(qn('w:color'), color)
        else:
            border.set(qn('w:val'), 'none')
        tcBorders.append(border)
    tcPr.append(tcBorders)


def set_col_width(table, col_idx, width_cm):
    for row in table.rows:
        row.cells[col_idx].width = Cm(width_cm)


def add_h1(doc, text):
    p = doc.add_paragraph(style='Heading 1')
    p.clear()
    run = p.add_run(text)
    run.bold = True
    run.font.size = Pt(20)
    run.font.color.rgb = BLUE
    run.font.name = 'Arial'
    p.paragraph_format.space_before = Pt(18)
    p.paragraph_format.space_after = Pt(8)
    return p


def add_h2(doc, text):
    p = doc.add_paragraph(style='Heading 2')
    p.clear()
    run = p.add_run(text)
    run.bold = True
    run.font.size = Pt(14)
    run.font.color.rgb = ACCENT
    run.font.name = 'Arial'
    p.paragraph_format.space_before = Pt(12)
    p.paragraph_format.space_after = Pt(4)
    return p


def add_h3(doc, text):
    p = doc.add_paragraph(style='Heading 3')
    p.clear()
    run = p.add_run(text)
    run.bold = True
    run.font.size = Pt(12)
    run.font.color.rgb = BLUE
    run.font.name = 'Arial'
    p.paragraph_format.space_before = Pt(8)
    p.paragraph_format.space_after = Pt(2)
    return p


def add_p(doc, text, bold=False, color=None, size=11):
    p = doc.add_paragraph()
    run = p.add_run(text)
    run.font.name = 'Arial'
    run.font.size = Pt(size)
    run.bold = bold
    if color:
        run.font.color.rgb = color
    p.paragraph_format.space_before = Pt(2)
    p.paragraph_format.space_after = Pt(2)
    return p


def add_bullet(doc, text):
    p = doc.add_paragraph(style='List Bullet')
    p.clear()
    run = p.add_run(text)
    run.font.name = 'Arial'
    run.font.size = Pt(11)
    p.paragraph_format.space_before = Pt(1)
    p.paragraph_format.space_after = Pt(1)
    return p


def add_callout(doc, label, text, color: RGBColor):
    table = doc.add_table(rows=1, cols=2)
    table.alignment = WD_TABLE_ALIGNMENT.LEFT
    # label cell
    c0 = table.rows[0].cells[0]
    c0.width = Cm(2.5)
    set_cell_bg(c0, color)
    set_cell_border(c0, color=rgb_hex(color))
    lp = c0.paragraphs[0]
    lr = lp.add_run(label)
    lr.bold = True
    lr.font.name = 'Arial'
    lr.font.size = Pt(10)
    lr.font.color.rgb = WHITE
    # text cell
    c1 = table.rows[0].cells[1]
    c1.width = Cm(14.5)
    set_cell_border(c1, color="CCCCCC")
    tp = c1.paragraphs[0]
    tr = tp.add_run(text)
    tr.font.name = 'Arial'
    tr.font.size = Pt(10)
    doc.add_paragraph()


def add_divider(doc):
    p = doc.add_paragraph()
    pPr = p._p.get_or_add_pPr()
    pBdr = OxmlElement('w:pBdr')
    bottom = OxmlElement('w:bottom')
    bottom.set(qn('w:val'), 'single')
    bottom.set(qn('w:sz'), '6')
    bottom.set(qn('w:color'), '2563EB')
    pBdr.append(bottom)
    pPr.append(pBdr)
    return p


def make_header_row(table, headers_widths, bg_color=BLUE):
    row = table.rows[0]
    for i, (text, width_cm) in enumerate(headers_widths):
        cell = row.cells[i]
        cell.width = Cm(width_cm)
        set_cell_bg(cell, bg_color)
        set_cell_border(cell, color=rgb_hex(bg_color))
        p = cell.paragraphs[0]
        run = p.add_run(text)
        run.bold = True
        run.font.name = 'Arial'
        run.font.size = Pt(10)
        run.font.color.rgb = WHITE
        cell.vertical_alignment = WD_ALIGN_VERTICAL.CENTER


def add_data_row(table, values_widths, shade=False):
    row = table.add_row()
    for i, (text, width_cm, right_align, bold) in enumerate(values_widths):
        cell = row.cells[i]
        cell.width = Cm(width_cm)
        if shade:
            set_cell_bg(cell, LIGHT)
        set_cell_border(cell, color="CCCCCC")
        p = cell.paragraphs[0]
        if right_align:
            p.alignment = WD_ALIGN_PARAGRAPH.RIGHT
        run = p.add_run(text)
        run.font.name = 'Arial'
        run.font.size = Pt(10)
        run.bold = bold
        cell.vertical_alignment = WD_ALIGN_VERTICAL.CENTER


# ── Documento ──────────────────────────────────────────────────
doc = Document()

# Márgenes
section = doc.sections[0]
section.page_width = Inches(8.5)
section.page_height = Inches(11)
section.left_margin = Inches(1)
section.right_margin = Inches(1)
section.top_margin = Inches(1)
section.bottom_margin = Inches(1)

# ── PORTADA ────────────────────────────────────────────────────
for _ in range(3):
    doc.add_paragraph()

title_p = doc.add_paragraph()
title_p.alignment = WD_ALIGN_PARAGRAPH.CENTER
r = title_p.add_run('ON DAXELTA')
r.bold = True
r.font.size = Pt(36)
r.font.color.rgb = BLUE
r.font.name = 'Arial'

sub_p = doc.add_paragraph()
sub_p.alignment = WD_ALIGN_PARAGRAPH.CENTER
r = sub_p.add_run('Prueba Técnica — Analista de Datos')
r.font.size = Pt(20)
r.font.color.rgb = ACCENT
r.font.name = 'Arial'

inf_p = doc.add_paragraph()
inf_p.alignment = WD_ALIGN_PARAGRAPH.CENTER
r = inf_p.add_run('Informe de sustentación')
r.font.size = Pt(14)
r.font.color.rgb = GRAY
r.font.name = 'Arial'

add_divider(doc)

autor_p = doc.add_paragraph()
autor_p.alignment = WD_ALIGN_PARAGRAPH.CENTER
r = autor_p.add_run('Weizman Fabian')
r.bold = True
r.font.size = Pt(16)
r.font.color.rgb = BLUE
r.font.name = 'Arial'

mail_p = doc.add_paragraph()
mail_p.alignment = WD_ALIGN_PARAGRAPH.CENTER
r = mail_p.add_run('weizmanfabian@gmail.com')
r.font.size = Pt(11)
r.font.color.rgb = GRAY
r.font.name = 'Arial'

date_p = doc.add_paragraph()
date_p.alignment = WD_ALIGN_PARAGRAPH.CENTER
r = date_p.add_run('Mayo 2026')
r.font.size = Pt(11)
r.font.color.rgb = GRAY
r.font.name = 'Arial'

doc.add_page_break()

# ══════════════════════════════════════════════════════════════
# 1. RESUMEN EJECUTIVO
# ══════════════════════════════════════════════════════════════
add_h1(doc, '1. Resumen ejecutivo')
add_p(doc, 'Se realizó un análisis completo del negocio de gas vehicular On Daxelta sobre una ventana de 7 días (24–30 jul 2017), cubriendo los 6 puntos requeridos por la prueba técnica. El trabajo incluyó limpieza de datos en Python, construcción de un modelo semántico en Power BI con más de 50 medidas DAX, y un dashboard interactivo de dos páginas.')

doc.add_paragraph()

tbl = doc.add_table(rows=1, cols=2)
make_header_row(tbl, [('Métrica', 9.5), ('Valor', 7.0)])
rows_data = [
    ('Valor venta total (semana)', '$8.186.473.842 COP', True),
    ('Galones totales', '5.439.692 gal', False),
    ('Transacciones limpias', '735.273', False),
    ('Clientes con compras identificadas', '99.753 (12,4% del maestro)', False),
    ('Estaciones activas', '279 de 407', False),
    ('Departamentos top 80% del valor', '7 de 19', True),
    ('Medidas DAX construidas', '53', False),
    ('Hallazgos de calidad de datos', '27 (5 críticos · 13 advertencias · 9 informativos)', False),
]
for i, (m, v, bold) in enumerate(rows_data):
    add_data_row(tbl, [(m, 9.5, False, False), (v, 7.0, False, bold)], shade=(i % 2 == 0))

doc.add_page_break()

# ══════════════════════════════════════════════════════════════
# 2. PROCESO Y HERRAMIENTAS
# ══════════════════════════════════════════════════════════════
add_h1(doc, '2. Proceso y herramientas utilizadas')
add_p(doc, 'El proyecto siguió un flujo en tres etapas: limpieza y preparación de datos, análisis analítico por punto, y visualización en Power BI.')

add_h2(doc, '2.1 Stack tecnológico')
tbl2 = doc.add_table(rows=1, cols=2)
make_header_row(tbl2, [('Capa', 6.0), ('Herramienta', 10.5)])
stack = [
    ('Preparación de datos', 'Python 3.12 — pandas, numpy, fastexcel, pyarrow'),
    ('Visualización', 'Power BI Desktop (formato PBIP) + DAX'),
    ('Documentación', 'Markdown + Mermaid'),
    ('Versionado', 'Git'),
]
for i, (c, h) in enumerate(stack):
    add_data_row(tbl2, [(c, 6.0, False, False), (h, 10.5, False, False)], shade=(i % 2 == 0))

add_h2(doc, '2.2 Script de limpieza: limpieza_ondaxelta.py')
add_p(doc, 'Se desarrolló un script de limpieza reproducible y documentado que procesa los 5 archivos fuente, genera los 4 CSVs limpios y un reporte de inconsistencias automático. Cada ejecución produce output/reporte_inconsistencias.txt con hallazgos clasificados por severidad.')
add_p(doc, 'Optimizaciones de rendimiento implementadas:')
add_bullet(doc, 'fastexcel (motor Rust) para lectura de Excel: 10–100× más rápido que openpyxl')
add_bullet(doc, 'Tipos de dato explícitos (dtype) al leer CSVs — evita inferencia fila a fila')
add_bullet(doc, 'Conversiones vectoriales con pandas en lugar de iteraciones')
add_bullet(doc, 'Int64 nullable para columna Edad: evita conflicto de locale colombiano (45.0 → 450 en Power BI)')

add_h2(doc, '2.3 Flujo de trabajo')
add_p(doc, 'Fuentes originales (xlsx / CSV) → limpieza_ondaxelta.py → output/*.csv → Power BI (modelo semántico + DAX) → Dashboard interactivo')

doc.add_page_break()

# ══════════════════════════════════════════════════════════════
# 3. LIMPIEZA Y CALIDAD DE DATOS
# ══════════════════════════════════════════════════════════════
add_h1(doc, '3. Limpieza y calidad de datos')
add_p(doc, 'Se detectaron y documentaron 27 hallazgos distribuidos en 5 archivos. La filosofía de limpieza fue conservar antes que eliminar: solo se eliminan registros técnicamente inválidos. Todo lo demás se marca con banderas de calidad para filtrado selectivo en Power BI.')

add_h2(doc, '3.1 Hallazgos por severidad')
tbl3 = doc.add_table(rows=1, cols=3)
make_header_row(tbl3, [('Severidad', 4.0), ('Cantidad', 3.0), ('Descripción', 9.5)])
sev = [
    ('CRITICO', '5', 'Bloquean o distorsionan el análisis', RED),
    ('ADVERTENCIA', '13', 'Requieren compensación o documentación', AMBER),
    ('INFO', '9', 'Trazabilidad y contexto', ACCENT),
]
for i, (s, c, d, _) in enumerate(sev):
    add_data_row(tbl3, [(s, 4.0, False, True), (c, 3.0, True, False), (d, 9.5, False, False)], shade=(i % 2 == 0))

add_h2(doc, '3.2 Problemas críticos y sus correcciones')

add_h3(doc, 'Header desplazado en Trans_2_Sem')
add_p(doc, 'El archivo Trans_2_Sem tenía el header con columnas en orden incorrecto respecto al contenido real, afectando 369.498 filas (49,9% del universo transaccional). Se reasignaron las columnas correctas en el script: Placa | IdCliente | IdEstacion | ValorVenta | Gal_Fid | Gal | FechaVenta.')

add_h3(doc, 'FechaNacimiento no confiable (40,2% de clientes)')
add_p(doc, 'Fechas nulas, futuras, menores de 16 años o mayores de 100. Se creó la columna FechaNac_confiable como bandera bool para filtrar en DAX sin eliminar registros. Las medidas de edad en Power BI se calculan directamente desde FechaNacimiento con filtro de rango [16–100] para independizarse del CSV.')

add_h3(doc, 'Duplicados en Clientes (1.421 registros)')
add_p(doc, 'Se detectaron 1.421 registros con IdCliente duplicado. Se deduplicó manteniendo la primera aparición, tanto en el script Python (drop_duplicates) como en Power Query (Table.Distinct).')

add_h3(doc, 'Cardinalidad y referencia cíclica en el modelo Power BI')
add_p(doc, 'Una relación con filtro bidireccional (bothDirections) creaba un ciclo. Se desactivó el filtro cruzado. Una relación con cardinalidad uno-a-muchos mal configurada en Estaciones generaba error de duplicado en IdCiudad — corregido en el TMDL.')

add_h2(doc, '3.3 Banderas de calidad generadas')
tbl4 = doc.add_table(rows=1, cols=3)
make_header_row(tbl4, [('Bandera', 5.5), ('Tabla', 3.5), ('Significado', 7.5)])
flags = [
    ('FechaNac_confiable', 'Clientes', 'Edad entre 16–100 años y fecha no nula'),
    ('cliente_identificado', 'Trans', 'IdCliente ≠ -99999'),
    ('EsInternacional', 'Geo', 'IdCiudad < 0 (México, Chile, Perú, Venezuela)'),
    ('outlier_valor', 'Trans', 'ValorVenta > percentil 99 ($34.392)'),
    ('outlier_gal', 'Trans', 'Gal > percentil 99 (22,06 gal)'),
]
for i, (f, t, s) in enumerate(flags):
    add_data_row(tbl4, [(f, 5.5, False, True), (t, 3.5, False, False), (s, 7.5, False, False)], shade=(i % 2 == 0))

doc.add_page_break()

# ══════════════════════════════════════════════════════════════
# 4. ANÁLISIS POR PUNTO
# ══════════════════════════════════════════════════════════════
add_h1(doc, '4. Análisis por punto de la prueba')

# Punto 1
add_h2(doc, 'Punto 1 — Volumetría del galonaje por día de la semana')
add_callout(doc, 'HALLAZGO', 'Pico viernes–sábado (30,7% del galonaje). Valle domingo (12,1%). Brecha pico/valle: +27%.', GREEN)

tbl5 = doc.add_table(rows=1, cols=6)
make_header_row(tbl5, [('Día', 3.0), ('Galones', 2.5), ('%Gal', 1.8), ('Valor venta', 3.0), ('Tickets', 2.2), ('Gal/Tx', 2.0)])
vol = [
    ('Lunes',          '764.346',  '14,1%', '$1.152M',  '101.977', '7,50', False),
    ('Martes',         '771.806',  '14,2%', '$1.164M',  '103.706', '7,44', False),
    ('Miércoles',      '783.785',  '14,4%', '$1.182M',  '104.494', '7,50', False),
    ('Jueves',         '792.352',  '14,6%', '$1.195M',  '106.647', '7,43', False),
    ('Viernes (pico)', '835.545',  '15,4%', '$1.258M',  '111.469', '7,50', True),
    ('Sábado',         '833.818',  '15,3%', '$1.249M',  '113.606', '7,34', False),
    ('Domingo (valle)','658.040',  '12,1%', '$984M',    '93.374',  '7,05', True),
]
for i, row in enumerate(vol):
    add_data_row(tbl5, [
        (row[0], 3.0, False, row[6]),
        (row[1], 2.5, True, row[6]),
        (row[2], 1.8, True, row[6]),
        (row[3], 3.0, True, row[6]),
        (row[4], 2.2, True, False),
        (row[5], 2.0, True, False),
    ], shade=(i % 2 == 0))

add_p(doc, 'Los días hábiles crecen monótonamente de lunes a viernes. El ticket promedio es estable ($10.543–$11.312), lo que indica que la volumetría la mueve la cantidad de transacciones, no el tamaño unitario.')

# Punto 2
add_h2(doc, 'Punto 2 — Pronóstico valor venta martes y miércoles')
add_callout(doc, 'MÉTODO', 'Naive estacional con banda de incertidumbre basada en CV (coeficiente de variación) inter-día. Con solo 7 días históricos no hay suficiente datos para ARIMA, Prophet ni Holt-Winters.', ACCENT)

tbl6 = doc.add_table(rows=1, cols=4)
make_header_row(tbl6, [('Día', 4.5), ('Pronóstico', 4.0), ('Mínimo (-CV)', 3.75), ('Máximo (+CV)', 3.75)])
add_data_row(tbl6, [
    ('Martes 2017-08-01',    4.5, False, True),
    ('$1.164.495.517',       4.0, True, True),
    ('$1.071.062.777',       3.75, True, False),
    ('$1.257.928.257',       3.75, True, False),
])
add_data_row(tbl6, [
    ('Miércoles 2017-08-02', 4.5, False, True),
    ('$1.182.080.425',       4.0, True, True),
    ('$1.087.258.792',       3.75, True, False),
    ('$1.276.901.059',       3.75, True, False),
], shade=True)
add_p(doc, 'CV inter-día: 8,03%. La banda de incertidumbre refleja la variabilidad real de la semana analizada. Limitación documentada: con 7 días no es posible capturar estacionalidad mensual ni efectos de temporada.')

# Punto 3
add_h2(doc, 'Punto 3 — Comportamiento por regional')
add_callout(doc, 'HALLAZGO', '7 departamentos concentran el 80% del valor total. Solo 2 (Valle del Cauca + Bogotá) suman el 50%.', GREEN)

tbl7 = doc.add_table(rows=1, cols=5)
make_header_row(tbl7, [('#', 0.7), ('Departamento', 5.0), ('Valor venta', 4.0), ('%Valor', 2.3), ('%Acumulado', 2.5)])
regional = [
    ('1', 'Valle del Cauca', '$1.985M', '24,3%', '24,3%', True),
    ('2', 'Bogotá D.C.',     '$1.143M', '14,0%', '38,3%', False),
    ('3', 'Atlántico',       '$745M',   '9,1%',  '47,4%', False),
    ('4', 'Córdoba',         '$620M',   '7,6%',  '54,9%', False),
    ('5', 'Cesar',           '$603M',   '7,4%',  '62,3%', False),
    ('6', 'Boyacá',          '$569M',   '7,0%',  '69,3%', False),
    ('7', 'Nariño',          '$438M',   '5,4%',  '74,6%', False),
]
for i, row in enumerate(regional):
    add_data_row(tbl7, [
        (row[0], 0.7, True, False),
        (row[1], 5.0, False, row[5]),
        (row[2], 4.0, True, False),
        (row[3], 2.3, True, False),
        (row[4], 2.5, True, False),
    ], shade=(i % 2 == 0))

# Punto 4
add_h2(doc, 'Punto 4 — Comportamiento por estación')
add_callout(doc, 'HALLAZGO', '166 estaciones concentran el 80% del valor (Pareto). 31,5% del maestro no operó en la semana. 51,4% de las Propias GNV estuvieron inactivas.', AMBER)

tbl8 = doc.add_table(rows=1, cols=5)
make_header_row(tbl8, [('Tipo', 5.0), ('Total maestro', 2.5), ('Activas', 2.5), ('%Activas', 2.5), ('%Valor', 2.0)])
estaciones = [
    ('Franquiciada GNV', '251', '192', '76,5%', '43%', False),
    ('Propia GNV',       '107', '52',  '48,6%', '38%', True),
    ('Operadora',        '45',  '35',  '77,8%', '19%', False),
]
for i, row in enumerate(estaciones):
    add_data_row(tbl8, [
        (row[0], 5.0, False, False),
        (row[1], 2.5, True, False),
        (row[2], 2.5, True, row[5]),
        (row[3], 2.5, True, row[5]),
        (row[4], 2.0, True, False),
    ], shade=(i % 2 == 0))
add_p(doc, 'Índice de fidelización por estación (% transacciones con cliente identificado): mejor estación 94%, peor 35%, promedio 81,3%.')

# Punto 5
add_h2(doc, 'Punto 5 — Segmentación de clientes (RFM)')
add_callout(doc, 'MÉTODO', 'RFM (Recencia·Frecuencia·Monetario). Recencia con scoring manual por día (solo 7 valores únicos — qcut no aplica). F y M con quintiles balanceados sobre 99.753 clientes activos.', ACCENT)

tbl9 = doc.add_table(rows=1, cols=6)
make_header_row(tbl9, [('Segmento', 3.5), ('Clientes', 2.0), ('%Cli', 1.8), ('%Valor', 1.8), ('Valor prom', 2.5), ('%Flotas', 2.9)])
rfm = [
    ('Champions',           '31.916', '31,9%', '58,2%', '$124.176', '12,0%', True),
    ('Leales',              '16.425', '16,4%', '16,0%', '$66.425',  '3,9%',  False),
    ('Nuevos',              '16.620', '16,6%', '7,4%',  '$30.453',  '0,0%',  False),
    ('Hibernando',          '15.467', '15,5%', '4,9%',  '$21.771',  '0,0%',  False),
    ('No puedo perderlos',  '226',    '0,2%',  '0,4%',  '$107.519', '27,9%', True),
    ('En riesgo',           '6.820',  '6,8%',  '5,9%',  '$59.240',  '8,1%',  False),
    ('Frecuentes bajo val.','8.279',  '8,3%',  '6,3%',  '$52.167',  '2,3%',  False),
]
for i, row in enumerate(rfm):
    add_data_row(tbl9, [
        (row[0], 3.5, False, row[6]),
        (row[1], 2.0, True, False),
        (row[2], 1.8, True, False),
        (row[3], 1.8, True, row[6]),
        (row[4], 2.5, True, False),
        (row[5], 2.9, True, row[6]),
    ], shade=(i % 2 == 0))
add_p(doc, 'Champions (31,9% de clientes) concentra el 58,2% del valor. Los "No puedo perderlos" tienen la mayor proporción de flotas (27,9%) — son flotas de alto valor que no compraron recientemente.')

# Punto 6
add_h2(doc, 'Punto 6 — Clientes de mayor valor')
add_callout(doc, 'HALLAZGO', 'Top 1% genera el 13,4% del valor. Pareto inverso: el 80% del valor lo genera el 51,2% de los clientes — base más distribuida de lo habitual.', GREEN)

tbl10 = doc.add_table(rows=1, cols=4)
make_header_row(tbl10, [('Segmento', 5.0), ('Valor acumulado', 4.0), ('%Valor', 3.0), ('%Flotas', 2.5)])
top = [
    ('Top 1% (998 clientes)',  '$1.100M', '13,4%', '63%', True),
    ('Top 10% (9.975 cli)',    '$4.500M', '55,0%', '29%', False),
    ('Top 20% (19.951 cli)',   '$5.800M', '70,9%', '18%', False),
    ('Top 50% (49.877 cli)',   '$7.500M', '91,7%', '8%',  False),
]
for i, row in enumerate(top):
    add_data_row(tbl10, [
        (row[0], 5.0, False, row[4]),
        (row[1], 4.0, True, False),
        (row[2], 3.0, True, row[4]),
        (row[3], 2.5, True, row[4]),
    ], shade=(i % 2 == 0))
add_p(doc, 'El top 1% tiene en promedio 8,6 placas por cliente. El 63% son flotas empresariales. La frecuencia promedio del top 10% es 3,9× la del resto.')

doc.add_page_break()

# ══════════════════════════════════════════════════════════════
# 5. MODELO SEMÁNTICO Y DAX
# ══════════════════════════════════════════════════════════════
add_h1(doc, '5. Modelo semántico Power BI')
add_p(doc, 'El proyecto usa formato PBIP (Power BI Project), que almacena el modelo semántico en archivos TMDL versionables con Git. Se construyeron 53 medidas DAX organizadas en 8 carpetas de visualización.')

add_h2(doc, '5.1 Tablas del modelo')
tbl11 = doc.add_table(rows=1, cols=3)
make_header_row(tbl11, [('Tabla', 4.5), ('Filas', 3.0), ('Origen', 9.0)])
tablas = [
    ('Clientes',   '799.916',   'customers_clean.csv'),
    ('Trans',      '735.273',   'trans_clean.csv'),
    ('Estaciones', '407',       'estaciones_clean.csv'),
    ('Geo',        '1.126',     'geo_clean.csv'),
    ('Calendario', '7',         'Tabla DAX generada'),
    ('Forecast',   '2',         'Tabla DAX (mar/mié)'),
    ('_Medidas',   '1 marcador','Tabla contenedora de 53 medidas'),
]
for i, row in enumerate(tablas):
    add_data_row(tbl11, [(row[0], 4.5, False, True), (row[1], 3.0, True, False), (row[2], 9.0, False, False)], shade=(i % 2 == 0))

add_h2(doc, '5.2 Medidas DAX destacadas')
tbl12 = doc.add_table(rows=1, cols=2)
make_header_row(tbl12, [('Medida', 5.0), ('Lógica', 11.5)])
medidas = [
    ('Segmento RFM', 'SWITCH con 10 reglas sobre R/F/M Score (columnas calculadas en tabla Clientes)'),
    ('Edad Promedio', 'AVERAGEX + FILTER: rango [16–100], calculado desde FechaNacimiento, no desde CSV'),
    ('Brecha Pico Valle', 'MAXX/MINX sobre todos los días para calcular variación %'),
    ('Pct Acumulado Cliente', 'RANKX + DIVIDE para curva de Pareto de clientes por valor'),
    ('Forecast Valor', 'Naive estacional: replica el valor del mismo día de la semana anterior'),
    ('Pct Fidelización Est.', 'DIVIDE(tx con cliente identificado, total tx) por estación'),
]
for i, row in enumerate(medidas):
    add_data_row(tbl12, [(row[0], 5.0, False, True), (row[1], 11.5, False, False)], shade=(i % 2 == 0))

add_h2(doc, '5.3 Errores corregidos en el modelo')
tbl13 = doc.add_table(rows=1, cols=3)
make_header_row(tbl13, [('Error', 5.0), ('Causa', 5.5), ('Fix', 6.0)])
errores = [
    ('Edad corrupta (x10)',         'dataType: string + locale es-CO lee 45.0 → 450',     'Int64 nullable en CSV + dataType: double en TMDL'),
    ('Referencia cíclica en Geo',   'Relación bothDirections + cardinalidad invertida',    'Removido crossFilteringBehavior, marcada inactiva'),
    ('Duplicado IdCiudad',          'fromCardinality: one en relación inactiva',           'Removida propiedad de cardinalidad'),
    ('Duplicado IdCliente',         'Script no deduplicaba customers',                     'Table.Distinct en PQ + drop_duplicates en Python'),
]
for i, row in enumerate(errores):
    add_data_row(tbl13, [(row[0], 5.0, False, True), (row[1], 5.5, False, False), (row[2], 6.0, False, False)], shade=(i % 2 == 0))

doc.add_page_break()

# ══════════════════════════════════════════════════════════════
# 6. DASHBOARD
# ══════════════════════════════════════════════════════════════
add_h1(doc, '6. Dashboard Power BI')
add_p(doc, 'El archivo VisualP.pbip contiene un dashboard de dos páginas. Todas las medidas DAX respetan los filtros del usuario en tiempo real.')

add_h2(doc, 'Página 1 — Dashboard General')
add_bullet(doc, '6 tarjetas KPI: Valor Venta, Total Galones, Total Tickets, Clientes Únicos, % Fidelización, Ticket Promedio')
add_bullet(doc, 'Gráfico combo: tendencia diaria de galones (barras) y valor (línea)')
add_bullet(doc, '2 gráficos de dona: distribución por Tipo de Estación y por Segmento RFM')
add_bullet(doc, 'Gráfico de barras horizontal: top departamentos por valor venta')
add_bullet(doc, 'Tabla resumen: Segmento RFM × Valor Promedio × Frecuencia × Recencia')

add_h2(doc, 'Página 2 — Demografía — Edades')
add_bullet(doc, '3 KPIs: Edad Promedio, % FechaNac Confiable, Clientes Con Edad Válida')
add_bullet(doc, 'Barras: Edad Promedio por Segmento RFM')
add_bullet(doc, 'Barras: Edad Promedio por tipo de cliente (Flota vs Particular)')
add_bullet(doc, 'Dona: distribución de confiabilidad de datos demográficos')
add_bullet(doc, 'Tabla: Segmento RFM × métricas de edad')

doc.add_page_break()

# ══════════════════════════════════════════════════════════════
# 7. RECOMENDACIONES
# ══════════════════════════════════════════════════════════════
add_h1(doc, '7. Recomendaciones de estandarización')
add_p(doc, 'Se generaron 12 recomendaciones priorizadas agrupadas por origen del problema.')

add_h2(doc, 'Recomendaciones críticas (implementar inmediatamente)')
add_callout(doc, 'R1', 'Corregir el header de Trans_2_Sem en el sistema fuente. Orden correcto: Placa | IdCliente | IdEstacion | ValorVenta | Gal_Fid | Gal | FechaVenta.', RED)
add_callout(doc, 'R2', 'Validación en captura para FechaNacimiento: rechazar fechas futuras y edades < 16. Alerta soft para edades > 100. El 40,2% de las fechas actuales no son confiables.', RED)
add_callout(doc, 'R3', 'Eliminar la fila basura con IdEstacion = 0 de la fuente. Agregar constraint en BD: IdEstacion > 0.', RED)

add_h2(doc, 'Recomendaciones de estandarización (semanas 3–6)')
add_bullet(doc, 'Eliminar "Sin Segmento" como categoría. Dominio cerrado propuesto: {SUSTENTO, RECORRIDO, NEGOCIO}.')
add_bullet(doc, 'Estandarizar TipoEstacion: dominio cerrado con 3 valores, sin variantes con espacios o typos.')
add_bullet(doc, 'Cambiar encoding de CSV a UTF-8 y separador estándar (coma o punto y coma). Los separadores § y £ requieren scripts especializados.')
add_bullet(doc, 'Crear diccionario de datos formal: nombre, tipo, dominio, nullable, descripción, ejemplo por columna.')
add_bullet(doc, 'Estandarizar IdCliente como entero: actualmente tiene -99999 mezclado con IDs reales.')

add_h2(doc, 'KPIs de gobierno de datos propuestos')
tbl14 = doc.add_table(rows=1, cols=3)
make_header_row(tbl14, [('KPI', 7.5), ('Valor actual', 3.75), ('Meta', 3.75)])
kpis = [
    ('% Tx con IdCliente identificado',    '81,3%', '≥ 95%'),
    ('% FechaNacimiento confiable',        '59,8%', '≥ 90%'),
    ('% Clientes con segmento clasificado','79,3%', '100%'),
    ('% Estaciones activas / maestro',     '68,5%', '≥ 90%'),
    ('% Integridad referencial Trans→Est', '100% ✓', '100%'),
]
for i, row in enumerate(kpis):
    add_data_row(tbl14, [(row[0], 7.5, False, False), (row[1], 3.75, True, False), (row[2], 3.75, True, True)], shade=(i % 2 == 0))

# ── Cierre ─────────────────────────────────────────────────────
doc.add_paragraph()
add_divider(doc)
close_p = doc.add_paragraph()
close_p.alignment = WD_ALIGN_PARAGRAPH.CENTER
r = close_p.add_run('Weizman Fabian — Prueba Técnica Analista de Datos — On Daxelta — Mayo 2026')
r.font.name = 'Arial'
r.font.size = Pt(9)
r.font.color.rgb = GRAY

# ── Guardar ────────────────────────────────────────────────────
out = os.path.join(os.path.dirname(__file__), 'sustentacion.docx')
doc.save(out)
print(f"OK  sustentacion.docx generado en: {out}")
