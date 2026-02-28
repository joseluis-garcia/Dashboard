"""
tarifa_20TD.py

Cálculo de periodos P1–P3 y costes regulados (peajes, cargos y pagos por capacidad)
para la tarifa 2.0TD en España.

NOTA:
Los valores de peajes, cargos y pagos por capacidad son EJEMPLOS.
Debes sustituirlos por los valores vigentes del BOE.
"""
import os
import pandas as pd
import json
from comun.date_conditions import periodo_2_0TD   
# ==========================
# COSTES REGULADOS
# ==========================

def costes_regulados(df: pd.DataFrame, col_datetime: str) -> pd.DataFrame:
    """
    Añade columnas:
    - periodo (P1–P3)
    - peaje
    - cargo
    - capacidad
    - coste_regulado
    """
# Directorio donde está este archivo (comun/) 
    BASE_DIR = os.path.dirname(os.path.abspath(__file__)) 
# Ruta al JSON dentro de comun/
    JSON_PATH = os.path.join(BASE_DIR, "costes_regulados.json")

    with open(JSON_PATH, "r", encoding="utf-8") as f:
        costes = json.load(f)["cargos"]

    df = df.copy()
    df[col_datetime] = pd.to_datetime(df[col_datetime])
    df["periodo"] = df[col_datetime].apply(periodo_2_0TD)
    
    df["peaje"] = df.apply(
    lambda row: costes[str(row[col_datetime].year)]["peaje"][row["periodo"]],
    axis=1
)
    df["cargo"] = df.apply(
    lambda row: costes[str(row[col_datetime].year)]["cargo"][row["periodo"]],
    axis=1
)
    df["capacidad"] = df.apply(
    lambda row: costes[str(row[col_datetime].year)]["capacidad"][row["periodo"]],
    axis=1
)
    df["costes_regulados"] = df["peaje"] + df["cargo"] + df["capacidad"]
    return df
