# -*- coding: utf-8 -*-
"""
Genera el proyecto Power BI (formato PBIP) con el modelo semantico On Daxelta.

Produce:
  VisualP.pbip                         archivo de proyecto
  VisualP.SemanticModel/               modelo de datos (tablas, relaciones, DAX)
  VisualP.Report/                      reporte (pagina en blanco reutilizada del .pbix)

Las 7 tablas se importan via Power Query (M): los 4 CSV de output/ y las tablas
Calendario / Forecast / _Medidas generadas con M. Sobre ese modelo se crean las
5 relaciones, las 10 columnas calculadas RFM de Clientes y las 50 medidas DAX
de los hallazgos F1-F6.

Las tablas de soporte se generan como tablas de importacion (no tablas DAX
calculadas) para que sus columnas tengan IDs validos y puedan participar en
relaciones sin errores de carga.

Uso:  python scripts/build_modelo_pbip.py
"""

import json
import shutil
import uuid
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUTPUT = ROOT / "output"
PBIX_ORIGINAL = ROOT / "VisualP.pbix"
SM_DIR = ROOT / "VisualP.SemanticModel"
RP_DIR = ROOT / "VisualP.Report"

COMPATIBILITY_LEVEL = 1567

# Mapa de tipos: clave interna -> tipo Power Query (M)
M_TYPE = {
    "string": "type text",
    "int64": "Int64.Type",
    "double": "type number",
    "dateTime": "type datetime",
    "boolean": "type logical",
}

# Columnas cuyos valores nulos se reemplazan por 0 al importar.
# Edad: si el cliente no tiene fecha de nacimiento confiable, queda en 0
# (marcador explicito de "sin edad", no en blanco).
FILL_ZERO = {"Clientes": ["Edad"]}


# --------------------------------------------------------------------------
# Tablas de origen (CSV):  (nombre, tipo, oculta)
# --------------------------------------------------------------------------
TRANS_COLS = [
    ("Placa", "string", False),
    ("IdCliente", "int64", True),
    ("IdEstacion", "int64", True),
    ("ValorVenta", "double", False),
    ("Gal_Fid", "double", False),
    ("Gal", "double", False),
    ("FechaVenta", "dateTime", True),
    ("_fuente", "string", False),
    ("cliente_identificado", "boolean", False),
    ("outlier_valor", "boolean", False),
    ("outlier_gal", "boolean", False),
    ("DiaSemana", "string", True),
    ("NumeroDia", "int64", True),
    ("Semana", "int64", True),
    ("Mes", "int64", True),
    ("Anio", "int64", True),
    ("DiaSemana_ES", "string", True),
    ("PrecioXGalon", "double", False),
]

CLIENTES_COLS = [
    ("IdCliente", "int64", True),
    ("Segmento", "string", False),
    ("IdCiudad", "int64", True),
    ("FechaNacimiento", "dateTime", False),
    ("FechaNac_confiable", "boolean", False),
    ("Edad", "double", False),
]

ESTACIONES_COLS = [
    ("IdEstacion", "int64", True),
    ("IdCiudad", "int64", True),
    ("TipoEstacion", "string", False),
]

GEO_COLS = [
    ("NombreDpto", "string", False),
    ("IdCiudad", "int64", True),
    ("NombreCiudad", "string", False),
    ("EsInternacional", "boolean", False),
]

CSV_TABLES = [
    ("Trans", "trans_clean.csv", TRANS_COLS),
    ("Clientes", "customers_clean.csv", CLIENTES_COLS),
    ("Estaciones", "estaciones_clean.csv", ESTACIONES_COLS),
    ("Geo", "geo_clean.csv", GEO_COLS),
]


# --------------------------------------------------------------------------
# Columnas calculadas de la tabla Clientes (RFM)
# (nombre, expresion DAX, oculta)
# --------------------------------------------------------------------------
CLIENTES_CALC_COLS = [
    ("Frecuencia",
     'CALCULATE(COUNTROWS(Trans), Trans[cliente_identificado]=TRUE())', False),
    ("Monetario",
     'CALCULATE(SUM(Trans[ValorVenta]), Trans[cliente_identificado]=TRUE())', False),
    ("Recencia",
     'VAR Ultima = CALCULATE(MAX(Trans[FechaVenta]), Trans[cliente_identificado]=TRUE()) '
     'VAR FechaRef = MAXX(ALL(Trans), Trans[FechaVenta]) '
     'RETURN IF(ISBLANK(Ultima), BLANK(), DATEDIFF(Ultima, FechaRef, DAY))', False),
    ("NumPlacas",
     'CALCULATE(DISTINCTCOUNT(Trans[Placa]), Trans[cliente_identificado]=TRUE())', False),
    ("R Score",
     'SWITCH(TRUE(), '
     'ISBLANK(Clientes[Recencia]), BLANK(), '
     'Clientes[Recencia]=0, 5, '
     'Clientes[Recencia]=1, 4, '
     'Clientes[Recencia]=2, 3, '
     'Clientes[Recencia]<=4, 2, '
     '1)', False),
    ("F Score",
     'IF(Clientes[Frecuencia]>0, '
     'VAR Activos = FILTER(ALL(Clientes), Clientes[Frecuencia]>0) '
     'VAR Total = COUNTROWS(Activos) '
     'VAR Pos = RANKX(Activos, Clientes[Frecuencia], , ASC) '
     'RETURN SWITCH(TRUE(), '
     'Pos<=Total*0.2, 1, Pos<=Total*0.4, 2, Pos<=Total*0.6, 3, Pos<=Total*0.8, 4, 5))', False),
    ("M Score",
     'IF(Clientes[Monetario]>0, '
     'VAR Activos = FILTER(ALL(Clientes), Clientes[Monetario]>0) '
     'VAR Total = COUNTROWS(Activos) '
     'VAR Pos = RANKX(Activos, Clientes[Monetario], , ASC) '
     'RETURN SWITCH(TRUE(), '
     'Pos<=Total*0.2, 1, Pos<=Total*0.4, 2, Pos<=Total*0.6, 3, Pos<=Total*0.8, 4, 5))', False),
    ("RFM Score",
     'Clientes[R Score] + Clientes[F Score] + Clientes[M Score]', True),
    ("Segmento RFM",
     'VAR R = Clientes[R Score] VAR F = Clientes[F Score] VAR M = Clientes[M Score] '
     'RETURN SWITCH(TRUE(), '
     'ISBLANK(R) || ISBLANK(F) || ISBLANK(M), "Sin actividad", '
     'R>=4 && F>=4 && M>=4, "Champions", '
     'R>=4 && F>=3 && M>=3, "Leales", '
     'R>=4 && F<=2, "Nuevos", '
     'R>=3 && F>=3 && M<=2, "Frecuentes bajo valor", '
     'R<=2 && F>=4 && M>=4, "No puedo perderlos", '
     'R<=2 && F>=3, "En riesgo", '
     'R<=2 && F<=2 && M>=4, "Grandes durmiendo", '
     'R<=2 && F<=2, "Hibernando", '
     'R+F+M>=9, "Potencial leal", '
     '"Necesitan atencion")', False),
    ("EsFlota",
     'IF(Clientes[NumPlacas]>=4, "Flota", "Particular")', False),
]


# --------------------------------------------------------------------------
# Medidas: (nombre, expresion DAX, formato, carpeta)
# --------------------------------------------------------------------------
MEASURES = [
    # 01 Base
    ("Total Galones", 'SUM(Trans[Gal])', "#,##0", "01 Base"),
    ("Valor Venta", 'SUM(Trans[ValorVenta])', "$#,##0", "01 Base"),
    ("Total Tickets", 'COUNTROWS(Trans)', "#,##0", "01 Base"),
    ("Clientes Unicos", 'DISTINCTCOUNT(Trans[IdCliente])', "#,##0", "01 Base"),
    ("Total Clientes", 'DISTINCTCOUNT(Clientes[IdCliente])', "#,##0", "01 Base"),
    ("Ticket Promedio", 'DIVIDE([Valor Venta], [Total Tickets])', "$#,##0", "01 Base"),
    ("Gal por Tx", 'DIVIDE([Total Galones], [Total Tickets])', "#,##0.00", "01 Base"),
    ("Estaciones Activas", 'DISTINCTCOUNT(Trans[IdEstacion])', "#,##0", "01 Base"),
    ("Valor por Estacion", 'DIVIDE([Valor Venta], [Estaciones Activas])', "$#,##0", "01 Base"),

    # 02 Volumetria dia
    ("Pct Galones Dia",
     'DIVIDE([Total Galones], CALCULATE([Total Galones], ALL(Calendario[NombreDia])))',
     "0.0%", "02 Volumetria dia"),
    ("Pct Valor Dia",
     'DIVIDE([Valor Venta], CALCULATE([Valor Venta], ALL(Calendario[NombreDia])))',
     "0.0%", "02 Volumetria dia"),
    ("Ranking Dia Gal",
     'RANKX(ALL(Calendario[NombreDia]), [Total Galones], , DESC, DENSE)',
     "0", "02 Volumetria dia"),
    ("Brecha Pico Valle Gal",
     'VAR Maximo = MAXX(ALL(Calendario[NombreDia]), [Total Galones]) '
     'VAR Minimo = MINX(ALL(Calendario[NombreDia]), [Total Galones]) '
     'RETURN DIVIDE(Maximo - Minimo, Minimo)',
     "0.0%", "02 Volumetria dia"),

    # 03 Forecast
    ("Valor Promedio Diario",
     'AVERAGEX(VALUES(Calendario[Fecha]), [Valor Venta])', "$#,##0", "03 Forecast"),
    ("CV Valor",
     'DIVIDE(STDEVX.S(VALUES(Calendario[Fecha]), [Valor Venta]), [Valor Promedio Diario])',
     "0.0%", "03 Forecast"),
    ("Forecast Valor",
     'VAR FechaActual = SELECTEDVALUE(Forecast[Fecha]) '
     'VAR FechaReferencia = FechaActual - 7 '
     'RETURN CALCULATE([Valor Venta], Calendario[Fecha] = FechaReferencia)',
     "$#,##0", "03 Forecast"),
    ("Forecast Valor Min", '[Forecast Valor] * (1 - [CV Valor])', "$#,##0", "03 Forecast"),
    ("Forecast Valor Max", '[Forecast Valor] * (1 + [CV Valor])', "$#,##0", "03 Forecast"),
    ("Gal Promedio Diario",
     'AVERAGEX(VALUES(Calendario[Fecha]), [Total Galones])', "#,##0", "03 Forecast"),
    ("CV Galones",
     'DIVIDE(STDEVX.S(VALUES(Calendario[Fecha]), [Total Galones]), [Gal Promedio Diario])',
     "0.0%", "03 Forecast"),
    ("Forecast Galones",
     'VAR FechaActual = SELECTEDVALUE(Forecast[Fecha]) '
     'VAR FechaReferencia = FechaActual - 7 '
     'RETURN CALCULATE([Total Galones], Calendario[Fecha] = FechaReferencia)',
     "#,##0", "03 Forecast"),
    ("Forecast Galones Min", '[Forecast Galones] * (1 - [CV Galones])', "#,##0", "03 Forecast"),
    ("Forecast Galones Max", '[Forecast Galones] * (1 + [CV Galones])', "#,##0", "03 Forecast"),

    # 04 Regional
    ("Pct Valor Dpto",
     'DIVIDE([Valor Venta], CALCULATE([Valor Venta], ALL(Geo[NombreDpto])))',
     "0.0%", "04 Regional"),
    ("Ranking Dpto",
     'RANKX(ALL(Geo[NombreDpto]), [Valor Venta], , DESC, DENSE)', "0", "04 Regional"),
    ("Pct Acumulado Dpto",
     'VAR ValorActual = [Valor Venta] '
     'VAR Tabla = ADDCOLUMNS(ALL(Geo[NombreDpto]), "@Val", [Valor Venta]) '
     'RETURN DIVIDE(SUMX(FILTER(Tabla, [@Val] >= ValorActual), [@Val]), SUMX(Tabla, [@Val]))',
     "0.0%", "04 Regional"),
    ("Es Top 7 Dpto",
     'IF([Ranking Dpto] <= 7, "Top 7 (80%)", "Resto")', None, "04 Regional"),

    # 05 Estaciones
    ("Tx Identificadas",
     'CALCULATE([Total Tickets], Trans[cliente_identificado]=TRUE())', "#,##0", "05 Estaciones"),
    ("Pct Fidelizacion",
     'DIVIDE([Tx Identificadas], [Total Tickets])', "0.0%", "05 Estaciones"),
    ("Pct Valor Estacion",
     'DIVIDE([Valor Venta], CALCULATE([Valor Venta], ALL(Estaciones[IdEstacion])))',
     "0.0%", "05 Estaciones"),
    ("Ranking Estacion",
     'RANKX(ALL(Estaciones[IdEstacion]), [Valor Venta], , DESC, DENSE)', "0", "05 Estaciones"),
    ("Pct Acumulado Estacion",
     'VAR ValorActual = [Valor Venta] '
     'VAR Tabla = ADDCOLUMNS(ALL(Estaciones[IdEstacion]), "@Val", [Valor Venta]) '
     'RETURN DIVIDE(SUMX(FILTER(Tabla, [@Val] >= ValorActual), [@Val]), SUMX(Tabla, [@Val]))',
     "0.0%", "05 Estaciones"),
    ("Es Top Pareto",
     'IF([Pct Acumulado Estacion] <= 0.8, "Top 80%", "Cola 20%")', None, "05 Estaciones"),
    ("Estaciones Maestro", 'COUNTROWS(Estaciones)', "#,##0", "05 Estaciones"),
    ("Estaciones Inactivas",
     '[Estaciones Maestro] - [Estaciones Activas]', "#,##0", "05 Estaciones"),
    ("Pct Cobertura",
     'DIVIDE([Estaciones Activas], [Estaciones Maestro])', "0.0%", "05 Estaciones"),
    ("Valor por Estacion Global",
     'CALCULATE([Valor por Estacion], ALL(Estaciones[TipoEstacion]))', "$#,##0", "05 Estaciones"),
    ("Indice vs Global",
     'DIVIDE([Valor por Estacion], [Valor por Estacion Global])', "0.00", "05 Estaciones"),

    # 06 RFM
    ("Pct Clientes Segmento",
     'DIVIDE([Total Clientes], CALCULATE([Total Clientes], ALL(Clientes[Segmento RFM])))',
     "0.0%", "06 RFM"),
    ("Pct Valor Segmento",
     'DIVIDE([Valor Venta], CALCULATE([Valor Venta], ALL(Clientes[Segmento RFM])))',
     "0.0%", "06 RFM"),
    ("Valor Promedio Cliente",
     'DIVIDE([Valor Venta], [Total Clientes])', "$#,##0", "06 RFM"),

    # 07 Top clientes
    ("Ranking Cliente",
     'RANKX(ALL(Clientes[IdCliente]), [Valor Venta], , DESC, DENSE)', "0", "07 Top clientes"),
    ("Pct Cliente Acumulado",
     'DIVIDE([Ranking Cliente], CALCULATE(DISTINCTCOUNT(Clientes[IdCliente]), ALL(Clientes)))',
     "0.0%", "07 Top clientes"),
    ("Es Top 1 Pct",
     'IF([Pct Cliente Acumulado] <= 0.01, "Top 1%", '
     'IF([Pct Cliente Acumulado] <= 0.1, "Top 10%", '
     'IF([Pct Cliente Acumulado] <= 0.2, "Top 20%", "Resto")))',
     None, "07 Top clientes"),
    ("Pct Valor Acumulado Cliente",
     'VAR ValorActual = [Valor Venta] '
     'VAR Tabla = ADDCOLUMNS(ALL(Clientes[IdCliente]), "@Val", [Valor Venta]) '
     'RETURN DIVIDE(SUMX(FILTER(Tabla, [@Val] >= ValorActual), [@Val]), SUMX(Tabla, [@Val]))',
     "0.0%", "07 Top clientes"),
    ("Frecuencia Promedio",
     'AVERAGEX(VALUES(Clientes[IdCliente]), [Total Tickets])', "#,##0.0", "07 Top clientes"),
    ("Pct Flotas en Tramo",
     'DIVIDE(CALCULATE(DISTINCTCOUNT(Clientes[IdCliente]), Clientes[EsFlota]="Flota"), '
     'DISTINCTCOUNT(Clientes[IdCliente]))',
     "0.0%", "07 Top clientes"),
    ("Valor No Atribuible",
     'CALCULATE(SUM(Trans[ValorVenta]), Trans[cliente_identificado]=FALSE())',
     "$#,##0", "07 Top clientes"),
    ("Pct No Atribuible",
     'DIVIDE([Valor No Atribuible], SUM(Trans[ValorVenta]))', "0.0%", "07 Top clientes"),
    ("Oportunidad Captura 50pct",
     '[Valor No Atribuible] * 0.5', "$#,##0", "07 Top clientes"),
]


# --------------------------------------------------------------------------
# Tablas de soporte generadas con Power Query (M)
# --------------------------------------------------------------------------
CALENDARIO_M = """let
    Inicio = #date(2017, 7, 24),
    Fin = #date(2017, 7, 30),
    Dias = List.Dates(Inicio, Duration.Days(Fin - Inicio) + 1, #duration(1, 0, 0, 0)),
    Origen = Table.FromList(Dias, Splitter.SplitByNothing(), {"Fecha"}),
    ConFecha = Table.TransformColumnTypes(Origen, {{"Fecha", type datetime}}),
    ConAnio = Table.AddColumn(ConFecha, "Anio", each Date.Year([Fecha]), Int64.Type),
    ConMes = Table.AddColumn(ConAnio, "Mes", each Date.Month([Fecha]), Int64.Type),
    ConNombreMes = Table.AddColumn(ConMes, "NombreMes", each Date.MonthName([Fecha]), type text),
    ConDia = Table.AddColumn(ConNombreMes, "Dia", each Date.Day([Fecha]), Int64.Type),
    ConNumeroDia = Table.AddColumn(ConDia, "NumeroDia", each Date.DayOfWeek([Fecha], Day.Monday), Int64.Type),
    ConOrdenDia = Table.AddColumn(ConNumeroDia, "OrdenDia", each [NumeroDia] + 1, Int64.Type),
    ConNombreDia = Table.AddColumn(ConOrdenDia, "NombreDia", each {"Lunes", "Martes", "Miercoles", "Jueves", "Viernes", "Sabado", "Domingo"}{[NumeroDia]}, type text),
    ConSemana = Table.AddColumn(ConNombreDia, "Semana", each Date.WeekOfYear([Fecha], Day.Monday), Int64.Type)
in
    ConSemana"""

FORECAST_M = """let
    Origen = Table.FromRows(
        {{#datetime(2017, 8, 1, 0, 0, 0), "Martes"}, {#datetime(2017, 8, 2, 0, 0, 0), "Miercoles"}},
        {"Fecha", "DiaSemana"}),
    Tipada = Table.TransformColumnTypes(Origen, {{"Fecha", type datetime}, {"DiaSemana", type text}})
in
    Tipada"""

MEDIDAS_M = """let
    Origen = Table.FromRows({{""}}, {"Marcador"}),
    Tipada = Table.TransformColumnTypes(Origen, {{"Marcador", type text}})
in
    Tipada"""

CALENDARIO_COLS = [
    ("Fecha", "dateTime", False, None),
    ("Anio", "int64", False, None),
    ("Mes", "int64", False, None),
    ("NombreMes", "string", False, None),
    ("Dia", "int64", False, None),
    ("NumeroDia", "int64", False, None),
    ("OrdenDia", "int64", False, None),
    ("NombreDia", "string", False, "OrdenDia"),
    ("Semana", "int64", False, None),
]

FORECAST_COLS = [
    ("Fecha", "dateTime", False, None),
    ("DiaSemana", "string", False, None),
]

MEDIDAS_COLS = [
    ("Marcador", "string", True, None),
]


# --------------------------------------------------------------------------
# Constructores
# --------------------------------------------------------------------------
def build_csv_m(csv_name, cols, fill_zero=None):
    """Expresion Power Query (M) para importar un CSV.

    fill_zero: columnas cuyos valores nulos se reemplazan por 0 (los faltantes
    quedan como 0 explicito, no en blanco).
    """
    path = str(OUTPUT / csv_name)
    transforms = ", ".join(
        '{"%s", %s}' % (name, M_TYPE[kind]) for name, kind, _ in cols
    )
    pasos = [
        "let",
        '    Origen = Csv.Document(File.Contents("%s"), '
        '[Delimiter=",", Encoding=65001, QuoteStyle=QuoteStyle.Csv]),' % path,
        "    Encabezados = Table.PromoteHeaders(Origen, [PromoteAllScalars=true]),",
    ]
    if fill_zero:
        columnas = "{%s}" % ", ".join('"%s"' % c for c in fill_zero)
        pasos += [
            "    Tipos = Table.TransformColumnTypes(Encabezados, {%s})," % transforms,
            "    SinNulos = Table.ReplaceValue(Tipos, null, 0, "
            "Replacer.ReplaceValue, %s)" % columnas,
            "in",
            "    SinNulos",
        ]
    else:
        pasos += [
            "    Tipos = Table.TransformColumnTypes(Encabezados, {%s})" % transforms,
            "in",
            "    Tipos",
        ]
    return "\n".join(pasos)


def data_column(name, kind, hidden=False, sort_by=None):
    col = {
        "name": name,
        "dataType": kind,
        "sourceColumn": name,
        "summarizeBy": "none",
    }
    if hidden:
        col["isHidden"] = True
    if sort_by:
        col["sortByColumn"] = sort_by
    return col


def calculated_column(name, expression, hidden=False):
    col = {
        "type": "calculated",
        "name": name,
        "expression": expression,
        "summarizeBy": "none",
    }
    if hidden:
        col["isHidden"] = True
    return col


def import_table(name, m_expression, columns, hidden=False):
    table = {
        "name": name,
        "columns": columns,
        "partitions": [{
            "name": name,
            "mode": "import",
            "source": {"type": "m", "expression": m_expression},
        }],
    }
    if hidden:
        table["isHidden"] = True
    return table


def measure(name, expression, fmt, folder):
    m = {"name": name, "expression": expression, "displayFolder": folder}
    if fmt:
        m["formatString"] = fmt
    return m


def relationship(from_table, from_col, to_table, to_col, active=True):
    rel = {
        "name": str(uuid.uuid4()),
        "fromTable": from_table,
        "fromColumn": from_col,
        "toTable": to_table,
        "toColumn": to_col,
        "crossFilteringBehavior": "oneDirection",
    }
    if not active:
        rel["isActive"] = False
    return rel


def build_model_bim():
    tables = []

    # Tablas de origen (CSV). Clientes recibe ademas las columnas calculadas RFM.
    for table_name, csv_name, cols in CSV_TABLES:
        columns = [data_column(n, k, h) for n, k, h in cols]
        if table_name == "Clientes":
            columns += [calculated_column(n, e, h) for n, e, h in CLIENTES_CALC_COLS]
        m_expr = build_csv_m(csv_name, cols, FILL_ZERO.get(table_name))
        tables.append(import_table(table_name, m_expr, columns))

    # Tablas de soporte (M).
    tables.append(import_table(
        "Calendario", CALENDARIO_M,
        [data_column(n, k, h, s) for n, k, h, s in CALENDARIO_COLS],
    ))
    tables.append(import_table(
        "Forecast", FORECAST_M,
        [data_column(n, k, h, s) for n, k, h, s in FORECAST_COLS],
    ))

    medidas = import_table(
        "_Medidas", MEDIDAS_M,
        [data_column(n, k, h, s) for n, k, h, s in MEDIDAS_COLS],
        hidden=True,
    )
    medidas["measures"] = [measure(n, e, f, d) for n, e, f, d in MEASURES]
    tables.append(medidas)

    relationships = [
        relationship("Trans", "IdEstacion", "Estaciones", "IdEstacion"),
        relationship("Trans", "IdCliente", "Clientes", "IdCliente"),
        relationship("Trans", "FechaVenta", "Calendario", "Fecha"),
        relationship("Estaciones", "IdCiudad", "Geo", "IdCiudad"),
        relationship("Clientes", "IdCiudad", "Geo", "IdCiudad", active=False),
    ]

    return {
        "name": "VisualP",
        "compatibilityLevel": COMPATIBILITY_LEVEL,
        "model": {
            "culture": "es-ES",
            "dataAccessOptions": {
                "legacyRedirects": True,
                "returnErrorValuesAsNull": True,
            },
            "defaultPowerBIDataSourceVersion": "powerBI_V3",
            "sourceQueryCulture": "es-ES",
            "tables": tables,
            "relationships": relationships,
        },
    }


def write_json(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(data, fh, indent=2, ensure_ascii=True)
        fh.write("\n")


def write_text(path, text):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(text)


def extract_report_from_pbix():
    """Reutiliza la pagina en blanco y el tema del VisualP.pbix original."""
    with zipfile.ZipFile(PBIX_ORIGINAL) as zf:
        layout_bytes = zf.read("Report/Layout")
        theme_bytes = zf.read(
            "Report/StaticResources/SharedResources/BaseThemes/CY26SU05.json"
        )

    write_text(RP_DIR / "report.json", layout_bytes.decode("utf-16"))

    try:
        theme_text = theme_bytes.decode("utf-8-sig")
    except UnicodeDecodeError:
        theme_text = theme_bytes.decode("utf-16")
    write_text(
        RP_DIR / "StaticResources" / "SharedResources" / "BaseThemes" / "CY26SU05.json",
        theme_text,
    )


def platform_file(item_type):
    return {
        "$schema": "https://developer.microsoft.com/json-schemas/fabric/"
                   "gitIntegration/platformProperties/2.0.0/schema.json",
        "metadata": {"type": item_type, "displayName": "VisualP"},
        "config": {"version": "2.0", "logicalId": str(uuid.uuid4())},
    }


def main():
    if not PBIX_ORIGINAL.exists():
        raise SystemExit("No se encontro VisualP.pbix en %s" % ROOT)

    for csv_name in (n for _, n, _ in CSV_TABLES):
        if not (OUTPUT / csv_name).exists():
            raise SystemExit("Falta el CSV: output/%s" % csv_name)

    for folder in (SM_DIR, RP_DIR):
        if folder.exists():
            shutil.rmtree(folder)

    # --- Modelo semantico ---
    write_json(SM_DIR / "model.bim", build_model_bim())
    write_json(SM_DIR / "definition.pbism", {"version": "4.2", "settings": {}})
    write_json(SM_DIR / ".platform", platform_file("SemanticModel"))

    # --- Reporte ---
    extract_report_from_pbix()
    write_json(RP_DIR / "definition.pbir", {
        "version": "1.0",
        "datasetReference": {"byPath": {"path": "../VisualP.SemanticModel"}},
    })
    write_json(RP_DIR / ".platform", platform_file("Report"))

    # --- Archivo de proyecto ---
    write_json(ROOT / "VisualP.pbip", {
        "version": "1.0",
        "artifacts": [{"report": {"path": "VisualP.Report"}}],
        "settings": {"enableAutoRecovery": True},
    })

    n_cols = sum(len(c) for _, _, c in CSV_TABLES) + len(CLIENTES_CALC_COLS)
    print("Proyecto PBIP generado:")
    print("  VisualP.pbip / VisualP.SemanticModel / VisualP.Report")
    print("Resumen del modelo:")
    print("  Tablas         : 7 (todas de importacion)")
    print("  Columnas       : %d origen/calculadas" % n_cols)
    print("  Columnas RFM   : %d (Clientes)" % len(CLIENTES_CALC_COLS))
    print("  Relaciones     : 5 (4 activas + 1 inactiva)")
    print("  Medidas        : %d" % len(MEASURES))


if __name__ == "__main__":
    main()
