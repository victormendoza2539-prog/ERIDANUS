
"""Generador de ventas históricas simuladas de ERIDANUS 4.0."""

from datetime import datetime
from time import perf_counter

import numpy as np
import polars as pl

from esquema_ventas import (
    ARCHIVO_PRODUCTOS,
    ARCHIVO_PARQUET,
    ESQUEMA_VENTAS,
    NUM_VENTAS_HISTORICAS,
)


def generar_parquet():

    inicio = perf_counter()

    # 1. Evitar sobrescribir un histórico existente
    if ARCHIVO_PARQUET.exists():
        print("ventas.parquet ya existe.")
        print("No se sobrescribirá el histórico.")
        return

    # 2. Leer el catálogo real de ERIDANUS
    catalogo = pl.read_csv(ARCHIVO_PRODUCTOS)

    nombres = catalogo["nombre"].to_numpy()
    precios = catalogo["precio"].to_numpy()

    n = NUM_VENTAS_HISTORICAS

    print(f"Productos disponibles: {len(nombres)}")
    print(f"Generando {n:,} ventas simuladas...")

    # 3. Inicializar el generador aleatorio
    rng = np.random.default_rng(42)

    # 4. Generar identificadores únicos
    ids = np.arange(1, n + 1, dtype=np.int64)

    # 5. Seleccionar productos aleatoriamente
    indices = rng.integers(0, len(nombres), size=n)

    productos = nombres[indices]
    precios_venta = precios[indices]

    # 6. Generar cantidades entre 1 y 5
    cantidades = rng.integers(1, 6, size=n)

    # 7. Generar fechas históricas
    fecha_inicio = np.datetime64("2021-01-01T00:00:00", "s")
    fecha_fin = np.datetime64("2026-01-01T00:00:00", "s")

    segundos = int(
        (fecha_fin - fecha_inicio) / np.timedelta64(1, "s")
    )

    desplazamientos = rng.integers(0, segundos, size=n)

    fechas = (
        fecha_inicio
        + desplazamientos.astype("timedelta64[s]")
    ).astype("datetime64[us]")

    # 8. Calcular el importe de cada venta
    montos = np.round(precios_venta * cantidades, 2)

    # 9. Construir el DataFrame de Polars
    ventas = pl.DataFrame(
        {
            "id_venta": ids,
            "fecha": fechas,
            "producto": productos.tolist(),
            "precio": precios_venta,
            "cantidad": cantidades,
            "monto_total": montos,
        },
        schema=ESQUEMA_VENTAS,
    )

    # 10. Exportar a Parquet comprimido
    ventas.write_parquet(
        ARCHIVO_PARQUET,
        compression="zstd",
    )

    # 11. Mostrar resultados
    tiempo = perf_counter() - inicio
    tamano_mb = ARCHIVO_PARQUET.stat().st_size / (1024 ** 2)

    print("\nGeneración completada correctamente.")
    print(f"Registros: {ventas.height:,}")
    print(f"Columnas: {ventas.width}")
    print(f"Tamaño del archivo: {tamano_mb:.2f} MB")
    print(f"Tiempo de ejecución: {tiempo:.2f} segundos")
    print(f"Archivo: {ARCHIVO_PARQUET.name}")

    print("\nEsquema de datos:")
    print(ventas.schema)

    print("\nPrimeras cinco transacciones:")
    print(ventas.head(5))


if __name__ == "__main__":
    generar_parquet()
