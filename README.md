# Prueba Analista de Datos — On Daxelta

Análisis del negocio de gas vehicular On Daxelta a partir de las bases `Customers`, `Estaciones`, `Geo`, `Trans_Sem` y `Trans_2_Sem`. Limpieza en Python, bases sólidas en CSV, dashboard interactivo en Power BI con segmentación RFM y análisis demográfico.

**Ventana de datos:** 7 días (24–30 jul 2017)  
**Estado:** ✅ completado — 6 puntos de la prueba + dashboard Power BI + documentación

---

## Quickstart

### Requisitos

```bash
pip install pandas numpy openpyxl fastexcel pyarrow
```

### Ejecutar limpieza

```bash
python limpieza_ondaxelta.py
```

Genera `output/*.csv` y `output/reporte_inconsistencias.txt`.

### Power BI

1. Abrir `VisualP.pbip` en Power BI Desktop
2. Inicio → **Actualizar**
3. Navegar entre las dos páginas del dashboard

---

## Estructura del proyecto

```
analisis_datos/
│
├── VisualP.pbip                 ← dashboard Power BI (abrir aquí)
│
├── limpieza_ondaxelta.py        ← script de limpieza y preparación de datos
│
├── (fuentes originales)
│   ├── Customers.xlsx
│   ├── Estaciones               (CSV separador £, latin-1)
│   ├── Geo.xlsx
│   ├── Trans_Sem                (CSV separador §, latin-1)
│   └── Trans_2_Sem              (header desplazado — corregido en script)
│
├── hallazgos/                   ← análisis por punto de la prueba
│   ├── 01_volumetria.md
│   ├── 02_forecast.md
│   ├── 03_regional.md
│   ├── 04_estaciones.md
│   ├── 05_rfm.md
│   └── 06_top_clientes.md
│
├── HALLAZGOS.md                 ← calidad de datos + cardinalidades
└── RECOMENDACIONES.md           ← estandarización + reporte ejecutivo
```

---

## Dashboard Power BI

El archivo `VisualP.pbip` contiene dos páginas:

**Dashboard General** — visión operativa del negocio
- 6 KPIs: valor venta, galones, tickets, clientes únicos, fidelización, ticket promedio
- Combo chart: volumen diario vs valor (tendencia semanal)
- Distribución por tipo de estación y segmento RFM
- Tabla resumen por segmento con valor promedio cliente

**Demografía — Edades** — perfil demográfico de la base
- KPIs: edad promedio, % fecha nacimiento confiable, clientes con edad válida
- Edad promedio por segmento RFM
- Edad promedio por tipo de cliente (flota vs particular)
- Distribución de confiabilidad de datos demográficos

---

## Hallazgos por punto de la prueba

| # | Punto | Documento |
|--:|-------|-----------|
| 1 | Volumetría galonaje por día semana | [`hallazgos/01_volumetria.md`](hallazgos/01_volumetria.md) |
| 2 | Pronóstico valor venta martes/miércoles | [`hallazgos/02_forecast.md`](hallazgos/02_forecast.md) |
| 3 | Comportamiento por regional | [`hallazgos/03_regional.md`](hallazgos/03_regional.md) |
| 4 | Comportamiento por estación | [`hallazgos/04_estaciones.md`](hallazgos/04_estaciones.md) |
| 5 | Segmentación de clientes (RFM) | [`hallazgos/05_rfm.md`](hallazgos/05_rfm.md) |
| 6 | Clientes de mayor valor | [`hallazgos/06_top_clientes.md`](hallazgos/06_top_clientes.md) |

---

## Cifras clave

| Métrica | Valor |
|---------|------:|
| Valor venta total semana | **$8.186M COP** |
| Galones totales | 5.440k gal |
| Transacciones limpias | 735.273 |
| Clientes únicos con compras | 99.753 (12,4% del maestro) |
| Estaciones activas | 279 de 407 |
| Departamentos top 80% valor | **7 de 19** |
| Top 1% clientes son flotas | **63%** |
| Pico semanal | Viernes (15,4% galones) |
| Tx sin atribución | 18,7% ($1.388M no asignados) |

---

## Inconsistencias detectadas

- **5 críticos**: header desplazado en Trans_2_Sem, IdEstacion=0, TipoEstacion nulo, FechaNac nula, nacidos después de 2017
- **13 advertencias**: 40% FechaNac no confiable, 1.421 clientes duplicados, 20% sin segmento real, 51% Propias inactivas, entre otros

Detalle completo en [`RECOMENDACIONES.md`](RECOMENDACIONES.md) y `output/reporte_inconsistencias.txt`.

---

## Stack tecnológico

| Capa | Herramienta |
|------|-------------|
| Preparación | Python 3.9+, pandas, numpy, fastexcel, pyarrow |
| Visualización | Power BI Desktop (formato PBIP) + DAX |
| Documentación | Markdown |
| Versionado | Git |

---

## Cumplimiento de la prueba

| Requerimiento | Entregable |
|--------------|------------|
| 1. Volumetría galonaje día semana | `hallazgos/01_volumetria.md` |
| 2. Pronóstico valor venta mar/mié | `hallazgos/02_forecast.md` |
| 3. Comportamiento regional | `hallazgos/03_regional.md` |
| 4. Comportamiento por estación | `hallazgos/04_estaciones.md` |
| 5. Segmentación clientes + caracterización | `hallazgos/05_rfm.md` |
| 6. Clientes de mayor valor | `hallazgos/06_top_clientes.md` |
| Documente proceso y herramientas | `PROCESO.md` |
| Recomendaciones estandarización + inconsistencias | `RECOMENDACIONES.md` + `output/reporte_inconsistencias.txt` |
| Dashboard interactivo | `VisualP.pbip` |
