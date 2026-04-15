"""
Módulo de utilidades para acceso a base de datos SQLite.

Proporciona funciones para:
- Inicializar conexiones a BD SQLite
- Obtener información de tablas
- Leer datos con índices de datetime en UTC
"""

from pathlib import Path
from typing import Tuple, Optional, List, Dict, Any
import sqlite3
import pandas as pd


def init_db() -> Tuple[Optional[sqlite3.Connection], Optional[str]]:
    """
    Inicializa conexión a la base de datos SQLite.
    
    Crea una conexión a la base de datos measures.db ubicada en
    la carpeta 'data' del proyecto.
    
    Returns:
        Tupla (conexión, error) donde:
        - conexión: objeto sqlite3.Connection si es exitoso, None si hay error
        - error: mensaje de error si falla, None si es exitoso
        
    Raises:
        sqlite3.Error: Si hay un problema al conectar (se captura y retorna como error)
        
    Example:
        >>> conn, error = init_db()
        >>> if error:
        ...     print(f"Error: {error}")
        ... else:
        ...     print("Conexión exitosa")
    """
    # Ruta a la BD
    repo_root = Path(__file__).resolve().parents[1]
    db_path = repo_root / "data" / "measures.db"

    # Conectar a la BD SQLite
    try:
        conn = sqlite3.connect(str(db_path))
        return conn, None
    except sqlite3.Error as e:
        error = f"Error al conectar a la base de datos: {e}"
        return None, error


def get_tables_info(
    conn: sqlite3.Connection, 
    tables: List[str]
) -> Tuple[Optional[pd.DataFrame], Optional[str]]:
    """
    Obtiene información sobre las tablas en la base de datos.
    
    Para cada tabla especificada, obtiene:
    - Nombre de la tabla
    - Fecha mínima de los datos (columna datetime)
    - Fecha máxima de los datos (columna datetime)
    
    Args:
        conn: Conexión abierta a SQLite
        tables: Lista de nombres de tablas a analizar
        
    Returns:
        Tupla (dataframe, error) donde:
        - dataframe: DataFrame con columnas ['Tabla', 'Desde', 'Hasta']
        - error: None si es exitoso, mensaje de error si falla
        
    Raises:
        Exception: Se captura cualquier error y se retorna como error message
        
    Example:
        >>> conn, _ = init_db()
        >>> df, error = get_tables_info(conn, ['measures'])
        >>> if not error:
        ...     print(df)
        ...     # Output: 
        ...     #    Tabla       Desde         Hasta
        ...     # 0 measures  2025-01-01  2026-03-09
    """
    try:
        cursor = conn.cursor()
        df = pd.DataFrame(columns=["Tabla", "Desde", "Hasta"])
        
        for table in tables:
            # Ejecutar query para obtener min/max de datetime
            sql = (
                f"SELECT '{table}' as Tabla, "
                f"min(datetime) as Desde, "
                f"max(datetime) as Hasta "
                f"FROM {table};"
            )
            cursor.execute(sql)
            row = cursor.fetchall()  # Retorna lista de tuplas
            
            if row:
                df = pd.concat(
                    [df, pd.DataFrame([row[0]], columns=["Tabla", "Desde", "Hasta"])],
                    ignore_index=True
                )
        
        return df, None
        
    except Exception as err:
        error = f"Error al obtener información de las tablas: {err}"
        return None, error


def read_sql_ts(
    query: str, 
    conn: sqlite3.Connection
)  -> Tuple[Optional[pd.DataFrame], Optional[str]]:
    """
    Lee datos de SQL y los retorna con índice datetime en UTC.
    
    Ejecuta una consulta SQL y retorna un DataFrame con:
    - La columna 'datetime' como índice
    - El índice convertido a UTC
    - Tipos de datos parseados correctamente
    
    Asume que todas las tablas tienen una columna 'datetime' en UTC.
    
    Args:
        query: Consulta SQL a ejecutar
        conn: Conexión abierta a SQLite
        
    Returns:
        DataFrame con índice datetime en UTC
        error en caso de error
        
    Raises:
        pd.errors.DatabaseError: Si hay error en la consulta SQL
        ValueError: Si no existe columna 'datetime'
        
    Example:
        >>> conn, _ = init_db()
        >>> query = "SELECT * FROM measures WHERE datetime > '2026-01-01'"
        >>> df = read_sql_ts(query, conn)
        >>> df.index.name
        'datetime'
        >>> df.index.tz
        datetime.timezone.utc
    """
    try:
        df = pd.read_sql(
            query,
            conn,
            index_col="datetime"
        )
        df.index = pd.to_datetime(df.index, utc=True)
        return df, None
    except Exception as err:
        return None, f"read_sql_ts: {err}"


__all__ = ["init_db", "get_tables_info", "read_sql_ts"]
