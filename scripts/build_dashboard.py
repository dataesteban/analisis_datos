# -*- coding: utf-8 -*-
"""
Genera el dashboard general en el reporte PBIP (enhanced format).

Crea visuals.json individuales en:
  VisualP.Report/definition/pages/<PAGE_ID>/visuals/<visual_id>/visual.json

Visuals generados:
  - 6 KPI cards (fila superior)
  - 1 Combo chart: Valor Venta (barras) + Total Galones (linea) por Dia
  - 2 Donuts: Segmento RFM | Tipo Estacion
  - 1 Bar horizontal: Top Departamentos
  - 1 Table: Top Estaciones con KPIs
  - 1 Donut: Flotas vs Particulares
  - 1 Slicer: Tipo Estacion

Uso:  python scripts/build_dashboard.py
"""

import json
import shutil
import uuid
from pathlib import Path

ROOT      = Path(__file__).resolve().parent.parent
RP_DIR    = ROOT / "VisualP.Report"
PAGES_DIR = RP_DIR / "definition" / "pages"
PAGE_ID   = "23477c05129b8050a2b4"
PAGE_DIR  = PAGES_DIR / PAGE_ID
VIS_DIR   = PAGE_DIR / "visuals"

# ---------- paleta dark theme ----------
BG_PAGE   = "#0F172A"   # fondo canvas
BG_PANEL  = "#1E293B"   # cards y charts
BG_HEADER = "#0D1B2A"   # header
GOLD      = "#F59E0B"
BLUE      = "#38BDF8"
GREEN     = "#34D399"
PINK      = "#F472B6"
PURPLE    = "#A78BFA"
WHITE     = "#F1F5F9"
GRAY      = "#64748B"

# ---------- canvas ----------
CW, CH = 1280, 720

VISUAL_SCHEMA = (
    "https://developer.microsoft.com/json-schemas/fabric/item/report/"
    "definition/visualContainer/1.5.0/schema.json"
)


# ═══════════════════════════════════════════════════════════════
#  Helpers de construccion
# ═══════════════════════════════════════════════════════════════

def uid() -> str:
    return uuid.uuid4().hex[:20]


def position(x: int, y: int, w: int, h: int, z: int = 1000, tab: int = 1000) -> dict:
    return {"x": x, "y": y, "z": z, "width": w, "height": h, "tabOrder": tab}


def measure_proj(name: str, table: str = "_Medidas") -> dict:
    return {
        "field": {
            "Measure": {
                "Expression": {"SourceRef": {"Entity": table}},
                "Property": name,
            }
        },
        "queryRef": f"{table}.{name}",
        "nativeQueryRef": name,
    }


def column_proj(name: str, table: str) -> dict:
    return {
        "field": {
            "Column": {
                "Expression": {"SourceRef": {"Entity": table}},
                "Property": name,
            }
        },
        "queryRef": f"{table}.{name}",
        "nativeQueryRef": name,
    }


def bg_obj(color: str) -> dict:
    """Objeto de fondo oscuro para un visual."""
    return {
        "background": [{"properties": {
            "show": {"expr": {"Literal": {"Value": "true"}}},
            "color": {"solid": {"color": color}},
            "transparency": {"expr": {"Literal": {"Value": "0D"}}},
        }}],
        "border": [{"properties": {
            "show": {"expr": {"Literal": {"Value": "false"}}},
        }}],
        "dropShadow": [{"properties": {
            "show": {"expr": {"Literal": {"Value": "false"}}},
        }}],
    }


def save(vid: str, data: dict) -> None:
    d = VIS_DIR / vid
    d.mkdir(parents=True, exist_ok=True)
    with open(d / "visual.json", "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
        f.write("\n")


# ═══════════════════════════════════════════════════════════════
#  Constructores de visuales
# ═══════════════════════════════════════════════════════════════

def make_card(x, y, w, h, measure: str, table: str = "_Medidas", tab: int = 1000) -> dict:
    vid = uid()
    v = {
        "$schema": VISUAL_SCHEMA,
        "name": vid,
        "position": position(x, y, w, h, tab=tab),
        "visual": {
            "visualType": "card",
            "query": {
                "queryState": {
                    "Values": {"projections": [measure_proj(measure, table)]},
                }
            },
            "objects": {
                **bg_obj(BG_PANEL),
                "labels": [{"properties": {
                    "color": {"solid": {"color": WHITE}},
                    "fontSize": {"expr": {"Literal": {"Value": "18D"}}},
                    "fontFamily": {"expr": {"Literal": {"Value": "'Segoe UI', wf_standard-font, helvetica, arial, sans-serif"}}},
                    "bold": {"expr": {"Literal": {"Value": "true"}}},
                }}],
                "categoryLabels": [{"properties": {
                    "show": {"expr": {"Literal": {"Value": "true"}}},
                    "color": {"solid": {"color": GRAY}},
                    "fontSize": {"expr": {"Literal": {"Value": "10D"}}},
                }}],
            },
        },
    }
    save(vid, v)
    return vid


def make_combo(x, y, w, h,
               axis_col: str, axis_table: str,
               col_measure: str, line_measure: str,
               tab: int = 2000) -> str:
    vid = uid()
    v = {
        "$schema": VISUAL_SCHEMA,
        "name": vid,
        "position": position(x, y, w, h, tab=tab),
        "visual": {
            "visualType": "lineClusteredColumnComboChart",
            "query": {
                "queryState": {
                    "Category": {"projections": [column_proj(axis_col, axis_table)]},
                    "Y":        {"projections": [measure_proj(col_measure)]},
                    "Y2":       {"projections": [measure_proj(line_measure)]},
                }
            },
            "objects": {
                **bg_obj(BG_PANEL),
                "valueAxis": [{"properties": {
                    "labelColor": {"solid": {"color": GRAY}},
                }}],
                "categoryAxis": [{"properties": {
                    "labelColor": {"solid": {"color": GRAY}},
                }}],
                "legend": [{"properties": {
                    "show": {"expr": {"Literal": {"Value": "true"}}},
                    "labelColor": {"solid": {"color": WHITE}},
                }}],
                "title": [{"properties": {
                    "show": {"expr": {"Literal": {"Value": "true"}}},
                    "titleText": {"expr": {"Literal": {"Value": f"'Ventas diarias — {col_measure} vs {line_measure}'"}}},
                    "fontColor": {"solid": {"color": WHITE}},
                    "fontSize": {"expr": {"Literal": {"Value": "11D"}}},
                }}],
            },
        },
    }
    save(vid, v)
    return vid


def make_donut(x, y, w, h,
               cat_col: str, cat_table: str,
               value_measure: str, title_txt: str,
               tab: int = 3000) -> str:
    vid = uid()
    v = {
        "$schema": VISUAL_SCHEMA,
        "name": vid,
        "position": position(x, y, w, h, tab=tab),
        "visual": {
            "visualType": "donutChart",
            "query": {
                "queryState": {
                    "Category": {"projections": [column_proj(cat_col, cat_table)]},
                    "Y":        {"projections": [measure_proj(value_measure)]},
                }
            },
            "objects": {
                **bg_obj(BG_PANEL),
                "legend": [{"properties": {
                    "show": {"expr": {"Literal": {"Value": "true"}}},
                    "labelColor": {"solid": {"color": WHITE}},
                    "fontSize": {"expr": {"Literal": {"Value": "9D"}}},
                }}],
                "dataLabels": [{"properties": {
                    "show": {"expr": {"Literal": {"Value": "true"}}},
                    "color": {"solid": {"color": WHITE}},
                    "fontSize": {"expr": {"Literal": {"Value": "9D"}}},
                }}],
                "title": [{"properties": {
                    "show": {"expr": {"Literal": {"Value": "true"}}},
                    "titleText": {"expr": {"Literal": {"Value": f"'{title_txt}'"}}},
                    "fontColor": {"solid": {"color": WHITE}},
                    "fontSize": {"expr": {"Literal": {"Value": "11D"}}},
                }}],
            },
        },
    }
    save(vid, v)
    return vid


def make_bar_h(x, y, w, h,
               cat_col: str, cat_table: str,
               value_measure: str, title_txt: str,
               tab: int = 4000) -> str:
    vid = uid()
    v = {
        "$schema": VISUAL_SCHEMA,
        "name": vid,
        "position": position(x, y, w, h, tab=tab),
        "visual": {
            "visualType": "barChart",
            "query": {
                "queryState": {
                    "Category": {"projections": [column_proj(cat_col, cat_table)]},
                    "Y":        {"projections": [measure_proj(value_measure)]},
                }
            },
            "objects": {
                **bg_obj(BG_PANEL),
                "categoryAxis": [{"properties": {
                    "labelColor": {"solid": {"color": GRAY}},
                    "fontSize": {"expr": {"Literal": {"Value": "9D"}}},
                }}],
                "valueAxis": [{"properties": {
                    "labelColor": {"solid": {"color": GRAY}},
                }}],
                "dataLabels": [{"properties": {
                    "show": {"expr": {"Literal": {"Value": "true"}}},
                    "color": {"solid": {"color": WHITE}},
                    "fontSize": {"expr": {"Literal": {"Value": "9D"}}},
                }}],
                "title": [{"properties": {
                    "show": {"expr": {"Literal": {"Value": "true"}}},
                    "titleText": {"expr": {"Literal": {"Value": f"'{title_txt}'"}}},
                    "fontColor": {"solid": {"color": WHITE}},
                    "fontSize": {"expr": {"Literal": {"Value": "11D"}}},
                }}],
            },
        },
    }
    save(vid, v)
    return vid


def make_table(x, y, w, h,
               columns: list,   # [(name, table, is_measure), ...]
               tab: int = 5000) -> str:
    """Tabla con columnas y medidas mixtas."""
    projs = []
    for name, table, is_measure in columns:
        projs.append(measure_proj(name, table) if is_measure else column_proj(name, table))

    vid = uid()
    v = {
        "$schema": VISUAL_SCHEMA,
        "name": vid,
        "position": position(x, y, w, h, tab=tab),
        "visual": {
            "visualType": "tableEx",
            "query": {
                "queryState": {
                    "Values": {"projections": projs},
                }
            },
            "objects": {
                **bg_obj(BG_PANEL),
                "grid": [{"properties": {
                    "gridVertical": {"expr": {"Literal": {"Value": "false"}}},
                    "gridHorizontalColor": {"solid": {"color": "#334155"}},
                    "rowPadding": {"expr": {"Literal": {"Value": "3D"}}},
                    "outlineColor": {"solid": {"color": "#334155"}},
                }}],
                "columnHeaders": [{"properties": {
                    "fontColor": {"solid": {"color": WHITE}},
                    "backColor": {"solid": {"color": BG_HEADER}},
                    "fontSize": {"expr": {"Literal": {"Value": "10D"}}},
                    "bold": {"expr": {"Literal": {"Value": "true"}}},
                }}],
                "values": [{"properties": {
                    "fontColorPrimary": {"solid": {"color": WHITE}},
                    "backColorPrimary": {"solid": {"color": BG_PANEL}},
                    "fontColorSecondary": {"solid": {"color": WHITE}},
                    "backColorSecondary": {"solid": {"color": "#263347"}},
                    "fontSize": {"expr": {"Literal": {"Value": "10D"}}},
                }}],
            },
        },
    }
    save(vid, v)
    return vid


def make_slicer(x, y, w, h,
                col: str, table: str,
                tab: int = 500) -> str:
    vid = uid()
    v = {
        "$schema": VISUAL_SCHEMA,
        "name": vid,
        "position": position(x, y, w, h, tab=tab),
        "visual": {
            "visualType": "slicer",
            "query": {
                "queryState": {
                    "Field": {"projections": [column_proj(col, table)]},
                }
            },
            "objects": {
                **bg_obj(BG_PANEL),
                "data": [{"properties": {
                    "mode": {"expr": {"Literal": {"Value": "'Basic'"}}},
                }}],
                "items": [{"properties": {
                    "fontColor": {"solid": {"color": WHITE}},
                    "background": {"solid": {"color": BG_PANEL}},
                    "fontSize": {"expr": {"Literal": {"Value": "10D"}}},
                }}],
                "header": [{"properties": {
                    "show": {"expr": {"Literal": {"Value": "true"}}},
                    "fontColor": {"solid": {"color": GRAY}},
                    "background": {"solid": {"color": BG_HEADER}},
                    "fontSize": {"expr": {"Literal": {"Value": "10D"}}},
                }}],
            },
        },
    }
    save(vid, v)
    return vid


def make_textbox(x, y, w, h, text: str,
                 font_size: int = 14, color: str = WHITE,
                 bold: bool = True, tab: int = 100) -> str:
    vid = uid()
    v = {
        "$schema": VISUAL_SCHEMA,
        "name": vid,
        "position": position(x, y, w, h, tab=tab),
        "visual": {
            "visualType": "textbox",
            "visualContainerObjects": {
                "background": [{"properties": {
                    "show": {"expr": {"Literal": {"Value": "false"}}},
                }}],
                "border": [{"properties": {
                    "show": {"expr": {"Literal": {"Value": "false"}}},
                }}],
            },
            "paragraphs": [{
                "textRuns": [{
                    "value": text,
                    "textRunStyle": {
                        "fontSize": f"{font_size}pt",
                        "fontWeight": "bold" if bold else "normal",
                        "color": color,
                        "fontFamily": "Segoe UI",
                    },
                }],
                "paragraphStyle": {"textAlignment": "Left"},
            }],
        },
    }
    save(vid, v)
    return vid


# ═══════════════════════════════════════════════════════════════
#  Layout principal
# ═══════════════════════════════════════════════════════════════

def build_page_background(page_data: dict) -> dict:
    """Aplica fondo oscuro al canvas de la pagina."""
    page_data["displayName"] = "Dashboard General"
    page_data["objects"] = {
        "background": [{"properties": {
            "color": {"solid": {"color": BG_PAGE}},
            "transparency": {"expr": {"Literal": {"Value": "0D"}}},
        }}],
        "outspace": [{"properties": {
            "color": {"solid": {"color": BG_PAGE}},
            "transparency": {"expr": {"Literal": {"Value": "0D"}}},
        }}],
    }
    return page_data


def main():
    # Limpiar visuals anteriores (borrar archivos y subdirs sin borrar el dir raiz)
    if VIS_DIR.exists():
        for child in VIS_DIR.iterdir():
            if child.is_dir():
                shutil.rmtree(child)
            else:
                child.unlink()
    VIS_DIR.mkdir(parents=True, exist_ok=True)

    created = []

    # ──────────────────────────────────────────────
    #  Titulo (textbox)
    #  y=10 h=45
    # ──────────────────────────────────────────────
    created.append(make_textbox(20, 12, 720, 42,
                                "Análisis de Ventas — Combustible On Daxelta",
                                font_size=16, color=WHITE, bold=True, tab=100))

    # Subtitulo con contexto de datos
    created.append(make_textbox(20, 42, 720, 22,
                                "Ventana: 24–30 Jul 2017  |  7 días de operación",
                                font_size=9, color=GRAY, bold=False, tab=101))

    # ──────────────────────────────────────────────
    #  Slicer: Tipo Estacion  (esquina superior derecha)
    #  x=900 y=10 w=360 h=55
    # ──────────────────────────────────────────────
    created.append(make_slicer(900, 10, 365, 55,
                               "TipoEstacion", "Estaciones", tab=500))

    # ──────────────────────────────────────────────
    #  KPI cards — fila 1
    #  y=72  h=88  6 cards × 200px + 5 gaps × 13px = 1265 → ajustar
    # ──────────────────────────────────────────────
    KPI_Y   = 72
    KPI_H   = 90
    KPI_W   = 196
    KPI_GAP = 16
    KPI_X0  = (CW - (6 * KPI_W + 5 * KPI_GAP)) // 2   # centrado

    kpis = [
        ("Valor Venta",        "_Medidas"),
        ("Total Galones",      "_Medidas"),
        ("Total Tickets",      "_Medidas"),
        ("Clientes Unicos",    "_Medidas"),
        ("Estaciones Activas", "_Medidas"),
        ("Ticket Promedio",    "_Medidas"),
    ]
    for i, (measure, table) in enumerate(kpis):
        cx = KPI_X0 + i * (KPI_W + KPI_GAP)
        created.append(make_card(cx, KPI_Y, KPI_W, KPI_H, measure, table, tab=1000 + i))

    # ──────────────────────────────────────────────
    #  Fila 2 — zona principal  y=170 h=335
    #  [Combo chart 640] [gap 10] [Donut RFM 290] [gap 10] [Donut TipoEst 290]
    # ──────────────────────────────────────────────
    MAIN_Y  = 170
    MAIN_H  = 335
    COMBO_W = 640
    DONUT_W = 290
    GAP     = 10
    COL3_X  = 10 + COMBO_W + GAP + DONUT_W + GAP

    # Combo: Valor Venta (barras) + Total Galones (linea) por dia
    created.append(make_combo(10, MAIN_Y, COMBO_W, MAIN_H,
                              "NombreDia", "Calendario",
                              "Valor Venta", "Total Galones",
                              tab=2000))

    # Donut: distribución Segmento RFM
    created.append(make_donut(10 + COMBO_W + GAP, MAIN_Y,
                              DONUT_W, (MAIN_H // 2) - GAP,
                              "Segmento RFM", "Clientes",
                              "Pct Clientes Segmento",
                              "Segmento RFM", tab=3000))

    # Donut: distribución Tipo Estacion
    created.append(make_donut(10 + COMBO_W + GAP,
                              MAIN_Y + (MAIN_H // 2) + GAP,
                              DONUT_W, (MAIN_H // 2) - GAP,
                              "TipoEstacion", "Estaciones",
                              "Valor Venta",
                              "Valor por Tipo Estación", tab=3001))

    # Bar horizontal: Top Departamentos por Valor Venta
    created.append(make_bar_h(COL3_X, MAIN_Y, DONUT_W, MAIN_H,
                              "NombreDpto", "Geo",
                              "Valor Venta",
                              "Top Departamentos", tab=4000))

    # ──────────────────────────────────────────────
    #  Fila 3 — bottom  y=515 h=195
    #  [Table top estaciones 640] [Donut EsFlota 290] [Bar % fidelizacion 290]
    # ──────────────────────────────────────────────
    BOT_Y = MAIN_Y + MAIN_H + GAP
    BOT_H = CH - BOT_Y - 10

    table_cols = [
        ("NombreDpto",        "Geo",       False),
        ("TipoEstacion",      "Estaciones", False),
        ("Valor Venta",       "_Medidas",   True),
        ("Total Galones",     "_Medidas",   True),
        ("Pct Fidelizacion",  "_Medidas",   True),
        ("Ranking Estacion",  "_Medidas",   True),
    ]
    created.append(make_table(10, BOT_Y, COMBO_W, BOT_H, table_cols, tab=5000))

    # Donut: Flotas vs Particulares
    created.append(make_donut(10 + COMBO_W + GAP, BOT_Y,
                              DONUT_W, BOT_H,
                              "EsFlota", "Clientes",
                              "Valor Venta",
                              "Flotas vs Particulares", tab=3002))

    # Bar horizontal: % Fidelizacion por tipo estacion
    created.append(make_bar_h(COL3_X, BOT_Y, DONUT_W, BOT_H,
                              "TipoEstacion", "Estaciones",
                              "Pct Fidelizacion",
                              "Fidelización por Tipo", tab=4001))

    # ──────────────────────────────────────────────
    #  Actualizar page.json
    # ──────────────────────────────────────────────
    page_path = PAGE_DIR / "page.json"
    with open(page_path, encoding="utf-8") as f:
        page = json.load(f)

    page = build_page_background(page)

    with open(page_path, "w", encoding="utf-8") as f:
        json.dump(page, f, indent=2, ensure_ascii=False)
        f.write("\n")

    print('Dashboard generado: ' + str(len(created)) + ' visuales')
    print('  Pagina: ' + str(PAGE_DIR))
    print('  Visuals: ' + str(VIS_DIR))
    for v in created:
        print('  - ' + v)


if __name__ == "__main__":
    main()
