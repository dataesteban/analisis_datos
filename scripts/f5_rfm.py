"""
============================================================
  F5 - Segmentacion RFM + caracterizacion demografica
  Proposito: cifras de orientacion para hallazgos/05_rfm.md
  Python   : 3.9+
  Deps     : pandas, numpy
  Entrada  : output/trans_clean.csv, customers_clean.csv, geo_clean.csv
============================================================
EJECUCION:
    python scripts/f5_rfm.py

NOTAS METODOLOGICAS:
  - R: scoring manual (qcut falla con 7 dias unicos)
  - F y M: quintiles balanceados con rank(method='first')
  - 10 segmentos cualitativos
  - EsFlota = #placas distintas >= 4
  - Caracterizacion: cruce con edad (donde confiable), segmento original, dpto
============================================================
"""

import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

import pandas as pd
import numpy as np

UMBRAL_FLOTA = 4


def cargar() -> tuple[pd.DataFrame, pd.DataFrame]:
    t = pd.read_csv(
        "output/trans_clean.csv",
        usecols=["IdCliente", "IdEstacion", "Placa", "ValorVenta",
                 "Gal", "FechaVenta", "cliente_identificado"],
        parse_dates=["FechaVenta"],
    )
    cust = pd.read_csv(
        "output/customers_clean.csv",
        usecols=["IdCliente", "Segmento", "FechaNac_confiable",
                 "Edad", "IdCiudad"],
    )
    geo = pd.read_csv("output/geo_clean.csv",
                      usecols=["IdCiudad", "NombreDpto"])
    cust = cust.merge(geo, on="IdCiudad", how="left")
    return t, cust


def construir_rfm(tx: pd.DataFrame) -> tuple[pd.DataFrame, pd.Timestamp]:
    ti = tx[tx["cliente_identificado"] == True].copy()
    fecha_ref = ti["FechaVenta"].max()

    rfm = (ti.groupby("IdCliente")
             .agg(Ultima=("FechaVenta", "max"),
                  Frecuencia=("FechaVenta", "count"),
                  Valor=("ValorVenta", "sum"),
                  Gal=("Gal", "sum"),
                  Tkt_prom=("ValorVenta", "mean"),
                  Placas=("Placa", "nunique"),
                  Estaciones=("IdEstacion", "nunique"))
             .reset_index())

    rfm["Recencia"] = (fecha_ref - rfm["Ultima"]).dt.days
    return rfm, fecha_ref


def r_score(dias: int) -> int:
    """Scoring R adaptado a 7 dias (qcut falla por baja cardinalidad)."""
    if dias == 0:
        return 5
    if dias <= 1:
        return 4
    if dias <= 2:
        return 3
    if dias <= 4:
        return 2
    return 1


def asignar_segmento(r: pd.Series) -> str:
    R, F, M = r["R"], r["F"], r["M"]
    if R >= 4 and F >= 4 and M >= 4:
        return "Champions"
    if R >= 4 and F >= 3 and M >= 3:
        return "Leales"
    if R >= 4 and F <= 2:
        return "Nuevos"
    if R >= 3 and F >= 3 and M <= 2:
        return "Frecuentes bajo valor"
    if R <= 2 and F >= 4 and M >= 4:
        return "No puedo perderlos"
    if R <= 2 and F >= 3:
        return "En riesgo"
    if R <= 2 and F <= 2 and M >= 4:
        return "Grandes durmiendo"
    if R <= 2 and F <= 2:
        return "Hibernando"
    if R + F + M >= 9:
        return "Potencial leal"
    return "Necesitan atencion"


def scoring(rfm: pd.DataFrame) -> pd.DataFrame:
    rfm["R"] = rfm["Recencia"].apply(r_score)
    rfm["F"] = pd.qcut(
        rfm["Frecuencia"].rank(method="first"),
        5, labels=[1, 2, 3, 4, 5]).astype(int)
    rfm["M"] = pd.qcut(
        rfm["Valor"].rank(method="first"),
        5, labels=[1, 2, 3, 4, 5]).astype(int)
    rfm["RFM_Score"] = rfm["R"] + rfm["F"] + rfm["M"]
    rfm["Segmento_RFM"] = rfm.apply(asignar_segmento, axis=1)
    rfm["EsFlota"] = rfm["Placas"] >= UMBRAL_FLOTA
    return rfm


def resumen_segmentos(rfm: pd.DataFrame) -> pd.DataFrame:
    res = (rfm.groupby("Segmento_RFM")
              .agg(Clientes=("IdCliente", "count"),
                   Valor=("Valor", "sum"),
                   Valor_prom=("Valor", "mean"),
                   Freq_prom=("Frecuencia", "mean"),
                   Rec_prom=("Recencia", "mean"),
                   Gal_total=("Gal", "sum"),
                   Pct_flota=("EsFlota", "mean"),
                   Edad_prom=("Edad", "mean"))
              .reset_index()
              .sort_values("Valor", ascending=False))
    res["Pct_cli"] = res["Clientes"] / res["Clientes"].sum() * 100
    res["Pct_val"] = res["Valor"] / res["Valor"].sum() * 100
    res["Pct_flota"] = res["Pct_flota"] * 100
    return res


def imprimir(rfm: pd.DataFrame, fecha_ref: pd.Timestamp) -> None:
    print(f"Fecha referencia: {fecha_ref.date()}")
    print(f"Clientes RFM    : {len(rfm):,}")
    print()

    print("Distribucion scores R/F/M (debe ser ~balanceada en F y M):")
    for col in ["R", "F", "M"]:
        print(f"  {col}: {dict(rfm[col].value_counts().sort_index())}")
    print()

    res = resumen_segmentos(rfm)
    print("=== SEGMENTOS RFM ===")
    print(f"{'Segmento':<22} {'Clientes':>9} {'%Cli':>5} {'%Val':>5} "
          f"{'V.Prom':>10} {'F.Prom':>6} {'R.Prom':>6} {'Edad':>5} "
          f"{'%Flota':>6}")
    print("-" * 100)
    for _, r in res.iterrows():
        edad = f"{r['Edad_prom']:.0f}" if pd.notna(r["Edad_prom"]) else "n/d"
        print(f"{r['Segmento_RFM']:<22} {r['Clientes']:>9,} "
              f"{r['Pct_cli']:>4.1f}% {r['Pct_val']:>4.1f}% "
              f"{r['Valor_prom']:>10,.0f} {r['Freq_prom']:>6.1f} "
              f"{r['Rec_prom']:>6.1f} {edad:>5} {r['Pct_flota']:>5.1f}%")
    print()

    print("=== SEGMENTO ORIGINAL por Segmento RFM (% participacion) ===")
    ct = pd.crosstab(rfm["Segmento_RFM"], rfm["Segmento"],
                     normalize="index") * 100
    print(ct.round(1).to_string())
    print()

    print("=== TOP 3 DPTOS por Segmento RFM ===")
    for seg in res["Segmento_RFM"]:
        top = rfm[rfm["Segmento_RFM"] == seg]["NombreDpto"].value_counts().head(3)
        print(f"  {seg:<22}: {dict(top)}")


if __name__ == "__main__":
    tx, cust = cargar()
    rfm, fecha_ref = construir_rfm(tx)
    rfm = scoring(rfm)
    rfm = rfm.merge(cust, on="IdCliente", how="left")
    imprimir(rfm, fecha_ref)
