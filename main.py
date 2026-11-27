"""ERIDANUS — Gabinete de Curiosidades. API CSV de inventario y ventas."""
import polars as pl

from concurrencia import lock
from analitica import cargar_ventas

from esquema_ventas import (
    COLUMNAS_VENTAS,
    ARCHIVO_PARQUET,
)

import asyncio
import csv
import os
import tempfile
from datetime import datetime
from pathlib import Path

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from analitica import router as router_analitica

from contextlib import asynccontextmanager
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from corte_caja import corte_de_caja

@asynccontextmanager
async def lifespan(app: FastAPI):

    # Preparar archivos antes de iniciar el servicio
    preparar_archivos()

    # Crear el planificador de tareas
    scheduler = AsyncIOScheduler(
        timezone="America/Mexico_City"
    )

    # Configurar modalidad de ejecución
    modo = os.getenv("MODO_CORTE", "demo")

    if modo == "demo":

        scheduler.add_job(
            corte_de_caja,
            trigger="interval",
            minutes=2,
            id="corte_eridanus",
            max_instances=1,
            coalesce=True,
            replace_existing=True,
        )

        print("[ERIDANUS] Corte automático cada 2 minutos.")

    elif modo == "produccion":

        scheduler.add_job(
            corte_de_caja,
            trigger="cron",
            hour=0,
            minute=0,
            id="corte_eridanus",
            max_instances=1,
            coalesce=True,
            replace_existing=True,
        )

        print("[ERIDANUS] Corte automático diario a medianoche.")

    else:
        raise ValueError("MODO_CORTE no reconocido.")

    # Iniciar APScheduler
    scheduler.start()

    app.state.scheduler = scheduler

    try:
        yield

    finally:
        # Detener la programación de nuevos cortes
        scheduler.pause()

        # Esperar a que termine cualquier operación protegida
        async with lock:
            scheduler.shutdown(wait=False)

        print("[ERIDANUS] Planificador detenido.")


app = FastAPI(
    title="ERIDANUS — API de Inventario",
    version="4.0",
    lifespan=lifespan,
)

app.include_router(router_analitica)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

CARPETA = Path(__file__).resolve().parent
ARCHIVO_PRODUCTOS = CARPETA / "productos.csv"
ARCHIVO_VENTAS = CARPETA / "ventas.csv"
COLUMNAS_PRODUCTOS = ["id", "nombre", "categoria", "precio", "cantidad", "descripcion", "imagen"]



class ProductoNuevo(BaseModel):
    nombre: str = Field(min_length=1)
    precio: float = Field(gt=0)
    cantidad: int = Field(ge=0)
    categoria: str = "Sin categoría"
    descripcion: str = ""
    imagen: str = ""


def preparar_archivos():
    for ruta, columnas in ((ARCHIVO_PRODUCTOS, COLUMNAS_PRODUCTOS), (ARCHIVO_VENTAS, COLUMNAS_VENTAS)):
        if not ruta.exists():
            with ruta.open("w", newline="", encoding="utf-8-sig") as archivo:
                csv.writer(archivo).writerow(columnas)


def leer_productos():
    preparar_archivos()
    with ARCHIVO_PRODUCTOS.open(newline="", encoding="utf-8-sig") as archivo:
        lector = csv.DictReader(archivo)
        return [
            {
                "id": int(fila["id"]),
                "nombre": fila["nombre"],
                "categoria": fila.get("categoria") or "Sin categoría",
                "precio": float(fila["precio"]),
                "cantidad": int(fila["cantidad"]),
                "descripcion": fila.get("descripcion") or "",
                "imagen": fila.get("imagen") or "",
            }
            for fila in lector
        ]


def guardar_productos(productos):
    descriptor, temporal = tempfile.mkstemp(dir=CARPETA, prefix="productos_", suffix=".tmp")
    try:
        with os.fdopen(descriptor, "w", newline="", encoding="utf-8-sig") as archivo:
            escritor = csv.DictWriter(archivo, fieldnames=COLUMNAS_PRODUCTOS)
            escritor.writeheader()
            escritor.writerows(productos)
        os.replace(temporal, ARCHIVO_PRODUCTOS)
    finally:
        if os.path.exists(temporal):
            os.remove(temporal)

def obtener_siguiente_id_venta():

    ultimo_id = (
        cargar_ventas()
        .select(pl.col("id_venta").max())
        .collect()
        .item()
    )

    return (ultimo_id or 0) + 1



def registrar_venta(producto, cantidad):

    venta = {
        "id_venta": obtener_siguiente_id_venta(),

        "fecha": datetime.now().isoformat(
            timespec="seconds"
        ),

        "producto": producto["nombre"],

        "precio": producto["precio"],

        "cantidad": cantidad,

        "monto_total": round(
            producto["precio"] * cantidad, 2
        ),
    }

    with open(
        ARCHIVO_VENTAS,
        "a",
        newline="",
        encoding="utf-8",
    ) as archivo:

        escritor = csv.DictWriter(
            archivo,
            fieldnames=COLUMNAS_VENTAS,
        )

        escritor.writerow(venta)

    return {
        **venta,
        "producto_id": producto["id"],
        "total": venta["monto_total"],
    }


@app.get("/")
async def home():
    return {"mensaje": "Bienvenido a ERIDANUS — Gabinete de Curiosidades"}


@app.get("/productos")
async def getProductos():
    return leer_productos()


@app.get("/productos/{producto_id}")
async def getProductoPorId(producto_id: int):
    for producto in leer_productos():
        if producto["id"] == producto_id:
            return producto
    raise HTTPException(status_code=404, detail="Producto no encontrado")


@app.post("/productos", status_code=201)
async def addProducto(producto: ProductoNuevo):
    async with lock:
        inventario = leer_productos()

        nuevo_id = max(
            (p["id"] for p in inventario), default=0
        ) + 1

        nuevo_producto = {
            "id": nuevo_id,
            "nombre": producto.nombre.strip(),
            "categoria": producto.categoria.strip() or "Sin categoría",
            "precio": producto.precio,
            "cantidad": producto.cantidad,
            "descripcion": producto.descripcion.strip(),
            "imagen": producto.imagen.strip(),
        }

        # Validar que el nombre no esté vacío
        if not nuevo_producto["nombre"]:
            raise HTTPException(
                status_code=422,
                detail="El nombre no puede estar vacío"
            )

        # NUEVO: evitar nombres duplicados
        if any(
            p["nombre"].strip().casefold()
            == nuevo_producto["nombre"].casefold()
            for p in inventario
        ):
            raise HTTPException(
                status_code=409,
                detail="Ya existe un producto con ese nombre."
            )

        inventario.append(nuevo_producto)
        guardar_productos(inventario)

        return {
            "mensaje": "Producto agregado con éxito",
            "producto": nuevo_producto
        }

@app.delete("/productos/{producto_id}")
async def deleteProducto(producto_id: int):
    async with lock:
        inventario = leer_productos()
        actualizado = [p for p in inventario if p["id"] != producto_id]
        if len(actualizado) == len(inventario):
            raise HTTPException(status_code=404, detail="Producto no encontrado")
        guardar_productos(actualizado)
        return {"mensaje": "Producto eliminado con éxito"}


@app.post("/productos/{producto_id}")
async def comprar_producto(producto_id: int, cantidad: int = Query(default=1, ge=1)):
    async with lock:
        inventario = leer_productos()
        for producto in inventario:
            if producto["id"] == producto_id:
                if producto["cantidad"] < cantidad:
                    raise HTTPException(status_code=400, detail="No hay stock suficiente")
                producto["cantidad"] -= cantidad
                venta = registrar_venta(producto, cantidad)
                guardar_productos(inventario)
                return {"mensaje": "Compra realizada", "venta": venta, "stock_restante": producto["cantidad"]}
        raise HTTPException(status_code=404, detail="Producto no encontrado")
