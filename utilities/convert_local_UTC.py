#!/usr/bin/env python
from pathlib import Path
import sqlite3
from datetime import datetime
from zoneinfo import ZoneInfo

repo_root = Path(__file__).resolve().parents[1]
DB_PATH = repo_root / "data" / "measures.db"

TABLE_ORIG = "precios_indexada_som"     # ← tabla con horas locales
COL_FECHA_LOCAL = "datetime"   # ← columna con la hora local (TEXT)
TABLE_UTC = "tabla_utc"           # ← nueva tabla a crear
TZ_LOCAL = "Europe/Madrid"


def local_to_utc(ts_str: str) -> str:
    """
    Convierte una fecha/hora local (sin tz) en Europe/Madrid a UTC (ISO 8601).
    Espera formato 'YYYY-MM-DD HH:MM:SS' o ISO similar.
    """
    if ts_str is None:
        return None

    # Parse naive
    dt = datetime.fromisoformat(ts_str)

    # Asignar zona horaria local
    dt_local = dt.replace(tzinfo=ZoneInfo(TZ_LOCAL))

    # Convertir a UTC
    dt_utc = dt_local.astimezone(ZoneInfo("UTC"))

    return dt_utc.isoformat(sep=" ")


def main():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    # 1) Leer esquema de la tabla original
    cur.execute(f"PRAGMA table_info({TABLE_ORIG})")
    cols_info = cur.fetchall()
    # cols_info: [(cid, name, type, notnull, dflt_value, pk), ...]

    col_names = [c[1] for c in cols_info]

    if COL_FECHA_LOCAL not in col_names:
        raise ValueError(f"La columna {COL_FECHA_LOCAL} no existe en {TABLE_ORIG}")

    # 2) Crear nueva tabla: mismas columnas + fecha_utc TEXT
    #    (si ya existe, la borramos)
    cur.execute(f"DROP TABLE IF EXISTS {TABLE_UTC}")

    cols_def = []
    for cid, name, col_type, notnull, dflt, pk in cols_info:
        col_def = f"{name} {col_type or ''}".strip()
        if pk:
            col_def += " PRIMARY KEY"
        cols_def.append(col_def)

    # Añadimos columna nueva
    cols_def.append("date_utc DATE")

    create_sql = f"CREATE TABLE {TABLE_UTC} ({', '.join(cols_def)})"
    cur.execute(create_sql)

    # 3) Leer todos los registros de la tabla original
    cur.execute(f"SELECT * FROM {TABLE_ORIG}")
    rows = cur.fetchall()

    idx_fecha_local = col_names.index(COL_FECHA_LOCAL)

    # 4) Preparar inserción en la nueva tabla
    new_col_names = col_names + ["date_utc"]
    placeholders = ", ".join(["?"] * len(new_col_names))
    insert_sql = f"INSERT INTO {TABLE_UTC} ({', '.join(new_col_names)}) VALUES ({placeholders})"

    new_rows = []
    for row in rows:
        row = list(row)
        ts_local = row[idx_fecha_local]
        ts_utc = local_to_utc(ts_local)
        new_rows.append(row + [ts_utc])

    # 5) Insertar en bloque
    cur.executemany(insert_sql, new_rows)
    conn.commit()
    conn.close()

    print(f"Tabla {TABLE_UTC} creada con {len(new_rows)} filas.")


if __name__ == "__main__":
    main()
