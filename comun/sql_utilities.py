from pathlib import Path
import sqlite3
import pandas as pd

def init_db():

# Ruta al JSON dentro de comun/
    repo_root = Path(__file__).resolve().parents[1]
    DB_PATH = repo_root / "data" / "measures.db"

    # Connect to SQLite database
    try:
        conn = sqlite3.connect(DB_PATH)
        return conn, None
    except sqlite3.Error as e:      
        error = f"Error al conectar a la base de datos: {e}"
        return None, error

def get_tables_info(conn, tables) -> pd.dataframe:
    try:
        # # Connect to the SQLite database
        cursor = conn.cursor()
        df = pd.DataFrame(columns=["Tabla", "Desde", "Hasta"])
        for table in tables:
            sql = f"SELECT '{table}' as Tabla, min(datetime) as Desde, max(datetime) as Hasta FROM {table};"
            cursor.execute(sql)
            row = cursor.fetchall()  # Returns a list of tuples
            df = pd.concat([df, pd.DataFrame([row[0]], columns=["Tabla", "Desde", "Hasta"])], ignore_index=True)
        return df, None
    except Exception as err:
    # Crear un Label para mostrar el mensaje
        error =f"Error al obtener información de las tablas: {err}"
        return None, error
    
def read_sql_ts(query: str, conn: sqlite3.Connection) -> pd.DataFrame:
    '''
    Convierte una instruccion SQL en un dataframe indexando la columna datetime con UTC
    Se basa en hipotesis todas las tablas tienen columna datetime y estan en UTC
    '''
    df = pd.read_sql(
        query,
        conn,
        parse_dates=["datetime"],
        index_col="datetime"
    )
    df.index = pd.to_datetime(df.index, utc=True)
    return df