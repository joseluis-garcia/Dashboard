from pathlib import Path
import sqlite3
import pandas as pd


def init_db():
    """
    Inicializa conexión a la base de datos SQLite.
    
    Returns:
        Tupla (conexión, error) donde error es None si todo va bien
    """
    # Ruta a la BD
    repo_root = Path(__file__).resolve().parents[1]
    DB_PATH = repo_root / "data" / "measures.db"

    # Connect to SQLite database
    try:
        conn = sqlite3.connect(str(DB_PATH))
        return conn, None
    except sqlite3.Error as e:
        error = f"Error al conectar a la base de datos: {e}"
        return None, error


def get_tables_info(conn, tables):
    """
    Obtiene información de las tablas en la BD.
    
    Args:
        conn: Conexión a SQLite
        tables: Lista de nombres de tablas
        
    Returns:
        Tupla (DataFrame con info, error)
    """
    try:
        cursor = conn.cursor()
        df = pd.DataFrame(columns=["Tabla", "Desde", "Hasta"])
        for table in tables:
            sql = f"SELECT '{table}' as Tabla, min(datetime) as Desde, max(datetime) as Hasta FROM {table};"
            cursor.execute(sql)
            row = cursor.fetchall()  # Returns a list of tuples
            df = pd.concat([df, pd.DataFrame([row[0]], columns=["Tabla", "Desde", "Hasta"])], ignore_index=True)
        return df, None
    except Exception as err:
        error = f"Error al obtener información de las tablas: {err}"
        return None, error


def read_sql_ts(query: str, conn: sqlite3.Connection) -> pd.DataFrame:
    """
    Convierte una instruccion SQL en un dataframe indexando la columna datetime con UTC.
    Se basa en hipotesis que todas las tablas tienen columna datetime y estan en UTC.
    
    Args:
        query: Consulta SQL
        conn: Conexión a BD
        
    Returns:
        DataFrame con índice datetime en UTC
    """
    df = pd.read_sql(
        query,
        conn,
        parse_dates=["datetime"],
        index_col="datetime"
    )
    df.index = pd.to_datetime(df.index, utc=True)
    return df
