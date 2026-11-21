"""ERIDANUS — Gabinete de Curiosidades. API CSV de inventario y ventas."""
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

app = FastAPI(title="ERIDANUS — API de Inventario")
app.include_router(router_analitica)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

CARPETA = Path(__file__).resolve().parent
ARCHIVO_PRODUCTOS = CARPETA / "productos.csv"
ARCHIVO_VENTAS = CARPETA / "ventas.csv"
COLUMNAS_PRODUCTOS = ["id", "nombre", "categoria", "precio", "cantidad", "descripcion", "imagen"]
COLUMNAS_VENTAS = ["fecha", "producto_id", "producto", "precio", "cantidad", "total"]
lock = asyncio.Lock()


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


def registrar_venta(producto, cantidad):
    preparar_archivos()
    venta = {
        "fecha": datetime.now().isoformat(timespec="seconds"),
        "producto_id": producto["id"],
        "producto": producto["nombre"],
        "precio": producto["precio"],
        "cantidad": cantidad,
        "total": round(producto["precio"] * cantidad, 2),
    }
    with ARCHIVO_VENTAS.open("a", newline="", encoding="utf-8-sig") as archivo:
        escritor = csv.DictWriter(archivo, fieldnames=COLUMNAS_VENTAS)
        escritor.writerow(venta)
    return venta


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
        nuevo_id = max((p["id"] for p in inventario), default=0) + 1
        nuevo_producto = {
            "id": nuevo_id,
            "nombre": producto.nombre.strip(),
            "categoria": producto.categoria.strip() or "Sin categoría",
            "precio": producto.precio,
            "cantidad": producto.cantidad,
            "descripcion": producto.descripcion.strip(),
            "imagen": producto.imagen.strip(),
        }
        if not nuevo_producto["nombre"]:
            raise HTTPException(status_code=422, detail="El nombre no puede estar vacío")
        inventario.append(nuevo_producto)
        guardar_productos(inventario)
        return {"mensaje": "Producto agregado con éxito", "producto": nuevo_producto}


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
