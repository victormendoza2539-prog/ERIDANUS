
"""Observatorio de ERIDANUS — Analítica con Polars."""

import asyncio
import polars as pl

from fastapi import APIRouter

from concurrencia import lock

from esquema_ventas import (
    ARCHIVO_PRODUCTOS,
    ARCHIVO_VENTAS,
    ARCHIVO_PARQUET,
    ESQUEMA_VENTAS,
)

router = APIRouter(tags=["Observatorio — Polars"])


# ==========================================
# 1. UNION VIRTUAL DE VENTAS
# ==========================================


def cargar_ventas():

    # Ventas históricas
    if ARCHIVO_PARQUET.exists():
        historico = pl.scan_parquet(ARCHIVO_PARQUET)
    else:
        historico = pl.DataFrame(
            schema=ESQUEMA_VENTAS
        ).lazy()

    # Ventas recientes
    if ARCHIVO_VENTAS.exists():
        recientes = pl.scan_csv(
            ARCHIVO_VENTAS,
            schema=ESQUEMA_VENTAS,
            try_parse_dates=True,
        )
    else:
        recientes = pl.DataFrame(
            schema=ESQUEMA_VENTAS
        ).lazy()

    # Excluir ventas previamente consolidadas
    pendientes = recientes.join(
        historico.select("id_venta"),
        on="id_venta",
        how="anti",
    )

    # Unión virtual protegida contra solapamientos
    return pl.concat(
        [historico, pendientes],
        how="vertical",
    )


# ==========================================
# 2. CATALOGO DE PRODUCTOS
# ==========================================

def catalogo_actual():

    return (
        pl.scan_csv(ARCHIVO_PRODUCTOS)
        .select(
            pl.col("id").alias("producto_id"),
            pl.col("nombre").alias("producto"),
            pl.col("categoria"),
        )
        .unique(subset=["producto"], keep="first")
    )


# ==========================================
# 3. INDICADORES KPI
# ==========================================

def calcular_resumen():

    ventas = cargar_ventas()

    indicadores = (
        ventas
        .select(
            pl.col("monto_total")
            .sum()
            .alias("ingresos_totales"),

            pl.len()
            .alias("transacciones"),

            pl.col("cantidad")
            .sum()
            .alias("unidades_vendidas"),

            pl.col("monto_total")
            .mean()
            .alias("ticket_promedio"),
        )
        .collect()
        .to_dicts()[0]
    )

    lider = (
        ventas
        .group_by("producto")
        .agg(
            pl.col("cantidad")
            .sum()
            .alias("unidades")
        )
        .sort(
            ["unidades", "producto"],
            descending=[True, False],
        )
        .head(1)
        .join(
            catalogo_actual(),
            on="producto",
            how="left",
        )
        .collect()
    )

    producto_mas_vendido = None

    if lider.height > 0:

        fila = lider.to_dicts()[0]

        producto_mas_vendido = {
            "id": fila["producto_id"],
            "nombre": fila["producto"],
            "unidades": fila["unidades"],
        }

    return {
        "ingresos_totales": round(
            indicadores["ingresos_totales"] or 0, 2
        ),
        "transacciones": indicadores["transacciones"],
        "unidades_vendidas": (
            indicadores["unidades_vendidas"] or 0
        ),
        "ticket_promedio": round(
            indicadores["ticket_promedio"] or 0, 2
        ),
        "producto_mas_vendido": producto_mas_vendido,
    }


@router.get("/analitica/resumen")
@router.get("/api/analisis/kpis")
async def resumen():

    async with lock:
        return await asyncio.to_thread(calcular_resumen)


# ==========================================
# 4. VENTAS POR PRODUCTO
# ==========================================

def calcular_ventas_por_producto():

    return (
        cargar_ventas()
        .group_by("producto")
        .agg(
            pl.col("cantidad")
            .sum()
            .alias("unidades_vendidas"),

            pl.col("monto_total")
            .sum()
            .round(2)
            .alias("ingresos"),

            pl.len()
            .alias("transacciones"),
        )
        .join(
            catalogo_actual(),
            on="producto",
            how="left",
        )
        .select(
            "producto_id",
            "producto",
            "unidades_vendidas",
            "ingresos",
            "transacciones",
        )
        .sort("ingresos", descending=True)
        .collect()
        .to_dicts()
    )


@router.get("/analitica/por-producto")
async def ventas_por_producto():

    async with lock:
        return await asyncio.to_thread(
            calcular_ventas_por_producto
        )


@router.get("/api/analisis/mas-vendidos")
async def mas_vendidos():

    async with lock:

        resultados = await asyncio.to_thread(
            calcular_ventas_por_producto
        )

        return sorted(
            resultados,
            key=lambda fila: (
                -fila["unidades_vendidas"],
                fila["producto"],
            ),
        )


# ==========================================
# 5. VENTAS POR CATEGORIA
# ==========================================

def calcular_ventas_por_categoria():

    return (
        cargar_ventas()
        .join(
            catalogo_actual(),
            on="producto",
            how="left",
        )
        .with_columns(
            pl.col("categoria")
            .fill_null("Sin categoría")
        )
        .group_by("categoria")
        .agg(
            pl.col("cantidad")
            .sum()
            .alias("unidades_vendidas"),

            pl.col("monto_total")
            .sum()
            .round(2)
            .alias("ingresos"),

            pl.len()
            .alias("transacciones"),
        )
        .sort("ingresos", descending=True)
        .collect()
        .to_dicts()
    )


@router.get("/analitica/por-categoria")
async def ventas_por_categoria():

    async with lock:
        return await asyncio.to_thread(
            calcular_ventas_por_categoria
        )
