"""
============================================================
  F3 - Comportamiento por Departamento + ciudad + Pareto
  Proposito: cifras de orientacion para hallazgos/03_regional.md
  Python   : 3.9+
  Deps     : pandas
  Entrada  : output/trans_clean.csv, estaciones_clean.csv, geo_clean.csv
============================================================
EJECUCION:
    python scripts/f3_regional.py
============================================================
"""

import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

import pandas as pd


def cargar_full() -> pd.DataFrame:
    """Une transacciones con estaciones y geografía."""
    t = pd.read_csv(
        "output/trans_clean.csv",
        usecols=["IdCliente", "IdEstacion", "ValorVenta", "Gal"],
    )
    est = pd.read_csv(
        "output/estaciones_clean.csv",
        usecols=["IdEstacion", "IdCiudad", "TipoEstacion"],
    )
    geo = pd.read_csv("output/geo_clean.csv")
    return (t.merge(est, on="IdEstacion", how="left")
             .merge(geo, on="IdCiudad", how="left"))


def regional(full: pd.DataFrame) -> pd.DataFrame:
    r = (full.groupby("NombreDpto", dropna=False)
             .agg(Valor=("ValorVenta", "sum"),
                  Gal=("Gal", "sum"),
                  Tickets=("ValorVenta", "count"),
                  Clientes=("IdCliente", "nunique"),
                  Estaciones=("IdEstacion", "nunique"),
                  Ticket_prom=("ValorVenta", "mean"))
             .reset_index()
             .sort_values("Valor", ascending=False))
    total = r["Valor"].sum()
    r["Pct_val"] = r["Valor"] / total * 100
    r["Pct_acum"] = r["Pct_val"].cumsum()
    r["Rank"] = range(1, len(r) + 1)
    return r


def por_ciudad(full: pd.DataFrame) -> pd.DataFrame:
    c = (full.groupby(["NombreDpto", "NombreCiudad"], dropna=False)
             .agg(Valor=("ValorVenta", "sum"),
                  Tickets=("ValorVenta", "count"),
                  Clientes=("IdCliente", "nunique"))
             .reset_index()
             .sort_values("Valor", ascending=False))
    c["Pct"] = c["Valor"] / c["Valor"].sum() * 100
    return c


def imprimir(full: pd.DataFrame) -> None:
    reg = regional(full)
    ciu = por_ciudad(full)

    print(f"Tx con NombreDpto NaN: {full['NombreDpto'].isna().sum()}")
    print(f"Tx totales           : {len(full):,}")
    print(f"Departamentos activos: {len(reg)}")
    print()

    print("TOP 15 DEPARTAMENTOS:")
    print(f"{'#':>3} {'Dpto':<20} {'Valor':>15} {'%':>6} {'%Acum':>7} "
          f"{'Gal':>11} {'Tickets':>9} {'Clientes':>9} {'Est':>5} {'Tkt':>9}")
    print("-" * 110)
    for _, r in reg.head(15).iterrows():
        n = str(r["NombreDpto"])[:20] if pd.notna(r["NombreDpto"]) else "(sin geo)"
        print(f"{r['Rank']:>3} {n:<20} {r['Valor']:>15,.0f} "
              f"{r['Pct_val']:>5.1f}% {r['Pct_acum']:>6.1f}% "
              f"{r['Gal']:>11,.0f} {r['Tickets']:>9,} "
              f"{r['Clientes']:>9,} {r['Estaciones']:>5} "
              f"{r['Ticket_prom']:>9,.0f}")
    print()

    for u in [50, 80, 90]:
        n = (reg["Pct_acum"] <= u).sum()
        print(f"Dptos para {u}% del valor: {n} ({n/len(reg)*100:.0f}%)")
    print()

    print("TOP 10 CIUDADES:")
    print(f"{'#':>3} {'Dpto':<15} {'Ciudad':<25} {'Valor':>15} {'%':>6}")
    print("-" * 80)
    for i, (_, r) in enumerate(ciu.head(10).iterrows(), 1):
        d = (str(r["NombreDpto"])[:15] if pd.notna(r["NombreDpto"])
             else "(sin geo)")
        c = (str(r["NombreCiudad"])[:25] if pd.notna(r["NombreCiudad"])
             else "(sin geo)")
        print(f"{i:>3} {d:<15} {c:<25} {r['Valor']:>15,.0f} {r['Pct']:>5.1f}%")


if __name__ == "__main__":
    full = cargar_full()
    imprimir(full)
