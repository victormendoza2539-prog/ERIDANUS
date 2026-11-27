
"""Prueba de concurrencia entre compras y corte de caja."""

import asyncio
from datetime import datetime
from pathlib import Path
from tempfile import TemporaryDirectory
from threading import Event
from unittest.mock import patch

import polars as pl

import main
import analitica
import corte_caja

from esquema_ventas import ESQUEMA_VENTAS


def crear_venta(id_venta):

    return {
        "id_venta": id_venta,
        "fecha": datetime(2026, 11, 27, 10, 0),
        "producto": "Producto experimental",
        "precio": 100.0,
        "cantidad": 1,
        "monto_total": 100.0,
    }


async def ejecutar_prueba():

    with TemporaryDirectory() as carpeta:

        base = Path(carpeta)

        parquet = base / "ventas.parquet"
        csv = base / "ventas.csv"
        productos = base / "productos.csv"

        # 1. Crear historico experimental
        pl.DataFrame(
            [crear_venta(1), crear_venta(2)],
            schema=ESQUEMA_VENTAS,
        ).write_parquet(parquet)

        # 2. Crear una venta pendiente
        pl.DataFrame(
            [crear_venta(3)],
            schema=ESQUEMA_VENTAS,
        ).write_csv(csv)

        # 3. Crear inventario experimental
        pl.DataFrame([{
            "id": 1,
            "nombre": "Producto experimental",
            "categoria": "Pruebas",
            "precio": 100.0,
            "cantidad": 10,
            "descripcion": "Producto temporal",
            "imagen": "",
        }]).write_csv(productos)

        # 4. Preparar eventos de sincronizacion
        corte_iniciado = Event()
        permitir_corte = Event()

        consolidacion_original = (
            corte_caja.consolidar_ventas
        )

        def consolidacion_controlada():

            corte_iniciado.set()

            if not permitir_corte.wait(timeout=15):
                raise TimeoutError(
                    "Tiempo de espera agotado."
                )

            return consolidacion_original()

        # 5. Sustituir rutas temporalmente
        with patch.multiple(
            main,
            CARPETA=base,
            ARCHIVO_PRODUCTOS=productos,
            ARCHIVO_VENTAS=csv,
            ARCHIVO_PARQUET=parquet,
        ), patch.multiple(
            analitica,
            ARCHIVO_PRODUCTOS=productos,
            ARCHIVO_VENTAS=csv,
            ARCHIVO_PARQUET=parquet,
        ), patch.multiple(
            corte_caja,
            BASE=base,
            ARCHIVO_VENTAS=csv,
            ARCHIVO_PARQUET=parquet,
            consolidar_ventas=consolidacion_controlada,
        ):

            assert main.lock is corte_caja.lock
            assert main.lock is analitica.lock

            print("\n--- ESTADO INICIAL ---")
            print("Stock inicial: 10")
            print("Ventas historicas: 2")
            print("Ventas pendientes: 1")

            # 6. Iniciar corte de caja
            tarea_corte = asyncio.create_task(
                corte_caja.corte_de_caja()
            )

            compras = []

            try:

                iniciado = await asyncio.to_thread(
                    corte_iniciado.wait, 5
                )

                assert iniciado
                assert main.lock.locked()

                print("\nCorte iniciado.")
                print("Bloqueo adquirido.")

                # 7. Lanzar cinco compras concurrentes
                compras = [
                    asyncio.create_task(
                        main.comprar_producto(
                            producto_id=1,
                            cantidad=1,
                        )
                    )
                    for _ in range(5)
                ]

                await asyncio.sleep(0.2)

                en_espera = sum(
                    not tarea.done()
                    for tarea in compras
                )

                print("Compras en espera:", en_espera)

                assert en_espera == 5

                assert main.leer_productos()[0][
                    "cantidad"
                ] == 10

                print("Stock intacto durante el bloqueo.")

            finally:

                # Liberar la consolidacion incluso
                # si alguna comprobacion falla
                permitir_corte.set()

                await asyncio.gather(
                    tarea_corte,
                    *compras,
                    return_exceptions=True,
                )

            # 8. Recuperar resultados
            resultado_corte = tarea_corte.result()

            print("\n--- CORTE COMPLETADO ---")
            print(resultado_corte)

            resultados = [
                tarea.result()
                for tarea in compras
            ]

            ids = sorted([
                resultado["venta"]["id_venta"]
                for resultado in resultados
            ])

            # 9. Verificar archivos e inventario
            historico = pl.read_parquet(parquet)

            recientes = pl.read_csv(
                csv,
                schema=ESQUEMA_VENTAS,
                try_parse_dates=True,
            )

            ventas = analitica.cargar_ventas().collect()

            stock = main.leer_productos()[0]["cantidad"]

            kpis = analitica.calcular_resumen()

            print("\n--- RESULTADOS FINALES ---")
            print("Compras exitosas:", len(resultados))
            print("IDs nuevos:", ids)
            print("Registros en Parquet:", historico.height)
            print("Registros en CSV:", recientes.height)
            print("Ventas totales:", ventas.height)
            print("IDs unicos:", ventas["id_venta"].n_unique())
            print("Stock final:", stock)
            print("Ingresos totales:", kpis["ingresos_totales"])

            # 10. Criterios de aceptacion
            assert resultado_corte["ventas_consolidadas"] == 1
            assert len(resultados) == 5
            assert ids == [4, 5, 6, 7, 8]
            assert historico.height == 3
            assert recientes.height == 5
            assert ventas.height == 8
            assert ventas["id_venta"].n_unique() == 8
            assert stock == 5
            assert kpis["transacciones"] == 8
            assert kpis["unidades_vendidas"] == 8
            assert kpis["ingresos_totales"] == 800.0

            print("\nPRUEBA SUPERADA")


if __name__ == "__main__":

    asyncio.run(ejecutar_prueba())
