"""
Limpieza y preparación de datos — On Daxelta.
Lee las 5 fuentes originales y genera en /output:
  trans_clean.csv, customers_clean.csv, estaciones_clean.csv,
  geo_clean.csv, reporte_inconsistencias.txt
"""

import sys
import io
import time
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

import pandas as pd
import numpy as np
import os
from datetime import datetime

# ── Motor Excel: fastexcel (Rust+Arrow) > calamine > openpyxl ──
try:
    import fastexcel as _fastexcel  # noqa
    EXCEL_ENGINE = "fastexcel"
except ImportError:
    try:
        import python_calamine  # noqa
        EXCEL_ENGINE = "calamine"
    except ImportError:
        EXCEL_ENGINE = "openpyxl"

def read_excel_fast(path, dtype=None):
    """Lee un Excel usando el motor más rápido disponible."""
    if EXCEL_ENGINE == "fastexcel":
        import fastexcel
        df = fastexcel.read_excel(path).load_sheet(0).to_pandas()
        if dtype:
            for col, t in dtype.items():
                if col in df.columns:
                    try:
                        df[col] = df[col].astype(t)
                    except Exception:
                        pass
        return df
    # calamine u openpyxl: vía pandas
    return pd.read_excel(path, engine=EXCEL_ENGINE, dtype=dtype)

print(f"[motor Excel] {EXCEL_ENGINE}")

# ── Rutas de entrada (ajusta según tu entorno) ─────────────
INPUT_DIR  = "."          # carpeta donde están los archivos originales
OUTPUT_DIR = "./output"   # carpeta de salida
os.makedirs(OUTPUT_DIR, exist_ok=True)

# ── Año de referencia del negocio ──────────────────────────
ANIO_REF = 2017

# ── Registro de inconsistencias ───────────────────────────
log = []

def registrar(archivo, tipo, descripcion, cantidad=None):
    """Agrega una entrada al log de inconsistencias."""
    entrada = {
        "archivo"    : archivo,
        "tipo"       : tipo,          # CRITICO | ADVERTENCIA | INFO
        "descripcion": descripcion,
        "cantidad"   : cantidad,
        "timestamp"  : datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    }
    log.append(entrada)
    icono = {"CRITICO": "❌", "ADVERTENCIA": "⚠️", "INFO": "ℹ️"}.get(tipo, "•")
    cant  = f"  [{cantidad:,} registros]" if cantidad is not None else ""
    print(f"  {icono} [{tipo}] {descripcion}{cant}")


# ══════════════════════════════════════════════════════════
#  1. GEO
# ══════════════════════════════════════════════════════════
print("\n▶ 1/5  Geo.xlsx")
_t = time.time()

geo = read_excel_fast(
    os.path.join(INPUT_DIR, "Geo.xlsx"),
    dtype={"IdCiudad": "Int64", "NombreDpto": str, "NombreCiudad": str},
)

# -- Diagnóstico
n_internacionales = (geo["IdCiudad"] < 0).sum()
registrar("Geo", "ADVERTENCIA",
          "Ciudades con IdCiudad negativo (México, Chile, Perú, Venezuela)",
          n_internacionales)

# -- Limpieza
geo["NombreDpto"]   = geo["NombreDpto"].str.strip()
geo["NombreCiudad"] = geo["NombreCiudad"].str.strip()

# Conservar TODAS las ciudades (Colombia + internacionales) con flag.
# Evita pérdida de relación con ~13k clientes en ciudades internacionales.
# Filtrado por slicer en Power BI (EsInternacional = False) para vista Colombia.
geo["EsInternacional"] = geo["IdCiudad"] < 0
n_colombia      = (~geo["EsInternacional"]).sum()
n_internacional = geo["EsInternacional"].sum()

registrar("Geo", "INFO",
          f"Ciudades Colombia: {n_colombia:,} | Internacionales marcadas: {n_internacional:,}")

geo.to_csv(os.path.join(OUTPUT_DIR, "geo_clean.csv"), index=False, encoding="utf-8-sig")
print(f"   ✔ geo_clean.csv guardado ({len(geo):,} filas)  [{time.time()-_t:.1f}s]")


# ══════════════════════════════════════════════════════════
#  2. ESTACIONES
# ══════════════════════════════════════════════════════════
print("\n▶ 2/5  Estaciones")
_t = time.time()

est = pd.read_csv(
    os.path.join(INPUT_DIR, "Estaciones"),
    sep="£", encoding="latin-1", engine="python",
    dtype={"IdEstacion": "Int64", "IdCiudad": "Int64", "TipoEstacion": str},
)

# -- Diagnóstico
n_id_cero  = (est["IdEstacion"] == 0).sum()
n_tipo_nulo = est["TipoEstacion"].isnull().sum()

registrar("Estaciones", "CRITICO",
          "Registro con IdEstacion = 0 (fila inválida)", n_id_cero)
registrar("Estaciones", "CRITICO",
          "TipoEstacion nulo", n_tipo_nulo)

tipos_raw = est["TipoEstacion"].dropna().unique().tolist()
registrar("Estaciones", "ADVERTENCIA",
          f"Valores sucios en TipoEstacion antes de normalizar: {tipos_raw}")

# -- Limpieza
# Eliminar fila con ID = 0
est = est[est["IdEstacion"] != 0].copy()

# Normalizar TipoEstacion: strip + lower para mapear
est["TipoEstacion"] = est["TipoEstacion"].str.strip().str.replace(r"\s+", " ", regex=True)

mapa_tipo = {
    # Propia GNV
    "Propia GNV"                  : "Propia GNV",
    # Operadora
    "Operadora"                   : "Operadora",
    # Franquiciada (todas las variantes)
    "Franquiciada GNV"            : "Franquiciada GNV",
    "Franquiciada Banderazo GNV"  : "Franquiciada GNV",   # Banderazo = subtipo
    "anquiciada GNV"              : "Franquiciada GNV",   # typo: falta 'Fr'
}
est["TipoEstacion"] = est["TipoEstacion"].map(
    lambda x: mapa_tipo.get(x, x) if pd.notna(x) else "Sin Clasificar"
)

# Rellenar nulos restantes
n_sin_tipo = (est["TipoEstacion"] == "Sin Clasificar").sum()
if n_sin_tipo > 0:
    registrar("Estaciones", "ADVERTENCIA",
              "Registros sin TipoEstacion después de normalizar", n_sin_tipo)

registrar("Estaciones", "INFO",
          f"Tipos finales: {est['TipoEstacion'].value_counts().to_dict()}")

est.to_csv(os.path.join(OUTPUT_DIR, "estaciones_clean.csv"), index=False, encoding="utf-8-sig")
print(f"   ✔ estaciones_clean.csv guardado ({len(est):,} filas)  [{time.time()-_t:.1f}s]")


# ══════════════════════════════════════════════════════════
#  3. CUSTOMERS
# ══════════════════════════════════════════════════════════
print("\n▶ 3/5  Customers.xlsx")
_t = time.time()

# calamine (Rust) es 10-100x más rápido que openpyxl para archivos grandes.
# dtype=str en la lectura evita type-inference por fila; conversiones se hacen
# vectorialmente después — significativamente más rápido en 800k filas.
cust = read_excel_fast(os.path.join(INPUT_DIR, "Customers.xlsx"))

n_total_cust = len(cust)
print(f"   Archivo leído ({n_total_cust:,} filas)  [{time.time()-_t:.1f}s]")

# -- Conversiones de tipo (vectoriales, mucho más rápidas que cell-by-cell en Excel)
cust["IdCliente"]  = pd.to_numeric(cust["IdCliente"],  errors="coerce").astype("Int64")
cust["IdCiudad"]   = pd.to_numeric(cust["IdCiudad"],   errors="coerce").astype("Int64")

# -- Diagnóstico FechaNacimiento
cust["FechaNacimiento"] = pd.to_datetime(cust["FechaNacimiento"], errors="coerce")
n_fecha_nula  = cust["FechaNacimiento"].isnull().sum()
cust["_edad"] = ANIO_REF - cust["FechaNacimiento"].dt.year
n_menores_16  = (cust["_edad"] < 16).sum()
n_mayores_100 = (cust["_edad"] > 100).sum()
n_entre_91_100 = ((cust["_edad"] >= 91) & (cust["_edad"] <= 100)).sum()
n_fecha_futura = (cust["FechaNacimiento"].dt.year > ANIO_REF).sum()

registrar("Customers", "CRITICO",
          "FechaNacimiento nula", n_fecha_nula)
registrar("Customers", "CRITICO",
          f"Nacidos después de {ANIO_REF} (imposible)", n_fecha_futura)
registrar("Customers", "ADVERTENCIA",
          "Edad calculada < 16 años (no deberían ser titulares)", n_menores_16)
registrar("Customers", "ADVERTENCIA",
          "Edad calculada > 100 años (probablemente error de captura)", n_mayores_100)
registrar("Customers", "INFO",
          "Edad calculada 91-100 años (adultos mayores — se conservan como confiables)", n_entre_91_100)

# -- Diagnóstico Segmento (NaN técnico vs "Sin Segmento" literal en fuente)
n_seg_nulo = cust["Segmento"].isnull().sum()
_seg_strip = cust["Segmento"].astype("string").str.strip()
n_seg_literal_sin = (_seg_strip == "Sin Segmento").sum()
n_seg_total_sin   = n_seg_nulo + n_seg_literal_sin
pct_seg_sin      = n_seg_total_sin / n_total_cust * 100

registrar("Customers", "ADVERTENCIA",
          "Segmento NaN (nulo técnico)", n_seg_nulo)
registrar("Customers", "ADVERTENCIA",
          f"Segmento 'Sin Segmento' literal en fuente ({pct_seg_sin:.1f}% sin clasificar real)",
          n_seg_literal_sin)

# -- Limpieza
# Normalizar Segmento: strip de espacios + nulos a "Sin Segmento"
cust["Segmento"] = _seg_strip.fillna("Sin Segmento")

# Marcar filas con FechaNacimiento no confiable (para análisis de edad)
# NO se eliminan — se marcan para uso correcto en segmentación demográfica
cust["FechaNac_confiable"] = (
    cust["FechaNacimiento"].notna() &
    (cust["_edad"] >= 16) &
    (cust["_edad"] <= 100)
)
n_no_confiable = (~cust["FechaNac_confiable"]).sum()
registrar("Customers", "INFO",
          f"FechaNacimiento NO confiable (marcada, no eliminada): {n_no_confiable:,} "
          f"({n_no_confiable/n_total_cust*100:.1f}%)")

# Calcular edad solo donde es confiable.
# Int64 (nullable) escribe enteros sin decimales en CSV: "45" no "45.0".
# Evita que Power BI con locale es-CO interprete el punto como miles y lea 45.0 → 450.
cust["Edad"] = cust["_edad"].where(cust["FechaNac_confiable"]).astype("Int64")

# Limpiar columnas auxiliares
cust.drop(columns=["_edad"], inplace=True)

# Deduplicar por IdCliente (keeper=first para conservar primera aparición)
n_antes = len(cust)
cust = cust.drop_duplicates(subset=["IdCliente"], keep="first")
n_dupes_cust = n_antes - len(cust)
if n_dupes_cust:
    registrar("Customers", "ADVERTENCIA",
              f"Filas duplicadas eliminadas (mismo IdCliente): {n_dupes_cust:,}")

registrar("Customers", "INFO",
          f"Distribución segmentos: {cust['Segmento'].value_counts().to_dict()}")

cust.to_csv(os.path.join(OUTPUT_DIR, "customers_clean.csv"), index=False, encoding="utf-8-sig")

# ── Validación: confirmar que no quedaron edades imposibles ──
edad_max = cust["Edad"].max()
edad_min = cust["Edad"].min()
n_edad_invalida = (cust["Edad"] > 100).sum()
print(f"   ✔ customers_clean.csv guardado ({len(cust):,} filas)  [{time.time()-_t:.1f}s]")
print(f"   ✔ Edad — min: {edad_min:.0f}  max: {edad_max:.0f}  valores > 100: {n_edad_invalida}")


# ══════════════════════════════════════════════════════════
#  4. TRANSACCIONES — Carga y corrección individual
# ══════════════════════════════════════════════════════════
print("\n▶ 4/5  Transacciones (Trans_Sem + Trans_2_Sem)")
_t = time.time()

# dtype=str evita inferencia fila-a-fila; conversiones vectoriales después.
# engine omitido → pandas usa C engine (10-20x más rápido que python engine).
# § es 0xA7 en latin-1 = 1 byte → compatible con C engine.
_TRANS_DTYPE = {
    "Placa": str, "IdCliente": str, "IdEstacion": str,
    "ValorVenta": str, "Gal_Fid": str, "Gal": str, "FechaVenta": str,
}

# ── 4a. Trans_Sem ──────────────────────────────────────────
print("   Cargando Trans_Sem...")
t1 = pd.read_csv(
    os.path.join(INPUT_DIR, "Trans_Sem"),
    sep="§", encoding="latin-1", engine="python", dtype=_TRANS_DTYPE,
)
# Columnas correctas: Placa§IdCliente§IdEstacion§ValorVenta§Gal_Fid§Gal§FechaVenta
t1["_fuente"] = "Trans_Sem"

# ── 4b. Trans_2_Sem ────────────────────────────────────────
print("   Cargando Trans_2_Sem...")
t2 = pd.read_csv(
    os.path.join(INPUT_DIR, "Trans_2_Sem"),
    sep="§", encoding="latin-1", engine="python", dtype=_TRANS_DTYPE,
)
# INCONSISTENCIA DOCUMENTADA: el header está desplazado respecto a los datos.
# Los datos reales están en orden: Placa, IdCliente, IdEstacion, ValorVenta, Gal_Fid, Gal, FechaVenta
# El header original dice: FechaVenta, Placa, IdCliente, IdEstacion, ValorVenta, Gal_Fid, Gal
# Se reasignan los nombres correctos según el contenido real.
registrar("Trans_2_Sem", "CRITICO",
          "Header del archivo desplazado: columnas renombradas según contenido real")

t2.columns = ["Placa", "IdCliente", "IdEstacion", "ValorVenta", "Gal_Fid", "Gal", "FechaVenta"]
t2["_fuente"] = "Trans_2_Sem"

# ── 4c. Unificar ───────────────────────────────────────────
trans = pd.concat([t1, t2], ignore_index=True)
n_antes_dedup = len(trans)

registrar("Transacciones", "INFO",
          f"Registros antes de deduplicar: {n_antes_dedup:,} "
          f"(Trans_Sem: {len(t1):,} | Trans_2_Sem: {len(t2):,})")

# ── 4d. Tipos de datos ─────────────────────────────────────
trans["FechaVenta"] = pd.to_datetime(trans["FechaVenta"], errors="coerce", format="mixed")
trans["ValorVenta"] = pd.to_numeric(trans["ValorVenta"], errors="coerce")
trans["Gal"]        = pd.to_numeric(trans["Gal"],        errors="coerce")
trans["Gal_Fid"]    = pd.to_numeric(trans["Gal_Fid"],    errors="coerce")
trans["IdCliente"]  = pd.to_numeric(trans["IdCliente"],  errors="coerce").astype("Int64")
trans["IdEstacion"] = pd.to_numeric(trans["IdEstacion"], errors="coerce").astype("Int64")
trans["Placa"]      = trans["Placa"].str.strip()

# ── 4e. Deduplicación ──────────────────────────────────────
# Clave natural: Placa + IdCliente + IdEstacion + FechaVenta + ValorVenta
clave_dup = ["Placa", "IdCliente", "IdEstacion", "FechaVenta", "ValorVenta"]
trans_dedup = trans.drop_duplicates(subset=clave_dup, keep="first").copy()
n_duplicados = n_antes_dedup - len(trans_dedup)

registrar("Transacciones", "ADVERTENCIA",
          "Registros duplicados exactos eliminados", n_duplicados)

trans = trans_dedup.reset_index(drop=True)

# ── 4f. Diagnóstico y limpieza por campo ───────────────────

# FechaVenta
n_fecha_nula_tx = trans["FechaVenta"].isnull().sum()
if n_fecha_nula_tx > 0:
    registrar("Transacciones", "CRITICO",
              "FechaVenta nula — se eliminan", n_fecha_nula_tx)
    trans = trans[trans["FechaVenta"].notna()].copy()

# Clientes sin identificar
n_sin_cliente = (trans["IdCliente"] == -99999).sum()
registrar("Transacciones", "ADVERTENCIA",
          f"Transacciones sin cliente identificado (IdCliente=-99999): "
          f"{n_sin_cliente:,} ({n_sin_cliente/len(trans)*100:.1f}%) — "
          "Se conservan, se marca la columna", n_sin_cliente)
trans["cliente_identificado"] = trans["IdCliente"] != -99999

# ValorVenta
n_valor_cero = (trans["ValorVenta"] <= 0).sum()
if n_valor_cero > 0:
    registrar("Transacciones", "CRITICO",
              "ValorVenta <= 0 — se eliminan", n_valor_cero)
    trans = trans[trans["ValorVenta"] > 0].copy()

# Gal
n_gal_cero = (trans["Gal"] <= 0).sum()
if n_gal_cero > 0:
    registrar("Transacciones", "ADVERTENCIA",
              "Gal <= 0 — se eliminan", n_gal_cero)
    trans = trans[trans["Gal"] > 0].copy()

# Outliers: ValorVenta y Gal (método IQR + p99)
# Se marcan, no se eliminan (pueden ser vehículos de carga pesada legítimos)
p99_valor = trans["ValorVenta"].quantile(0.99)
p99_gal   = trans["Gal"].quantile(0.99)

trans["outlier_valor"] = trans["ValorVenta"] > p99_valor
trans["outlier_gal"]   = trans["Gal"]        > p99_gal

n_out_valor = trans["outlier_valor"].sum()
n_out_gal   = trans["outlier_gal"].sum()

registrar("Transacciones", "INFO",
          f"Outliers ValorVenta > p99 (${p99_valor:,.0f}) marcados: {n_out_valor:,}")
registrar("Transacciones", "INFO",
          f"Outliers Gal > p99 ({p99_gal:.2f} gal) marcados: {n_out_gal:,}")

# Clientes en transacciones no presentes en Customers
cust_ids = set(cust["IdCliente"].unique())
trans_ids = set(trans[trans["IdCliente"] != -99999]["IdCliente"].dropna().unique())
ids_sin_match = trans_ids - cust_ids
registrar("Transacciones", "ADVERTENCIA",
          f"Clientes en transacciones sin registro en Customers: {len(ids_sin_match):,}")

# ── 4g. Enriquecimiento temporal ───────────────────────────
trans["DiaSemana"]     = trans["FechaVenta"].dt.day_name()
trans["NumeroDia"]     = trans["FechaVenta"].dt.dayofweek   # 0=Lun … 6=Dom
trans["Semana"]        = trans["FechaVenta"].dt.isocalendar().week.astype(int)
trans["Mes"]           = trans["FechaVenta"].dt.month
trans["Anio"]          = trans["FechaVenta"].dt.year

# Mapa español para legibilidad en Power BI
mapa_dias = {
    "Monday": "Lunes", "Tuesday": "Martes", "Wednesday": "Miércoles",
    "Thursday": "Jueves", "Friday": "Viernes", "Saturday": "Sábado", "Sunday": "Domingo"
}
trans["DiaSemana_ES"] = trans["DiaSemana"].map(mapa_dias)

# ── 4h. Precio por galón (métrica calculada) ───────────────
trans["PrecioXGalon"] = trans["ValorVenta"] / trans["Gal"]

registrar("Transacciones", "INFO",
          f"Registros finales limpios: {len(trans):,}")

trans.to_csv(os.path.join(OUTPUT_DIR, "trans_clean.csv"), index=False, encoding="utf-8-sig")
print(f"   ✔ trans_clean.csv guardado ({len(trans):,} filas)  [{time.time()-_t:.1f}s]")


# ══════════════════════════════════════════════════════════
#  5. VALIDACIÓN CRUZADA (integridad referencial)
# ══════════════════════════════════════════════════════════
print("\n▶ 5/5  Validación cruzada")

# Estaciones en transacciones vs maestro
est_ids  = set(est["IdEstacion"].unique())
tx_est   = set(trans["IdEstacion"].dropna().unique())
est_huerfanas = tx_est - est_ids
registrar("Validación", "INFO" if not est_huerfanas else "ADVERTENCIA",
          f"Estaciones en tx sin maestro: {len(est_huerfanas):,}")

# Ciudades de clientes vs Geo completo (Col + Internacional)
geo_ids        = set(geo["IdCiudad"].unique())
cust_city_ids  = set(cust["IdCiudad"].dropna().unique())
ciudades_sin_geo = cust_city_ids - geo_ids
registrar("Validación", "ADVERTENCIA",
          f"IdCiudad en Customers sin match en Geo (Col+Intl): {len(ciudades_sin_geo):,}",
          len(ciudades_sin_geo))

# Ciudades de estaciones vs Geo
est_city_ids  = set(est["IdCiudad"].dropna().unique())
est_sin_geo   = est_city_ids - geo_ids
registrar("Validación", "INFO",
          f"IdCiudad en Estaciones sin match en Geo: {len(est_sin_geo):,}")


# ══════════════════════════════════════════════════════════
#  6. REPORTE DE INCONSISTENCIAS
# ══════════════════════════════════════════════════════════
print("\n▶ Generando reporte_inconsistencias.txt...")

reporte_path = os.path.join(OUTPUT_DIR, "reporte_inconsistencias.txt")
sep = "=" * 65

with open(reporte_path, "w", encoding="utf-8") as f:
    f.write(f"{sep}\n")
    f.write("  REPORTE DE INCONSISTENCIAS — On Daxelta\n")
    f.write(f"  Generado: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
    f.write(f"{sep}\n\n")

    archivos = sorted(set(e["archivo"] for e in log))
    for archivo in archivos:
        f.write(f"\n{'─'*65}\n")
        f.write(f"  ARCHIVO: {archivo}\n")
        f.write(f"{'─'*65}\n")
        for e in log:
            if e["archivo"] != archivo:
                continue
            cant = f"  → {e['cantidad']:,} registros" if e["cantidad"] is not None else ""
            f.write(f"\n  [{e['tipo']}]\n")
            f.write(f"  {e['descripcion']}{cant}\n")

    f.write(f"\n\n{sep}\n")
    f.write("  RESUMEN\n")
    f.write(f"{sep}\n")

    criticos     = [e for e in log if e["tipo"] == "CRITICO"]
    advertencias = [e for e in log if e["tipo"] == "ADVERTENCIA"]
    infos        = [e for e in log if e["tipo"] == "INFO"]

    f.write(f"\n  ❌ Críticos     : {len(criticos)}\n")
    f.write(f"  ⚠️  Advertencias : {len(advertencias)}\n")
    f.write(f"  ℹ️  Informativos : {len(infos)}\n")

    f.write(f"\n\n{sep}\n")
    f.write("  RECOMENDACIONES DE ESTANDARIZACIÓN\n")
    f.write(f"{sep}\n")
    recomendaciones = [
        "1. Definir un esquema de validación en origen para FechaNacimiento.",
        "   Rechazar fechas futuras o edades < 16 o > 100 (FechaNac_confiable=False).",
        "",
        "2. Corregir el header de Trans_2_Sem en el sistema fuente.",
        "   El orden correcto de columnas es:",
        "   Placa | IdCliente | IdEstacion | ValorVenta | Gal_Fid | Gal | FechaVenta",
        "",
        "3. Estandarizar TipoEstacion con lista de valores controlada:",
        "   Valores permitidos: Propia GNV | Franquiciada GNV | Operadora",
        "",
        "4. Implementar un programa de captura para el 18-19% de transacciones",
        "   sin IdCliente (-99999). Representan ~$8M en ventas no atribuidas.",
        "",
        "5. Resolver los 2.055 clientes activos sin ficha en Customers.",
        "   Probable carga tardía de datos maestros.",
        "",
        "6. Registros internacionales (IdCiudad < 0): conservados en geo_clean",
        "   con flag EsInternacional para filtrado por slicer en Power BI.",
        "   Evita pérdida de relación con ~13k clientes asociados.",
        "",
        "7. Auditar outliers de ValorVenta (> $34.352 p99) y Gal (> 22 gal p99).",
        "   Pueden ser vehículos de carga pesada legítimos o errores de captura.",
        "",
        "8. Segmento Customers: eliminar la categoría literal 'Sin Segmento'",
        "   del dominio. Debe ser un nulo enrutado a flujo de asignación,",
        "   no una opción válida (afecta ~20% de la base).",
    ]
    for r in recomendaciones:
        f.write(f"  {r}\n")

print(f"   ✔ reporte_inconsistencias.txt guardado")


# ══════════════════════════════════════════════════════════
#  RESUMEN FINAL EN CONSOLA
# ══════════════════════════════════════════════════════════
criticos     = sum(1 for e in log if e["tipo"] == "CRITICO")
advertencias = sum(1 for e in log if e["tipo"] == "ADVERTENCIA")

print(f"""
{'='*55}
  ✅  LIMPIEZA COMPLETADA
{'='*55}
  Archivos generados en: {OUTPUT_DIR}/
    • trans_clean.csv
    • customers_clean.csv
    • estaciones_clean.csv
    • geo_clean.csv
    • reporte_inconsistencias.txt

  Resumen de hallazgos:
    ❌ Críticos      : {criticos}
    ⚠️  Advertencias : {advertencias}
{'='*55}
""")
