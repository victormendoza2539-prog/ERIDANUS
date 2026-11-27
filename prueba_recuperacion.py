
"""Pruebas de recuperacion de ERIDANUS 4.0."""

from datetime import datetime
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

import polars as pl

import analitica
import corte_caja

from esquema_ventas import ESQUEMA_VENTAS


def crear_venta(id_venta, cantidad=1):

    return {
        "id_venta": id_venta,
        "fecha": datetime(2026, 11, 27, 10, 0),
        "producto": "Producto experimental",
        "precio": 100.0,
        "cantidad": cantidad,
        "monto_total": 100.0 * cantidad,
    }


def crear_tabla(ventas):

    return pl.DataFrame(
        ventas,
        schema=ESQUEMA_VENTAS,
    )


def ejecutar_pruebas():

    with TemporaryDirectory() as carpeta:

        base = Path(carpeta)
        parquet = base / "ventas.parquet"
        csv = base / "ventas.csv"

        # Historico experimental
        crear_tabla([
            crear_venta(1),
            crear_venta(2),
        ]).write_parquet(parquet)

        # Simular un corte interrumpido
        crear_tabla([
            crear_venta(2),
            crear_venta(3),
        ]).write_csv(csv)

        with patch.multiple(
            analitica,
            ARCHIVO_PARQUET=parquet,
            ARCHIVO_VENTAS=csv,
        ), patch.multiple(
            corte_caja,
            BASE=base,
            ARCHIVO_PARQUET=parquet,
            ARCHIVO_VENTAS=csv,
        ):

            # PRUEBA D1
            print("\n--- D1: UNION SIN DUPLICADOS ---")

            ventas = analitica.cargar_ventas().collect()

            print("Registros:", ventas.height)
            print("IDs:", sorted(ventas["id_venta"].to_list()))
            print("Ingresos:", ventas["monto_total"].sum())

            assert ventas.height == 3
            assert ventas["id_venta"].n_unique() == 3
            assert ventas["monto_total"].sum() == 300.0

            print("D1 SUPERADA")

            # PRUEBA D2
            print("\n--- D2: RECUPERACION DEL CORTE ---")

            resultado = corte_caja.consolidar_ventas()

            print(resultado)

            historico = pl.read_parquet(parquet)
            recientes = pl.read_csv(
                csv,
                schema=ESQUEMA_VENTAS,
            )

            assert resultado["ventas_consolidadas"] == 1
            assert historico.height == 3
            assert historico["id_venta"].n_unique() == 3
            assert recientes.height == 0

            # Repetir el corte
            repeticion = corte_caja.consolidar_ventas()

            assert repeticion["ventas_consolidadas"] == 0
            assert pl.read_parquet(parquet).height == 3

            print("D2 SUPERADA")

            # PRUEBA D3
            print("\n--- D3: REGISTROS CONTRADICTORIOS ---")

            crear_tabla([
                crear_venta(3, cantidad=5),
            ]).write_csv(csv)

            parquet_antes = parquet.read_bytes()
            csv_antes = csv.read_bytes()

            try:

                corte_caja.consolidar_ventas()

            except ValueError as error:

                print("Conflicto detectado:", error)

                assert "Conflicto" in str(error)

            else:

                raise AssertionError(
                    "El conflicto no fue detectado."
                )

            assert parquet.read_bytes() == parquet_antes
            assert csv.read_bytes() == csv_antes

            print("Archivos preservados correctamente")
            print("D3 SUPERADA")

    print("\nTODAS LAS PRUEBAS SUPERADAS")


if __name__ == "__main__":

    ejecutar_pruebas()
