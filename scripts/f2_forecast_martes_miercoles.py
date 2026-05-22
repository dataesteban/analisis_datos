"""
============================================================
  F2 - Pronostico Valor Venta martes y miercoles siguientes
  Proposito: cifras + banda para hallazgos/02_forecast.md
  Python   : 3.9+
  Deps     : pandas
  Entrada  : output/trans_clean.csv
============================================================
EJECUCION:
    python scripts/f2_forecast_martes_miercoles.py

METODO:
  Naive estacional: pronostico = valor observado mismo dia semana anterior.
  Banda: +/- CV (coeficiente variacion) de los 7 dias observados.
============================================================
"""

import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

import pandas as pd


def cargar(ruta: str) -> pd.DataFrame:
    return pd.read_csv(
        ruta,
        usecols=["FechaVenta", "DiaSemana_ES", "NumeroDia",
                 "Gal", "ValorVenta"],
        parse_dates=["FechaVenta"],
    )


def resumen_diario(tx: pd.DataFrame) -> pd.DataFrame:
    """Agrega por día calendario."""
    return (tx.groupby([tx["FechaVenta"].dt.date,
                        "NumeroDia", "DiaSemana_ES"])
              .agg(Valor=("ValorVenta", "sum"),
                   Gal=("Gal", "sum"),
                   Tickets=("ValorVenta", "count"))
              .reset_index()
              .rename(columns={"FechaVenta": "Fecha"}))


def proxima_fecha_dia(ultimo: pd.Timestamp, dia_objetivo: int) -> pd.Timestamp:
    """Devuelve la siguiente fecha cuyo weekday == dia_objetivo (0=Lun)."""
    delta = (dia_objetivo - ultimo.weekday()) % 7
    return ultimo + pd.Timedelta(days=delta if delta > 0 else 7)


def estadisticos(diario: pd.DataFrame, col: str) -> dict:
    media = diario[col].mean()
    std = diario[col].std()
    return {"media": media, "std": std, "cv": std / media}


def imprimir_forecast(diario: pd.DataFrame) -> None:
    ultimo = pd.to_datetime(diario["Fecha"].max())
    print(f"Ultimo dia observado: {ultimo.date()} "
          f"({diario.iloc[-1]['DiaSemana_ES']})")
    print()

    e_val = estadisticos(diario, "Valor")
    e_gal = estadisticos(diario, "Gal")
    print(f"Valor: media=${e_val['media']:,.0f}  "
          f"std=${e_val['std']:,.0f}  CV={e_val['cv']*100:.1f}%")
    print(f"Gal  : media={e_gal['media']:,.0f}  "
          f"std={e_gal['std']:,.0f}  CV={e_gal['cv']*100:.1f}%")
    print()

    prox_mar = proxima_fecha_dia(ultimo, 1)
    prox_mie = prox_mar + pd.Timedelta(days=1)

    mar = diario[diario["NumeroDia"] == 1].iloc[0]
    mie = diario[diario["NumeroDia"] == 2].iloc[0]

    for label, fecha, obs_val, obs_gal in [
        ("Martes",    prox_mar.date(), mar["Valor"], mar["Gal"]),
        ("Miercoles", prox_mie.date(), mie["Valor"], mie["Gal"]),
    ]:
        print(f"{label} {fecha}:")
        print(f"  Valor: ${obs_val*(1-e_val['cv']):>15,.0f}  --  "
              f"${obs_val:>15,.0f}  --  "
              f"${obs_val*(1+e_val['cv']):>15,.0f}")
        print(f"  Gal  : {obs_gal*(1-e_gal['cv']):>15,.0f}  --  "
              f"{obs_gal:>15,.0f}  --  "
              f"{obs_gal*(1+e_gal['cv']):>15,.0f}")


if __name__ == "__main__":
    tx = cargar("output/trans_clean.csv")
    diario = resumen_diario(tx)
    imprimir_forecast(diario)
