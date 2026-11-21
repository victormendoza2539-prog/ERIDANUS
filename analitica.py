"""Endpoints de análisis de ventas de ERIDANUS mediante Pandas."""
from pathlib import Path
import pandas as pd
from fastapi import APIRouter

router = APIRouter(prefix="/analitica", tags=["Observatorio — Pandas"])
BASE = Path(__file__).resolve().parent
VENTAS = BASE / "ventas.csv"
PRODUCTOS = BASE / "productos.csv"
COLUMNAS = ["fecha", "producto_id", "producto", "precio", "cantidad", "total"]


def cargar_ventas():
    if not VENTAS.exists() or VENTAS.stat().st_size == 0:
        return pd.DataFrame(columns=COLUMNAS)
    df = pd.read_csv(VENTAS, encoding="utf-8-sig")
    if df.empty:
        return pd.DataFrame(columns=COLUMNAS)
    for col in ("producto_id", "precio", "cantidad", "total"):
        df[col] = pd.to_numeric(df[col], errors="raise")
    return df


def categorias_actuales():
    if not PRODUCTOS.exists() or PRODUCTOS.stat().st_size == 0:
        return pd.DataFrame(columns=["id", "categoria"])
    df = pd.read_csv(PRODUCTOS, encoding="utf-8-sig")
    if "categoria" not in df.columns:
        return pd.DataFrame(columns=["id", "categoria"])
    return df[["id", "categoria"]].rename(columns={"id": "producto_id"})


@router.get("/resumen")
def resumen():
    df = cargar_ventas()
    if df.empty:
        return {"ingresos_totales": 0.0, "transacciones": 0, "unidades_vendidas": 0,
                "ticket_promedio": 0.0, "producto_mas_vendido": None}
    unidades = (df.groupby(["producto_id", "producto"], as_index=False)["cantidad"]
                .sum().sort_values(["cantidad", "producto_id"], ascending=[False, True]))
    lider = unidades.iloc[0]
    return {
        "ingresos_totales": round(float(df["total"].sum()), 2),
        "transacciones": int(len(df)),
        "unidades_vendidas": int(df["cantidad"].sum()),
        "ticket_promedio": round(float(df["total"].mean()), 2),
        "producto_mas_vendido": {"id": int(lider["producto_id"]),
                                  "nombre": str(lider["producto"]),
                                  "unidades": int(lider["cantidad"])}
    }


@router.get("/por-producto")
def ventas_por_producto():
    df = cargar_ventas()
    if df.empty:
        return []
    tabla = (df.groupby(["producto_id", "producto"], as_index=False)
             .agg(unidades_vendidas=("cantidad", "sum"), ingresos=("total", "sum"),
                  transacciones=("fecha", "size"))
             .sort_values(["ingresos", "producto_id"], ascending=[False, True]))
    return [{"producto_id": int(r.producto_id), "producto": str(r.producto),
             "unidades_vendidas": int(r.unidades_vendidas),
             "ingresos": round(float(r.ingresos), 2), "transacciones": int(r.transacciones)}
            for r in tabla.itertuples(index=False)]


@router.get("/por-categoria")
def ventas_por_categoria():
    df = cargar_ventas()
    if df.empty:
        return []
    # La categoría se obtiene del catálogo actual; los productos eliminados quedan como "Sin categoría".
    df = df.merge(categorias_actuales(), on="producto_id", how="left")
    df["categoria"] = df["categoria"].fillna("Sin categoría")
    tabla = (df.groupby("categoria", as_index=False)
             .agg(unidades_vendidas=("cantidad", "sum"), ingresos=("total", "sum"),
                  transacciones=("fecha", "size"))
             .sort_values("ingresos", ascending=False))
    return [{"categoria": str(r.categoria), "unidades_vendidas": int(r.unidades_vendidas),
             "ingresos": round(float(r.ingresos), 2), "transacciones": int(r.transacciones)}
            for r in tabla.itertuples(index=False)]
