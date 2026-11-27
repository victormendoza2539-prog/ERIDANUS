
"""Prueba reproducible de concurrencia de ERIDANUS 4.0."""

import requests

from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
from time import perf_counter
from uuid import uuid4


BASE_URL = "http://127.0.0.1:8000"


def crear_producto():

    producto = {
        "nombre": f"Producto de Prueba {uuid4().hex[:8]}",
        "categoria": "Pruebas Tecnicas",
        "precio": 100.0,
        "cantidad": 20,
        "descripcion": "Producto temporal de concurrencia.",
        "imagen": "",
    }

    respuesta = requests.post(
        f"{BASE_URL}/productos",
        json=producto,
        timeout=15,
    )

    respuesta.raise_for_status()

    return respuesta.json()["producto"]["id"]


def ejecutar_prueba(producto_id, num_compras):

    barrera = Barrier(num_compras)

    producto = requests.get(
        f"{BASE_URL}/productos/{producto_id}",
        timeout=10,
    )

    producto.raise_for_status()

    stock_inicial = producto.json()["cantidad"]

    def realizar_compra(numero):

        barrera.wait(timeout=15)

        respuesta = requests.post(
            f"{BASE_URL}/productos/{producto_id}",
            params={"cantidad": 1},
            timeout=30,
        )

        return {
            "solicitud": numero,
            "codigo": respuesta.status_code,
            "respuesta": respuesta.json(),
        }

    inicio = perf_counter()

    with ThreadPoolExecutor(
        max_workers=num_compras
    ) as executor:

        resultados = list(
            executor.map(
                realizar_compra,
                range(1, num_compras + 1),
            )
        )

    tiempo = perf_counter() - inicio

    exitosas = [
        r for r in resultados
        if r["codigo"] == 200
    ]

    rechazadas = [
        r for r in resultados
        if r["codigo"] != 200
    ]

    ids = [
        r["respuesta"]["venta"]["id_venta"]
        for r in exitosas
    ]

    producto_final = requests.get(
        f"{BASE_URL}/productos/{producto_id}",
        timeout=10,
    )

    producto_final.raise_for_status()

    stock_final = producto_final.json()["cantidad"]

    print(f"Solicitudes concurrentes: {num_compras}")
    print(f"Compras exitosas: {len(exitosas)}")
    print(f"Compras rechazadas: {len(rechazadas)}")
    print(f"IDs generados: {sorted(ids)}")
    print(f"IDs duplicados: {len(ids) - len(set(ids))}")
    print(f"Stock inicial: {stock_inicial}")
    print(f"Stock final: {stock_final}")
    print(f"Tiempo total: {tiempo:.3f} segundos")

    esperadas = min(stock_inicial, num_compras)

    assert len(exitosas) == esperadas
    assert len(rechazadas) == num_compras - esperadas
    assert all(r["codigo"] == 400 for r in rechazadas)
    assert len(set(ids)) == esperadas
    assert stock_final == stock_inicial - esperadas
    assert stock_final >= 0

    print("PRUEBA SUPERADA")

    return ids


if __name__ == "__main__":

    print("ERIDANUS 4.0 - Pruebas de concurrencia")

    producto_id = crear_producto()

    try:

        print("\n--- PRUEBA A: COMPRAS CONCURRENTES ---")

        ids_a = ejecutar_prueba(producto_id, 10)

        print("\n--- PRUEBA B: PREVENCION DE SOBREVENTA ---")

        ids_b = ejecutar_prueba(producto_id, 20)

        ids_totales = ids_a + ids_b

        assert len(ids_totales) == 20
        assert len(set(ids_totales)) == 20

        print("\nTODAS LAS PRUEBAS SUPERADAS")

    finally:

        respuesta = requests.delete(
            f"{BASE_URL}/productos/{producto_id}",
            timeout=15,
        )

        respuesta.raise_for_status()

        print("Producto experimental eliminado.")
