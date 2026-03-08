"""
tarifa_20TD.py
Cálculo de periodos P1–P3 y costes regulados (peajes, cargos y pagos por capacidad)
para la tarifa 2.0TD en España.
Contiene:
    def costes_regulados(df: pd.DataFrame, col_datetime: str) -> pd.DataFrame:
"""
from pathlib import Path
import pandas as pd
import json
from comun.date_conditions import periodo_2_0TD   
# ==========================
# COSTES REGULADOS
# ==========================
def costes_regulados(df: pd.DataFrame) -> pd.DataFrame:
    """
    Añade columnas al df:
    - periodo (P1–P3)
    - peaje
    - cargo
    - capacidad
    - coste_regulado
    Parameters:
    - df debe estar indexado por datetime UTC
    """
# Ruta al JSON dentro de data/
    repo_root = Path(__file__).resolve().parents[1]
    JSON_PATH = repo_root / "data" / "costes_regulados.json"
    try:
        with open(JSON_PATH, "r", encoding="utf-8") as f:
            costes = json.load(f)["cargos"]
    except FileNotFoundError:
        print(f"Archivo no encontrado: {JSON_PATH}")
        return df
    except json.JSONDecodeError:
        print(f"Error al decodificar el archivo JSON: {JSON_PATH}")
        return df

    df = df.copy()
    df["periodo"] = df.index.map(periodo_2_0TD)
    
    #row.index.year no existe por lo que se usa row.name que contiene el valor del date que actua como index
    df["peaje"] = df.apply(
        lambda row: costes[str(row.name.year)]["peaje"][row["periodo"]],
        axis=1
    )
    df["cargo"] = df.apply(
        lambda row: costes[str(row.name.year)]["cargo"][row["periodo"]],
        axis=1
    )
    df["capacidad"] = df.apply(
        lambda row: costes[str(row.name.year)]["capacidad"][row["periodo"]],
        axis=1
    )
    df["costes_regulados"] = df["peaje"] + df["cargo"] + df["capacidad"]
    return df
