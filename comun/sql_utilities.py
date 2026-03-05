import os
from pathlib import Path
import sqlite3

def init_db():

# Ruta al JSON dentro de comun/
    repo_root = Path(__file__).resolve().parents[1]
    DB_PATH = repo_root / "data" / "measures.db"

    print(f"Conectando a la base de datos en: {DB_PATH}")
    # Connect to SQLite database
    try:
        conn = sqlite3.connect(DB_PATH)
        return conn, None
    except sqlite3.Error as e:      
        error = f"Error al conectar a la base de datos: {e}"
        return None, error

