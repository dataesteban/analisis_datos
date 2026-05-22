"""
============================================================
  F4 - Comportamiento por Estacion de servicio
  Proposito: cifras de orientacion para hallazgos/04_estaciones.md
  Python   : 3.9+
  Deps     : pandas
  Entrada  : output/trans_clean.csv, estaciones_clean.csv, geo_clean.csv
============================================================
EJECUCION:
    python scripts/f4_estaciones.py

INCLUYE:
  - Por TipoEstacion (Propia / Franquiciada / Operadora / Sin Clasificar)
  - Cobertura del maestro (activas vs maestro)
  - Pareto estaciones
  - Top 10 estaciones por valor
  - Top/Bottom fidelizacion (con minimo de tx)
============================================================
"""

import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

import pandas as pd

MIN_TX_FIDELIZACION = 1000


def cargar_full() -> tuple[pd.DataFrame, pd.DataFrame]:
    """Devuelve (full enriquecido, maestro estaciones)."""
    t = pd.read_csv(
        "output/trans_clean.csv",
        usecols=["IdCliente", "IdEstacion", "ValorVenta",
                 "Gal", "cliente_identificado"],
    )
    est = pd.read_csv("output/estaciones_clean.csv")
    geo = pd.read_csv(
        "output/geo_clean.csv",
        usecols=["IdCiudad", "NombreDpto", "NombreCiudad"],
    )
    full = (t.merge(est, on="IdEstacion", how="left")
             .merge(geo, on="IdCiudad", how="left"))
    return full, est


def por_tipo(full: pd.DataFrame, est: pd.DataFrame) -> pd.DataFrame:
    t = (full.groupby("TipoEstacion")
             .agg(Valor=("ValorVenta", "sum"),
                  Gal=("Gal", "sum"),
                  Tickets=("ValorVenta", "count"),
                  Estaciones=("IdEstacion", "nunique"),
                  Clientes=("IdCliente", "nunique"),
                  Tkt_prom=("ValorVenta", "mean"),
                  Pct_fid=("cliente_identificado", "mean"))
             .reset_index()
             .sort_values("Valor", ascending=False))

    total = t["Valor"].sum()
    t["Pct_val"] = t["Valor"] / total * 100
    t["Val_x_est"] = t["Valor"] / t["Estaciones"]
    t["Pct_fid"] = t["Pct_fid"] * 100

    maestro = (est.groupby("TipoEstacion")
                  .size().rename("Maestro").reset_index())
    t = t.merge(maestro, on="TipoEstacion", how="left")
    t["Cobertura"] = t["Estaciones"] / t["Maestro"] * 100
    return t


def por_estacion(full: pd.DataFrame) -> pd.DataFrame:
    p = (full.groupby(["IdEstacion", "TipoEstacion",
                       "NombreDpto", "NombreCiudad"])
              .agg(Valor=("ValorVenta", "sum"),
                   Gal=("Gal", "sum"),
                   Tickets=("ValorVenta", "count"),
                   Clientes=("IdCliente", "nunique"),
                   Tkt_prom=("ValorVenta", "mean"),
                   Pct_fid=("cliente_identificado", "mean"))
              .reset_index()
              .sort_values("Valor", ascending=False))
    p["Pct"] = p["Valor"] / p["Valor"].sum() * 100
    p["Pct_acum"] = p["Pct"].cumsum()
    p["Rank"] = range(1, len(p) + 1)
    return p


def imprimir(full: pd.DataFrame, est: pd.DataFrame) -> None:
    tipo = por_tipo(full, est)
    pe = por_estacion(full)

    print("=== POR TIPO DE ESTACION ===")
    print(f"{'Tipo':<20} {'Valor':>15} {'%Val':>6} {'Estac':>6} "
          f"{'Maest':>6} {'Cob%':>6} {'Val/Est':>12} "
          f"{'Tkt':>9} {'%Fid':>6}")
    print("-" * 110)
    for _, r in tipo.iterrows():
        print(f"{r['TipoEstacion']:<20} {r['Valor']:>15,.0f} "
              f"{r['Pct_val']:>5.1f}% {r['Estaciones']:>6} "
              f"{r['Maestro']:>6} {r['Cobertura']:>5.1f}% "
              f"{r['Val_x_est']:>12,.0f} {r['Tkt_prom']:>9,.0f} "
              f"{r['Pct_fid']:>5.1f}%")
    print()

    activas = set(full["IdEstacion"].dropna())
    inactivas = est[~est["IdEstacion"].isin(activas)]
    print(f"Maestro: {len(est)}  Activas: {len(activas)}  "
          f"Inactivas: {len(inactivas)}")
    if len(inactivas) > 0:
        print(f"Inactivas por tipo: {inactivas['TipoEstacion'].value_counts().to_dict()}")
    print()

    print("=== PARETO ESTACIONES ===")
    for u in [50, 80, 90, 95]:
        n = (pe["Pct_acum"] <= u).sum()
        print(f"  Para {u}%: {n} estaciones ({n/len(pe)*100:.1f}%)")
    print()

    print("=== TOP 10 ESTACIONES ===")
    print(f"{'#':>3} {'Id':>6} {'Tipo':<18} {'Dpto':<13} {'Ciudad':<18} "
          f"{'Valor':>13} {'%':>5} {'%Fid':>5}")
    print("-" * 105)
    for _, r in pe.head(10).iterrows():
        print(f"{r['Rank']:>3} {r['IdEstacion']:>6} "
              f"{r['TipoEstacion'][:18]:<18} "
              f"{str(r['NombreDpto'])[:13]:<13} "
              f"{str(r['NombreCiudad'])[:18]:<18} "
              f"{r['Valor']:>13,.0f} {r['Pct']:>4.1f}% "
              f"{r['Pct_fid']*100:>4.1f}%")
    print()

    pct_fid_global = full["cliente_identificado"].mean() * 100
    print(f"% Fidelizacion global: {pct_fid_global:.1f}%")
    print()

    qual = pe[pe["Tickets"] >= MIN_TX_FIDELIZACION].sort_values(
        "Pct_fid", ascending=False)
    print(f"Top 5 fidelizacion (min {MIN_TX_FIDELIZACION} tx):")
    for _, r in qual.head(5).iterrows():
        print(f"  {r['IdEstacion']:>6} {r['TipoEstacion']:<18} "
              f"{str(r['NombreCiudad'])[:20]:<20} "
              f"{r['Pct_fid']*100:>5.1f}%  ({r['Tickets']:,} tx)")
    print()
    print(f"Bottom 5 fidelizacion (min {MIN_TX_FIDELIZACION} tx):")
    for _, r in qual.tail(5).iterrows():
        print(f"  {r['IdEstacion']:>6} {r['TipoEstacion']:<18} "
              f"{str(r['NombreCiudad'])[:20]:<20} "
              f"{r['Pct_fid']*100:>5.1f}%  ({r['Tickets']:,} tx)")


if __name__ == "__main__":
    full, est = cargar_full()
    imprimir(full, est)
