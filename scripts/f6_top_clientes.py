"""
============================================================
  F6 - Clientes de mayor valor para la marca
  Proposito: cifras de orientacion para hallazgos/06_top_clientes.md
  Python   : 3.9+
  Deps     : pandas
  Entrada  : output/trans_clean.csv, customers_clean.csv, geo_clean.csv
============================================================
EJECUCION:
    python scripts/f6_top_clientes.py

INCLUYE:
  - Concentracion top 1/5/10/20/30/50%
  - Pareto inverso (cuantos clientes = 50/80/90%)
  - Perfil Top 10% y Top 1% (incluye %Flotas, edad, dpto)
  - Top 10 clientes individuales
  - Ventas no atribuibles (sin IdCliente)
============================================================
"""

import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

import pandas as pd

UMBRAL_FLOTA = 4
TRAMOS_TOP_PCT = [1, 5, 10, 20, 30, 50]
UMBRALES_PARETO = [50, 80, 90]


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


def ranking_clientes(tx: pd.DataFrame) -> pd.DataFrame:
    ti = tx[tx["cliente_identificado"] == True].copy()
    cv = (ti.groupby("IdCliente")
              .agg(Valor=("ValorVenta", "sum"),
                   Frec=("FechaVenta", "count"),
                   Gal=("Gal", "sum"),
                   Tkt_prom=("ValorVenta", "mean"),
                   Placas=("Placa", "nunique"),
                   Estaciones=("IdEstacion", "nunique"),
                   Ultima=("FechaVenta", "max"))
              .reset_index()
              .sort_values("Valor", ascending=False)
              .reset_index(drop=True))
    cv["Rank"] = cv.index + 1
    cv["EsFlota"] = cv["Placas"] >= UMBRAL_FLOTA
    cv["Pct_val_acum"] = cv["Valor"].cumsum() / cv["Valor"].sum() * 100
    return cv


def imprimir_concentracion(cv: pd.DataFrame) -> None:
    total_val = cv["Valor"].sum()
    total_cli = len(cv)

    print(f"Universo: {total_cli:,} clientes identificados")
    print(f"Valor total: ${total_val:,.0f}")
    print()

    print("=== CONCENTRACION TOP N% ===")
    for pct in TRAMOS_TOP_PCT:
        n = int(total_cli * pct / 100)
        val = cv.head(n)["Valor"].sum()
        print(f"  Top {pct:>3}% ({n:>6,} cli): "
              f"${val:>15,.0f}  ({val/total_val*100:>5.1f}% valor)")
    print()

    print("=== PARETO INVERSO ===")
    for u in UMBRALES_PARETO:
        n = (cv["Pct_val_acum"] <= u).sum()
        print(f"  Para {u}%: {n:,} clientes ({n/total_cli*100:.1f}%)")
    print()


def perfil_tramo(cv: pd.DataFrame, pct: int, etiqueta: str) -> None:
    total_val = cv["Valor"].sum()
    total_cli = len(cv)
    tramo = cv.head(int(total_cli * pct / 100))

    print(f"=== PERFIL {etiqueta} ===")
    print(f"Clientes        : {len(tramo):,}")
    print(f"Valor sumado    : ${tramo['Valor'].sum():,.0f} "
          f"({tramo['Valor'].sum()/total_val*100:.1f}%)")
    print(f"Valor promedio  : ${tramo['Valor'].mean():,.0f}")
    print(f"Frec promedio   : {tramo['Frec'].mean():.1f} tx")
    print(f"Placas promedio : {tramo['Placas'].mean():.1f}")
    print(f"%Flotas         : {tramo['EsFlota'].mean()*100:.1f}%")
    if "Edad" in tramo.columns:
        print(f"Edad promedio   : {tramo['Edad'].mean():.1f}")
    if "NombreDpto" in tramo.columns:
        print(f"Top 5 dptos     : "
              f"{dict(tramo['NombreDpto'].value_counts().head(5))}")
    if "Segmento" in tramo.columns:
        seg = tramo["Segmento"].value_counts(normalize=True).round(3) * 100
        print(f"Segmento orig   : {dict(seg)}")
    print()


def imprimir_top10(cv: pd.DataFrame) -> None:
    print("=== TOP 10 CLIENTES ===")
    print(f"{'#':>3} {'IdCliente':>10} {'Valor':>14} {'Frec':>5} "
          f"{'Placas':>6} {'Est':>4} {'Dpto':<15} {'Segmento':<14}")
    print("-" * 90)
    for _, r in cv.head(10).iterrows():
        seg = str(r.get("Segmento", "n/d"))[:14]
        dp = str(r.get("NombreDpto", "n/d"))[:15]
        print(f"{r['Rank']:>3} {r['IdCliente']:>10} "
              f"{r['Valor']:>14,.0f} {r['Frec']:>5} "
              f"{r['Placas']:>6} {r['Estaciones']:>4} "
              f"{dp:<15} {seg:<14}")
    print()


def imprimir_no_atribuible(tx: pd.DataFrame) -> None:
    sin_id = tx[~tx["cliente_identificado"]]
    total = tx["ValorVenta"].sum()
    print("=== VENTAS NO ATRIBUIBLES ===")
    print(f"Tx sin IdCliente: {len(sin_id):,} "
          f"({len(sin_id)/len(tx)*100:.1f}%)")
    print(f"Valor           : ${sin_id['ValorVenta'].sum():,.0f} "
          f"({sin_id['ValorVenta'].sum()/total*100:.1f}% del total)")


if __name__ == "__main__":
    tx, cust = cargar()
    cv = ranking_clientes(tx)
    cv = cv.merge(cust, on="IdCliente", how="left")

    imprimir_concentracion(cv)
    perfil_tramo(cv, 10, "TOP 10%")
    perfil_tramo(cv, 1, "TOP 1% (super premium)")
    imprimir_top10(cv)
    imprimir_no_atribuible(tx)
