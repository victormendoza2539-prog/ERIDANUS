
"""Corte de caja y consolidación histórica de ERIDANUS."""

import asyncio
import logging
import os

from time import perf_counter

import polars as pl

from concurrencia import lock

from esquema_ventas import (
    BASE,
    ARCHIVO_VENTAS,
    ARCHIVO_PARQUET,
    ESQUEMA_VENTAS,
)


logger = logging.getLogger("uvicorn.error")


def consolidar_ventas():

    inicio = perf_counter()

    # 1. Leer las ventas recientes
    recientes = pl.read_csv(
        ARCHIVO_VENTAS,
        schema=ESQUEMA_VENTAS,
        try_parse_dates=True,
    )

    if recientes.is_empty():

        logger.info(
            "[ERIDANUS] Corte de caja: sin ventas pendientes."
        )

        return {
            "ventas_consolidadas": 0,
            "mensaje": "Sin ventas pendientes",
        }

    # 2. Leer el histórico
    historico = pl.read_parquet(ARCHIVO_PARQUET)

    registros_antes = historico.height


    # 3. Validar integridad de identificadores
    if recientes["id_venta"].n_unique() != recientes.height:
        raise ValueError("Existen IDs duplicados en el CSV.")

    if historico["id_venta"].n_unique() != historico.height:
        raise ValueError("Existen IDs duplicados en el Parquet.")

    # 3.1. Identificar registros presentes en ambos archivos
    coincidentes = recientes.join(
        historico.select("id_venta"),
        on="id_venta",
        how="semi",
    )

    # 3.2. Comprobar que las ventas coincidentes sean identicas
    if coincidentes.height > 0:

        originales = historico.join(
            coincidentes.select("id_venta"),
            on="id_venta",
            how="semi",
        )

        if not coincidentes.sort("id_venta").equals(
            originales.sort("id_venta")
        ):
            raise ValueError(
                "Conflicto entre CSV y Parquet. "
                "Se conservan ambos archivos."
            )

        logger.info(
            "[ERIDANUS] %s ventas previamente consolidadas.",
            coincidentes.height,
        )


    # 4. Identificar ventas aún no consolidadas
    pendientes = recientes.join(
        historico.select("id_venta"),
        on="id_venta",
        how="anti",
    )

    # 5. Consolidar el histórico
    if pendientes.height > 0:

        consolidado = pl.concat(
            [historico, pendientes],
            how="vertical",
        )

        # Validar integridad antes de guardar
        if (
            consolidado["id_venta"].n_unique()
            != consolidado.height
        ):
            raise ValueError(
                "Se detectaron identificadores duplicados."
            )

        # Escribir primero en un archivo temporal
        temporal_parquet = BASE / "ventas_temporal.parquet"

        consolidado.write_parquet(
            temporal_parquet,
            compression="zstd",
        )

        # Reemplazar el histórico original
        os.replace(
            temporal_parquet,
            ARCHIVO_PARQUET,
        )

    # 6. Crear un CSV vacío con el esquema correcto
    temporal_csv = BASE / "ventas_temporal.csv"

    pl.DataFrame(
        schema=ESQUEMA_VENTAS
    ).write_csv(temporal_csv)

    # Vaciar CSV únicamente después de consolidar
    os.replace(
        temporal_csv,
        ARCHIVO_VENTAS,
    )

    tiempo = perf_counter() - inicio

    resultado = {
        "ventas_consolidadas": pendientes.height,
        "historico_antes": registros_antes,
        "historico_despues": (
            registros_antes + pendientes.height
        ),
        "ventas_pendientes": 0,
        "tiempo_segundos": round(tiempo, 3),
    }

    logger.info(
        "[ERIDANUS] Corte de caja completado: %s",
        resultado,
    )

    return resultado


async def corte_de_caja():

    async with lock:

        logger.info(
            "[ERIDANUS] Iniciando corte de caja..."
        )

        return await asyncio.to_thread(
            consolidar_ventas
        )
