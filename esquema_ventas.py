
"""Esquema común de ventas para ERIDANUS 4.0."""

from pathlib import Path
import polars as pl

# Rutas de almacenamiento
BASE = Path(__file__).resolve().parent

ARCHIVO_PRODUCTOS = BASE / "productos.csv"
ARCHIVO_VENTAS = BASE / "ventas.csv"
ARCHIVO_PARQUET = BASE / "ventas.parquet"

# Esquema obligatorio de ventas
ESQUEMA_VENTAS = {
    "id_venta": pl.Int64,
    "fecha": pl.Datetime("us"),
    "producto": pl.String,
    "precio": pl.Float64,
    "cantidad": pl.Int64,
    "monto_total": pl.Float64,
}

COLUMNAS_VENTAS = list(ESQUEMA_VENTAS.keys())

# Cantidad inicial de ventas simuladas
NUM_VENTAS_HISTORICAS = 2_000_000
