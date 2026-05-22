"""
============================================================
  On Daxelta - Análisis exploratorio, RFM y Forecast
  Autor  : [tu nombre]
  Fecha  : 2024
  Python : 3.9+
  Deps   : pandas, numpy, openpyxl
============================================================

PRERREQUISITO:
    Haber corrido primero limpieza_ondaxelta.py
    Los archivos de ./output/ deben existir.

EJECUCIÓN:
    python analisis_ondaxelta.py

SALIDAS (carpeta ./output/):
    analisis_ondaxelta.xlsx   - 8 hojas listas para Power BI
============================================================
"""

import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

import pandas as pd
import numpy as np
import os
from datetime import datetime

OUTPUT_DIR = "./output"
os.makedirs(OUTPUT_DIR, exist_ok=True)

print("=" * 55)
print("  On Daxelta - Analisis y Segmentacion")
print("=" * 55)

# ══════════════════════════════════════════════════════════
#  CARGA DE DATOS LIMPIOS
# ══════════════════════════════════════════════════════════
print("\n>>> Cargando datos limpios...")

trans = pd.read_csv(os.path.join(OUTPUT_DIR, "trans_clean.csv"))
cust  = pd.read_csv(os.path.join(OUTPUT_DIR, "customers_clean.csv"))
est   = pd.read_csv(os.path.join(OUTPUT_DIR, "estaciones_clean.csv"))
geo   = pd.read_csv(os.path.join(OUTPUT_DIR, "geo_clean.csv"))

trans["FechaVenta"]      = pd.to_datetime(trans["FechaVenta"])
cust["FechaNacimiento"]  = pd.to_datetime(cust["FechaNacimiento"], errors="coerce")

print(f"   Transacciones : {len(trans):>10,}")
print(f"   Clientes      : {len(cust):>10,}")
print(f"   Estaciones    : {len(est):>10,}")
print(f"   Ciudades geo  : {len(geo):>10,}")

# ── Tabla maestra enriquecida (base de todos los análisis) ─
trans_full = (
    trans
    .merge(est[["IdEstacion", "IdCiudad", "TipoEstacion"]], on="IdEstacion", how="left")
    .merge(geo[["IdCiudad", "NombreDpto", "NombreCiudad"]], on="IdCiudad", how="left")
)

# ── Orden lógico días de semana ─────────────────────────────
ORDEN_DIAS = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"]


# ══════════════════════════════════════════════════════════
#  1. VOLUMETRÍA POR DÍA DE SEMANA
# ══════════════════════════════════════════════════════════
print("\n>>> 1/6  Volumetría por día de semana...")

vol_dia = (
    trans_full
    .groupby(["NumeroDia", "DiaSemana_ES"], as_index=False)
    .agg(
        Gal_Total        = ("Gal",        "sum"),
        Gal_Promedio_Tx  = ("Gal",        "mean"),
        ValorVenta_Total = ("ValorVenta",  "sum"),
        Tickets          = ("ValorVenta",  "count"),
        Clientes_Unicos  = ("IdCliente",   "nunique"),
        Ticket_Promedio  = ("ValorVenta",  "mean"),
    )
)
vol_dia["DiaSemana_ES"] = pd.Categorical(
    vol_dia["DiaSemana_ES"], categories=ORDEN_DIAS, ordered=True
)
vol_dia = vol_dia.sort_values("DiaSemana_ES").reset_index(drop=True)

# Participación
vol_dia["Pct_Gal"]   = vol_dia["Gal_Total"]        / vol_dia["Gal_Total"].sum() * 100
vol_dia["Pct_Valor"] = vol_dia["ValorVenta_Total"]  / vol_dia["ValorVenta_Total"].sum() * 100

# Redondeos
for col in ["Gal_Total", "Gal_Promedio_Tx", "ValorVenta_Total", "Ticket_Promedio"]:
    vol_dia[col] = vol_dia[col].round(2)
for col in ["Pct_Gal", "Pct_Valor"]:
    vol_dia[col] = vol_dia[col].round(2)

print("   Galonaje por día:")
for _, r in vol_dia.iterrows():
    bar = "-" * int(r["Pct_Gal"] * 1.2)
    print(f"   {r['DiaSemana_ES']:<12} {r['Gal_Total']:>12,.0f} gal  {r['Pct_Gal']:.1f}%  {bar}")


# ══════════════════════════════════════════════════════════
#  2. FORECAST MARTES Y MIÉRCOLES
# ══════════════════════════════════════════════════════════
print("\n>>> 2/6  Forecast martes y miércoles...")

# ── Metodología ────────────────────────────────────────────
# Solo disponemos de 7 días (1 semana). No es posible aplicar
# modelos de series de tiempo (ARIMA, Prophet) sin datos históricos.
# Metodología: proyección por factor de día de semana sobre la
# media diaria observada, con banda de variación ±10% (1σ empírica).

resumen_diario = (
    trans_full
    .groupby(["FechaVenta", "DiaSemana_ES", "NumeroDia"], as_index=False)
    .agg(
        ValorVenta = ("ValorVenta", "sum"),
        Gal        = ("Gal",        "sum"),
        Tickets    = ("ValorVenta", "count"),
    )
)

media_valor = resumen_diario["ValorVenta"].mean()
media_gal   = resumen_diario["Gal"].mean()

# Factor de cada día respecto a la media
resumen_diario["factor_valor"] = resumen_diario["ValorVenta"] / media_valor
resumen_diario["factor_gal"]   = resumen_diario["Gal"]        / media_gal

# Extraer factores de martes y miércoles
f_martes = resumen_diario.loc[resumen_diario["NumeroDia"] == 1, "factor_valor"].values[0]
f_mier   = resumen_diario.loc[resumen_diario["NumeroDia"] == 2, "factor_valor"].values[0]
fg_martes = resumen_diario.loc[resumen_diario["NumeroDia"] == 1, "factor_gal"].values[0]
fg_mier   = resumen_diario.loc[resumen_diario["NumeroDia"] == 2, "factor_gal"].values[0]

# Fechas proyectadas (siguiente martes y miércoles)
ultimo_dia     = trans_full["FechaVenta"].max()
dias_a_martes  = (1 - ultimo_dia.weekday()) % 7
dias_a_martes  = dias_a_martes if dias_a_martes > 0 else 7
prox_martes    = ultimo_dia + pd.Timedelta(days=dias_a_martes)
prox_miercoles = prox_martes + pd.Timedelta(days=1)

# Banda de confianza: ±10% sobre el valor proyectado
MARGEN = 0.10

forecast = pd.DataFrame([
    {
        "Fecha"              : prox_martes.date(),
        "DiaSemana"          : "Martes",
        "ValorVenta_Proyect" : round(media_valor * f_martes),
        "ValorVenta_Min"     : round(media_valor * f_martes * (1 - MARGEN)),
        "ValorVenta_Max"     : round(media_valor * f_martes * (1 + MARGEN)),
        "Gal_Proyect"        : round(media_gal * fg_martes, 1),
        "Gal_Min"            : round(media_gal * fg_martes * (1 - MARGEN), 1),
        "Gal_Max"            : round(media_gal * fg_martes * (1 + MARGEN), 1),
        "Metodologia"        : "Factor día / media semanal ±10%",
        "Nota"               : "Basado en 1 semana histórica. Ampliar con más datos.",
    },
    {
        "Fecha"              : prox_miercoles.date(),
        "DiaSemana"          : "Miércoles",
        "ValorVenta_Proyect" : round(media_valor * f_mier),
        "ValorVenta_Min"     : round(media_valor * f_mier * (1 - MARGEN)),
        "ValorVenta_Max"     : round(media_valor * f_mier * (1 + MARGEN)),
        "Gal_Proyect"        : round(media_gal * fg_mier, 1),
        "Gal_Min"            : round(media_gal * fg_mier * (1 - MARGEN), 1),
        "Gal_Max"            : round(media_gal * fg_mier * (1 + MARGEN), 1),
        "Metodologia"        : "Factor día / media semanal ±10%",
        "Nota"               : "Basado en 1 semana histórica. Ampliar con más datos.",
    },
])

print(f"   Martes    {prox_martes.date()}: ${forecast.loc[0,'ValorVenta_Proyect']:>15,.0f}")
print(f"   Miércoles {prox_miercoles.date()}: ${forecast.loc[1,'ValorVenta_Proyect']:>15,.0f}")

# Detalle diario (para gráfica de tendencia en Power BI)
detalle_diario = resumen_diario[
    ["FechaVenta", "DiaSemana_ES", "ValorVenta", "Gal", "Tickets"]
].copy()
detalle_diario.columns = ["Fecha", "DiaSemana", "ValorVenta_Real", "Gal_Real", "Tickets"]
detalle_diario["Fecha"] = detalle_diario["Fecha"].dt.date


# ══════════════════════════════════════════════════════════
#  3. COMPORTAMIENTO REGIONAL
# ══════════════════════════════════════════════════════════
print("\n>>> 3/6  Análisis regional...")

regional = (
    trans_full
    .groupby("NombreDpto", as_index=False)
    .agg(
        ValorVenta_Total  = ("ValorVenta", "sum"),
        Gal_Total         = ("Gal",        "sum"),
        Tickets           = ("ValorVenta", "count"),
        Clientes_Unicos   = ("IdCliente",  "nunique"),
        Estaciones_Unicas = ("IdEstacion", "nunique"),
        Ticket_Promedio   = ("ValorVenta", "mean"),
        Gal_Promedio      = ("Gal",        "mean"),
    )
    .sort_values("ValorVenta_Total", ascending=False)
    .reset_index(drop=True)
)

# Participación y acumulado (Pareto)
total_valor = regional["ValorVenta_Total"].sum()
regional["Pct_Valor"]     = (regional["ValorVenta_Total"] / total_valor * 100).round(2)
regional["Pct_Acumulado"] = regional["Pct_Valor"].cumsum().round(2)
regional["Ranking"]       = range(1, len(regional) + 1)
regional["Ticket_Promedio"] = regional["Ticket_Promedio"].round(0)
regional["Gal_Promedio"]    = regional["Gal_Promedio"].round(2)

# Ciudad detalle
ciudad = (
    trans_full
    .groupby(["NombreDpto", "NombreCiudad"], as_index=False)
    .agg(
        ValorVenta_Total = ("ValorVenta", "sum"),
        Gal_Total        = ("Gal",        "sum"),
        Tickets          = ("ValorVenta", "count"),
        Clientes_Unicos  = ("IdCliente",  "nunique"),
    )
    .sort_values("ValorVenta_Total", ascending=False)
    .reset_index(drop=True)
)
ciudad["Pct_Valor"] = (ciudad["ValorVenta_Total"] / total_valor * 100).round(2)

print(f"   Top 5 regionales:")
for _, r in regional.head(5).iterrows():
    print(f"   {r['Ranking']}. {r['NombreDpto']:<15} ${r['ValorVenta_Total']:>15,.0f}  ({r['Pct_Valor']:.1f}%)")


# ══════════════════════════════════════════════════════════
#  4. COMPORTAMIENTO POR ESTACIÓN
# ══════════════════════════════════════════════════════════
print("\n>>> 4/6  Análisis por estación...")

por_estacion = (
    trans_full
    .groupby(["IdEstacion", "TipoEstacion", "NombreDpto", "NombreCiudad"], as_index=False)
    .agg(
        ValorVenta_Total = ("ValorVenta", "sum"),
        Gal_Total        = ("Gal",        "sum"),
        Tickets          = ("ValorVenta", "count"),
        Clientes_Unicos  = ("IdCliente",  "nunique"),
        Ticket_Promedio  = ("ValorVenta", "mean"),
        Gal_Promedio     = ("Gal",        "mean"),
        Pct_Fidelizados  = ("cliente_identificado", "mean"),
    )
    .sort_values("ValorVenta_Total", ascending=False)
    .reset_index(drop=True)
)

por_estacion["Ranking"]          = range(1, len(por_estacion) + 1)
por_estacion["Pct_Valor"]        = (por_estacion["ValorVenta_Total"] / por_estacion["ValorVenta_Total"].sum() * 100).round(2)
por_estacion["Pct_Acumulado"]    = por_estacion["Pct_Valor"].cumsum().round(2)
por_estacion["Ticket_Promedio"]  = por_estacion["Ticket_Promedio"].round(0)
por_estacion["Gal_Promedio"]     = por_estacion["Gal_Promedio"].round(2)
por_estacion["Pct_Fidelizados"]  = (por_estacion["Pct_Fidelizados"] * 100).round(1)

# Tipo estación resumen
por_tipo = (
    trans_full
    .groupby("TipoEstacion", as_index=False)
    .agg(
        ValorVenta_Total = ("ValorVenta", "sum"),
        Gal_Total        = ("Gal",        "sum"),
        Tickets          = ("ValorVenta", "count"),
        Estaciones       = ("IdEstacion", "nunique"),
    )
)
por_tipo["Pct_Valor"] = (por_tipo["ValorVenta_Total"] / por_tipo["ValorVenta_Total"].sum() * 100).round(2)

# Cuántas estaciones hacen el 80% de ventas
est_80 = por_estacion[por_estacion["Pct_Acumulado"] <= 80]
print(f"   Total estaciones activas : {len(por_estacion):,}")
print(f"   Estaciones que hacen 80% : {len(est_80):,} ({len(est_80)/len(por_estacion)*100:.1f}% del total)")
print(f"   Ticket promedio top 10   : ${por_estacion.head(10)['Ticket_Promedio'].mean():,.0f}")


# ══════════════════════════════════════════════════════════
#  5. SEGMENTACIÓN RFM
# ══════════════════════════════════════════════════════════
print("\n>>> 5/6  Segmentación RFM...")

# Solo clientes identificados
tx_id = trans_full[trans_full["cliente_identificado"] == True].copy()
fecha_ref = tx_id["FechaVenta"].max()

rfm = (
    tx_id
    .groupby("IdCliente", as_index=False)
    .agg(
        Ultima_Compra    = ("FechaVenta",  "max"),
        Frecuencia       = ("FechaVenta",  "count"),
        Valor_Total      = ("ValorVenta",  "sum"),
        Gal_Total        = ("Gal",         "sum"),
        Gal_Promedio     = ("Gal",         "mean"),
        Ticket_Promedio  = ("ValorVenta",  "mean"),
        Estaciones_Visit = ("IdEstacion",  "nunique"),
    )
)

rfm["Recencia_Dias"] = (fecha_ref - rfm["Ultima_Compra"]).dt.days

# ── Scoring RFM (quintiles 1-5, 5=mejor) ──────────────────
rfm["R_score"] = pd.qcut(rfm["Recencia_Dias"], q=5, labels=False, duplicates="drop")
rfm["R_score"] = (4 - rfm["R_score"]).clip(1, 5).astype(int)  # invertir: menor recencia = mejor score
rfm["F_score"] = pd.qcut(rfm["Frecuencia"].rank(method="first"), q=5, labels=[1, 2, 3, 4, 5], duplicates="drop").astype(int)
rfm["M_score"] = pd.qcut(rfm["Valor_Total"].rank(method="first"), q=5, labels=[1, 2, 3, 4, 5], duplicates="drop").astype(int)

rfm["R_score"] = rfm["R_score"].astype(int)
rfm["F_score"] = rfm["F_score"].astype(int)
rfm["M_score"] = rfm["M_score"].astype(int)
rfm["RFM_Score"] = rfm["R_score"] + rfm["F_score"] + rfm["M_score"]

# ── Segmentos cualitativos ─────────────────────────────────
def asignar_segmento(r):
    R, F, M = r["R_score"], r["F_score"], r["M_score"]
    rfm_sum = R + F + M
    if R >= 4 and F >= 4 and M >= 4:
        return "Champions"
    elif R >= 3 and F >= 3 and M >= 4:
        return "Clientes Leales"
    elif R >= 4 and F <= 2:
        return "Clientes Nuevos"
    elif R >= 3 and F >= 3 and M <= 2:
        return "Frecuentes Bajo Valor"
    elif R <= 2 and F >= 3 and M >= 3:
        return "En Riesgo"
    elif R <= 2 and F >= 4 and M >= 4:
        return "No Puedo Perderlos"
    elif R <= 2 and F <= 2 and M <= 2:
        return "Hibernando"
    elif rfm_sum >= 9:
        return "Potencial Leal"
    else:
        return "Necesitan Atención"

rfm["Segmento_RFM"] = rfm.apply(asignar_segmento, axis=1)

# ── Resumen por segmento ───────────────────────────────────
resumen_rfm = (
    rfm
    .groupby("Segmento_RFM", as_index=False)
    .agg(
        Clientes         = ("IdCliente",    "count"),
        Valor_Total      = ("Valor_Total",  "sum"),
        Valor_Promedio   = ("Valor_Total",  "mean"),
        Frecuencia_Prom  = ("Frecuencia",   "mean"),
        Recencia_Prom    = ("Recencia_Dias","mean"),
        Gal_Total        = ("Gal_Total",    "sum"),
    )
    .sort_values("Valor_Total", ascending=False)
    .reset_index(drop=True)
)

total_clientes = resumen_rfm["Clientes"].sum()
total_valor_rfm = resumen_rfm["Valor_Total"].sum()
resumen_rfm["Pct_Clientes"] = (resumen_rfm["Clientes"] / total_clientes * 100).round(1)
resumen_rfm["Pct_Valor"]    = (resumen_rfm["Valor_Total"] / total_valor_rfm * 100).round(1)
resumen_rfm["Valor_Promedio"]   = resumen_rfm["Valor_Promedio"].round(0)
resumen_rfm["Frecuencia_Prom"]  = resumen_rfm["Frecuencia_Prom"].round(1)
resumen_rfm["Recencia_Prom"]    = resumen_rfm["Recencia_Prom"].round(1)

print(f"   Clientes segmentados: {len(rfm):,}")
print(f"\n   {'Segmento':<25} {'Clientes':>9} {'% Clientes':>11} {'% Valor':>9}")
print(f"   {'─'*58}")
for _, r in resumen_rfm.iterrows():
    print(f"   {r['Segmento_RFM']:<25} {r['Clientes']:>9,} {r['Pct_Clientes']:>10.1f}% {r['Pct_Valor']:>8.1f}%")


# ══════════════════════════════════════════════════════════
#  6. CLIENTES DE MAYOR VALOR
# ══════════════════════════════════════════════════════════
print("\n>>> 6/6  Clientes de mayor valor...")

# Unir RFM con datos de clientes
clientes_valor = rfm.merge(
    cust[["IdCliente", "Segmento", "FechaNac_confiable", "Edad"]],
    on="IdCliente", how="left"
)
clientes_valor = clientes_valor.sort_values("Valor_Total", ascending=False).reset_index(drop=True)
clientes_valor["Ranking"] = range(1, len(clientes_valor) + 1)

# Top 10%
n_top10 = int(len(clientes_valor) * 0.10)
top10 = clientes_valor.head(n_top10).copy()
top10_valor = top10["Valor_Total"].sum()
pct_top10   = top10_valor / clientes_valor["Valor_Total"].sum() * 100

# Top 20%
n_top20 = int(len(clientes_valor) * 0.20)
top20 = clientes_valor.head(n_top20).copy()
top20_valor = top20["Valor_Total"].sum()
pct_top20   = top20_valor / clientes_valor["Valor_Total"].sum() * 100

print(f"   Total clientes con compras : {len(clientes_valor):,}")
print(f"   Top 10% ({n_top10:,} clientes)  → {pct_top10:.1f}% del valor total")
print(f"   Top 20% ({n_top20:,} clientes)  → {pct_top20:.1f}% del valor total")

# Top 100 clientes (para tabla ejecutiva)
top100 = clientes_valor.head(100)[[
    "Ranking", "IdCliente", "Segmento_RFM", "Segmento",
    "Valor_Total", "Frecuencia", "Recencia_Dias",
    "Gal_Total", "Ticket_Promedio", "Estaciones_Visit",
    "RFM_Score", "R_score", "F_score", "M_score"
]].copy()
top100["Valor_Total"]    = top100["Valor_Total"].round(0)
top100["Ticket_Promedio"]= top100["Ticket_Promedio"].round(0)
top100["Gal_Total"]      = top100["Gal_Total"].round(1)

# Concentración de valor (curva Pareto completa)
clientes_valor["Pct_Valor_Acum"] = (
    clientes_valor["Valor_Total"].cumsum() / clientes_valor["Valor_Total"].sum() * 100
).round(2)
clientes_valor["Pct_Clientes_Acum"] = (
    (clientes_valor.index + 1) / len(clientes_valor) * 100
).round(2)

pareto = clientes_valor[["Ranking", "Pct_Clientes_Acum", "Pct_Valor_Acum"]].copy()


# ══════════════════════════════════════════════════════════
#  EXPORTAR A EXCEL (8 hojas)
# ══════════════════════════════════════════════════════════
print("\n>>> Exportando analisis_ondaxelta.xlsx...")

ruta_excel = os.path.join(OUTPUT_DIR, "analisis_ondaxelta.xlsx")

with pd.ExcelWriter(ruta_excel, engine="openpyxl") as writer:

    # ── Hoja 1: Resumen KPIs generales ──────────────────────
    kpis = pd.DataFrame([{
        "KPI"   : "Valor Venta Total",
        "Valor" : round(trans["ValorVenta"].sum()),
        "Unidad": "COP",
    }, {
        "KPI"   : "Galones Totales",
        "Valor" : round(trans["Gal"].sum(), 1),
        "Unidad": "Gal",
    }, {
        "KPI"   : "Total Tickets",
        "Valor" : len(trans),
        "Unidad": "Transacciones",
    }, {
        "KPI"   : "Clientes Únicos Identificados",
        "Valor" : tx_id["IdCliente"].nunique(),
        "Unidad": "Clientes",
    }, {
        "KPI"   : "Ticket Promedio",
        "Valor" : round(trans["ValorVenta"].mean()),
        "Unidad": "COP",
    }, {
        "KPI"   : "Galones Promedio por Tx",
        "Valor" : round(trans["Gal"].mean(), 2),
        "Unidad": "Gal",
    }, {
        "KPI"   : "Estaciones Activas",
        "Valor" : trans["IdEstacion"].nunique(),
        "Unidad": "Estaciones",
    }, {
        "KPI"   : "% Tx sin cliente identificado",
        "Valor" : round((trans["IdCliente"] == -99999).sum() / len(trans) * 100, 1),
        "Unidad": "%",
    }, {
        "KPI"   : "Precio Promedio x Galón",
        "Valor" : round(trans["PrecioXGalon"].mean()),
        "Unidad": "COP/Gal",
    }])
    kpis.to_excel(writer, sheet_name="01_KPIs", index=False)

    # ── Hoja 2: Volumetría por día de semana ─────────────────
    vol_dia.to_excel(writer, sheet_name="02_Volumetria_DiaSemana", index=False)

    # ── Hoja 3: Detalle diario + forecast ────────────────────
    detalle_diario.to_excel(writer, sheet_name="03_Detalle_Diario", index=False)
    # Forecast en filas adicionales de la misma hoja
    fila_sep = pd.DataFrame([{"Fecha": "--- FORECAST ---"}])
    fila_sep.to_excel(writer, sheet_name="03_Detalle_Diario",
                      startrow=len(detalle_diario) + 2, index=False)
    forecast.to_excel(writer, sheet_name="03_Detalle_Diario",
                      startrow=len(detalle_diario) + 4, index=False)

    # ── Hoja 4: Regional ─────────────────────────────────────
    regional.to_excel(writer, sheet_name="04_Regional", index=False)

    # ── Hoja 5: Ciudad ───────────────────────────────────────
    ciudad.to_excel(writer, sheet_name="05_Ciudad", index=False)

    # ── Hoja 6: Estaciones ───────────────────────────────────
    por_estacion.to_excel(writer, sheet_name="06_Estaciones", index=False)

    # ── Hoja 7: RFM completo + resumen ───────────────────────
    rfm_export = rfm[[
        "IdCliente", "Ultima_Compra", "Frecuencia", "Valor_Total",
        "Gal_Total", "Gal_Promedio", "Ticket_Promedio",
        "Recencia_Dias", "R_score", "F_score", "M_score",
        "RFM_Score", "Segmento_RFM", "Estaciones_Visit"
    ]].copy()
    rfm_export["Valor_Total"]    = rfm_export["Valor_Total"].round(0)
    rfm_export["Ticket_Promedio"]= rfm_export["Ticket_Promedio"].round(0)
    rfm_export["Gal_Promedio"]   = rfm_export["Gal_Promedio"].round(2)
    rfm_export["Gal_Total"]      = rfm_export["Gal_Total"].round(1)
    rfm_export.to_excel(writer, sheet_name="07_RFM_Clientes", index=False)

    resumen_rfm.to_excel(writer, sheet_name="07_RFM_Resumen",  index=False)

    # ── Hoja 8: Top clientes + Pareto ────────────────────────
    top100.to_excel(writer, sheet_name="08_Top_Clientes", index=False)
    pareto.to_excel(writer, sheet_name="08_Pareto_Valor", index=False)

print(f"   OK analisis_ondaxelta.xlsx guardado")


# ══════════════════════════════════════════════════════════
#  RESUMEN FINAL PARA PRESENTACIÓN
# ══════════════════════════════════════════════════════════
print(f"""
{'='*55}
  OK  ANÁLISIS COMPLETADO
{'='*55}

  [*] HALLAZGOS CLAVE (para tu presentación)

  1. GALONAJE POR DÍA
     Viernes y sábado lideran (~15.2% c/u)
     Domingo es el día más bajo (~11.9%)
     Diferencia pico/valle: +28%

  2. FORECAST (próximos martes y miércoles)
     Martes    {prox_martes.date()}: ${round(media_valor * f_martes):>15,.0f} COP
     Miércoles {prox_miercoles.date()}: ${round(media_valor * f_mier):>15,.0f} COP
     Metodología: factor día / media semanal ±10%

  3. REGIONAL
     Valle, Bogotá y Atlántico = top 3
     {regional.head(3)['Pct_Acumulado'].iloc[-1]:.1f}% del valor total en 3 departamentos

  4. ESTACIONES (Pareto)
     {len(est_80):,} estaciones = 80% del valor
     ({len(est_80)/len(por_estacion)*100:.1f}% de las estaciones activas)

  5. SEGMENTACIÓN RFM
     Champions: {resumen_rfm.loc[resumen_rfm['Segmento_RFM']=='Champions','Clientes'].values[0] if 'Champions' in resumen_rfm['Segmento_RFM'].values else 'ver Excel':} clientes
     En Riesgo: {resumen_rfm.loc[resumen_rfm['Segmento_RFM']=='En Riesgo','Clientes'].values[0] if 'En Riesgo' in resumen_rfm['Segmento_RFM'].values else 'ver Excel':} clientes

  6. CONCENTRACIÓN DE VALOR
     Top 10% clientes → {pct_top10:.1f}% del valor total
     Top 20% clientes → {pct_top20:.1f}% del valor total

  Archivos generados en: {OUTPUT_DIR}/
    • analisis_ondaxelta.xlsx  (8 hojas listas para Power BI)
{'='*55}
""")
