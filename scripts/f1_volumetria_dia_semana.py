"""
============================================================
  F1 - Volumetria del galonaje por dia de la semana
  Proposito: cifras de orientacion para hallazgos/01_volumetria.md
  Python   : 3.9+
  Deps     : pandas
  Entrada  : output/trans_clean.csv
============================================================
EJECUCION:
    python scripts/f1_volumetria_dia_semana.py
============================================================
"""

import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

import pandas as pd

ORDEN_DIAS = ["Lunes", "Martes", "Miércoles", "Jueves",
              "Viernes", "Sábado", "Domingo"]


def cargar_transacciones(ruta: str) -> pd.DataFrame:
    """Carga columnas mínimas necesarias para volumetría diaria."""
    return pd.read_csv(
        ruta,
        usecols=["FechaVenta", "DiaSemana_ES", "NumeroDia",
                 "Gal", "ValorVenta", "IdCliente"],
        parse_dates=["FechaVenta"],
    )


def volumetria_por_dia(tx: pd.DataFrame) -> pd.DataFrame:
    """Agrega métricas por día de la semana ordenado lunes→domingo."""
    v = (tx.groupby(["NumeroDia", "DiaSemana_ES"])
           .agg(Gal_Total=("Gal", "sum"),
                Valor_Total=("ValorVenta", "sum"),
                Tickets=("ValorVenta", "count"),
                Clientes_Unicos=("IdCliente", "nunique"),
                Gal_Prom_Tx=("Gal", "mean"),
                Ticket_Prom=("ValorVenta", "mean"))
           .reset_index()
           .sort_values("NumeroDia"))

    v["Pct_Gal"] = v["Gal_Total"] / v["Gal_Total"].sum() * 100
    v["Pct_Valor"] = v["Valor_Total"] / v["Valor_Total"].sum() * 100
    return v


def imprimir_resumen(tx: pd.DataFrame, vol: pd.DataFrame) -> None:
    """Imprime ventana de fechas y tabla por día."""
    print(f"Fechas    : {tx['FechaVenta'].min().date()} a "
          f"{tx['FechaVenta'].max().date()}")
    print(f"Dias únicos: {tx['FechaVenta'].dt.date.nunique()}")
    print()

    cabecera = (f"{'Dia':<11} {'Gal':>11} {'%Gal':>6} {'Valor':>14} "
                f"{'%Val':>6} {'Tickets':>8} {'Cli.Un':>8} "
                f"{'Gal/Tx':>7} {'Ticket':>10}")
    print(cabecera)
    print("-" * len(cabecera))

    for _, r in vol.iterrows():
        print(f"{r['DiaSemana_ES']:<11} "
              f"{r['Gal_Total']:>11,.0f} {r['Pct_Gal']:>5.1f}% "
              f"{r['Valor_Total']:>14,.0f} {r['Pct_Valor']:>5.1f}% "
              f"{r['Tickets']:>8,} {r['Clientes_Unicos']:>8,} "
              f"{r['Gal_Prom_Tx']:>7.2f} {r['Ticket_Prom']:>10,.0f}")

    print()
    idx_max = vol["Gal_Total"].idxmax()
    idx_min = vol["Gal_Total"].idxmin()
    brecha = (vol["Gal_Total"].max() / vol["Gal_Total"].min() - 1) * 100
    print(f"Pico : {vol.loc[idx_max, 'DiaSemana_ES']} "
          f"({vol['Gal_Total'].max():,.0f} gal, "
          f"{vol['Pct_Gal'].max():.1f}%)")
    print(f"Valle: {vol.loc[idx_min, 'DiaSemana_ES']} "
          f"({vol['Gal_Total'].min():,.0f} gal, "
          f"{vol['Pct_Gal'].min():.1f}%)")
    print(f"Brecha pico/valle: +{brecha:.1f}%")


if __name__ == "__main__":
    tx = cargar_transacciones("output/trans_clean.csv")
    vol = volumetria_por_dia(tx)
    imprimir_resumen(tx, vol)
