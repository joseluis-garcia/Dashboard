"""
Módulo para calcular costes regulados de la tarifa 2.0TD en España.

Proporciona funciones para:
- Calcular periodos tarifarios (P1, P2, P3)
- Obtener peajes, cargos y costes por capacidad
- Agregar costes regulados a DataFrames de precios
"""

from typing import Optional
from pathlib import Path
import pandas as pd
import json
from dashboard.comun.date_conditions import periodo_2_0TD


def costes_regulados(df: pd.DataFrame) -> pd.DataFrame:
    """
    Añade columnas de costes regulados al DataFrame.
    
    Agrega las siguientes columnas al DataFrame:
    - periodo: Periodo tarifario (P1, P2 o P3)
    - peaje: Peaje según periodo y año
    - cargo: Cargo según periodo y año
    - capacidad: Coste de capacidad según periodo y año
    - costes_regulados: Suma de peaje + cargo + capacidad
    
    Args:
        df: DataFrame indexado por datetime UTC
        
    Returns:
        DataFrame con las nuevas columnas agregadas
        
    Note:
        El DataFrame debe estar indexado por datetime.
        
    Example:
        >>> df = pd.DataFrame({...}, index=pd.DatetimeIndex([...]))
        >>> df = costes_regulados(df)
        >>> print(df[['periodo', 'costes_regulados']].head())
    """
    # Ruta al archivo JSON con costes regulados
    # Desde: dashboard/comun/costes_regulados.py
    # A: dashboard/data/costes_regulados.json
    current_file = Path(__file__)
    dashboard_dir = current_file.parents[1]
    json_path = dashboard_dir / "data" / "costes_regulados.json"

    # Cargar costes regulados desde JSON
    try:
        with open(json_path, "r", encoding="utf-8") as f:
            costes = json.load(f)["cargos"]
    except FileNotFoundError:
        print(f"Archivo no encontrado: {json_path}")
        return df
    except json.JSONDecodeError:
        print(f"Error al decodificar el archivo JSON: {json_path}")
        return df
    except KeyError as e:
        print(f"Estructura JSON incorrecta en {json_path}: {e}")
        return df

    # Copiar DataFrame para no modificar el original
    df = df.copy()

    # Calcular periodo tarifario para cada fila
    df["periodo"] = df.index.map(periodo_2_0TD)

    # Obtener peaje según año y periodo
    df["peaje"] = df.apply(
        lambda row: costes[str(row.name.year)]["peaje"][row["periodo"]],
        axis=1
    )

    # Obtener cargo según año y periodo
    df["cargo"] = df.apply(
        lambda row: costes[str(row.name.year)]["cargo"][row["periodo"]],
        axis=1
    )

    # Obtener coste de capacidad según año y periodo
    df["capacidad"] = df.apply(
        lambda row: costes[str(row.name.year)]["capacidad"][row["periodo"]],
        axis=1
    )

    # Calcular total de costes regulados
    df["costes_regulados"] = df["peaje"] + df["cargo"] + df["capacidad"]

    return df


__all__ = ["costes_regulados"]
