
"""Migración de ventas del Proyecto 3 al Proyecto 4."""

import shutil
import polars as pl

from esquema_ventas import (
    BASE,
    ARCHIVO_VENTAS,
    ARCHIVO_PARQUET,
    ESQUEMA_VENTAS,
    COLUMNAS_VENTAS,
)


def migrar_ventas():

    # 1. Verificar los archivos necesarios
    if not ARCHIVO_VENTAS.exists():
        print("No se encontró ventas.csv.")
        return

    if not ARCHIVO_PARQUET.exists():
        print("No se encontró ventas.parquet.")
        return

    # 2. Leer las ventas anteriores
    ventas = pl.read_csv(ARCHIVO_VENTAS)

    # 3. Evitar una segunda migración
    if ventas.columns == COLUMNAS_VENTAS:
        print("ventas.csv ya tiene el esquema correcto.")
        return

    columnas_anteriores = [
        "fecha",
        "producto_id",
        "producto",
        "precio",
        "cantidad",
        "total",
    ]

    if ventas.columns != columnas_anteriores:
        raise ValueError("El esquema original no es el esperado.")

    # 4. Consultar el último ID del histórico
    ultimo_id = (
        pl.scan_parquet(ARCHIVO_PARQUET)
        .select(pl.col("id_venta").max())
        .collect()
        .item()
    )

    # 5. Adaptar las columnas al nuevo esquema
    ventas_nuevas = (
        ventas
        .with_columns(
            pl.int_range(
                ultimo_id + 1,
                ultimo_id + 1 + ventas.height,
                dtype=pl.Int64,
            ).alias("id_venta"),

            pl.col("fecha")
            .str.to_datetime(time_unit="us"),

            pl.col("total").alias("monto_total"),
        )
        .select(COLUMNAS_VENTAS)
        .cast(ESQUEMA_VENTAS)
    )

    # 6. Crear una copia de seguridad
    respaldo = BASE / "ventas_proyecto3.csv"

    if not respaldo.exists():
        shutil.copy2(ARCHIVO_VENTAS, respaldo)

    # 7. Guardar el CSV migrado
    temporal = BASE / "ventas_migracion.tmp"

    ventas_nuevas.write_csv(
        temporal,
        datetime_format="%Y-%m-%dT%H:%M:%S",
    )

    temporal.replace(ARCHIVO_VENTAS)

    # 8. Mostrar resultados
    print("Migración completada correctamente.")
    print(f"Ventas conservadas: {ventas_nuevas.height}")
    print(f"Respaldo: {respaldo.name}")

    print("\nNuevo esquema:")
    print(ventas_nuevas.schema)

    print("\nVentas migradas:")
    print(ventas_nuevas)


if __name__ == "__main__":
    migrar_ventas()
