"""
merge_desvios.py
----------------
Lee un CSV con columnas [desvio, value, datetime] y añade las columnas
'subir' y 'bajar' a una tabla SQLite existente, promediando si la
frecuencia del CSV es mayor que la horaria.

Uso:
    python merge_desvios.py \
        --db      ruta/a/base.db \
        --table   nombre_tabla \
        --csv     ruta/a/desvios.csv \
        --dt-col  datetime          # nombre columna datetime en la tabla (por defecto: datetime)
"""

import argparse
import sqlite3
import pandas as pd


# ── helpers ──────────────────────────────────────────────────────────────────

def load_csv(path: str) -> pd.DataFrame:
    df = pd.read_csv(path, delimiter=';')
    df.columns = df.columns.str.strip().str.lower()

    required = {"desvio", "value", "datetime"}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"El CSV no tiene las columnas esperadas: {missing}")

    df["datetime"] = pd.to_datetime(df["datetime"])
    df["value"] = pd.to_numeric(df["value"], errors="coerce")
    return df


def pivot_and_resample(df: pd.DataFrame) -> pd.DataFrame:
    """
    Pivota subir/bajar y promedía por hora.
    Devuelve un DataFrame con índice horario y columnas [subir, bajar].
    """
    df["desvio"] = df["desvio"].str.strip().str.lower()

    pivot = (
        df.pivot_table(index="datetime", columns="desvio", values="value", aggfunc="mean")
        .rename_axis(None, axis=1)
        .reset_index()
    )

    # Asegurar que existen ambas columnas aunque el CSV solo traiga una
    for col in ("subir", "bajar"):
        if col not in pivot.columns:
            pivot[col] = float("nan")

    # Redondear al inicio de hora para el merge posterior
    pivot["datetime"] = pd.to_datetime(pivot["datetime"], utc=True).dt.floor("h")

    # Si hay varias filas por hora (frecuencia > horaria) → promedio
    hourly = (
        pivot.groupby("datetime")[["subir", "bajar"]]
        .mean()
        .reset_index()
    )

    return hourly


def add_columns_if_missing(conn: sqlite3.Connection, table: str) -> None:
    existing = {
        row[1]
        for row in conn.execute(f"PRAGMA table_info('{table}')").fetchall()
    }
    for col in ("subir", "bajar"):
        if col not in existing:
            conn.execute(f"ALTER TABLE '{table}' ADD COLUMN {col} REAL")
            print(f"  · Columna '{col}' añadida a la tabla '{table}'.")
        else:
            print(f"  · Columna '{col}' ya existe, se actualizará.")
    conn.commit()


def update_table(
    conn: sqlite3.Connection,
    table: str,
    hourly: pd.DataFrame,
    dt_col: str,
) -> int:
    """
    Actualiza las columnas subir/bajar en la tabla SQLite haciendo
    el match por la hora truncada del datetime existente.
    Devuelve el número de filas actualizadas.
    """
    cur = conn.cursor()
    updated = 0

    for _, row in hourly.iterrows():
        # Construir el rango horario [hora, hora+59:59] para cubrir
        # distintos formatos de datetime en la tabla destino
        hour_start = row["datetime"]
        hour_end   = hour_start + pd.Timedelta(hours=1) - pd.Timedelta(seconds=1)

        # Formato ISO para SQLite
        t0 = hour_start.strftime("%Y-%m-%d %H:%M:%S")
        t1 = hour_end.strftime("%Y-%m-%d %H:%M:%S")

        sql = f"""
            UPDATE '{table}'
            SET subir = ?,
                bajar = ?
            WHERE strftime('%Y-%m-%d %H', {dt_col}) =
                  strftime('%Y-%m-%d %H', ?)
        """
        cur.execute(sql, (
            None if pd.isna(row["subir"]) else float(row["subir"]),
            None if pd.isna(row["bajar"]) else float(row["bajar"]),
            t0,
        ))
        updated += cur.rowcount

    conn.commit()
    return updated


# ── main ─────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Merge desvíos CSV → SQLite")
    parser.add_argument("--db",     required=True, help="Ruta a la base de datos SQLite")
    parser.add_argument("--table",  required=True, help="Nombre de la tabla destino")
    parser.add_argument("--csv",    required=True, help="Ruta al CSV de desvíos")
    parser.add_argument("--dt-col", default="datetime",
                        help="Nombre de la columna datetime en la tabla (por defecto: datetime)")
    args = parser.parse_args()

    print(f"\n📂 CSV:    {args.csv}")
    print(f"🗄️  DB:     {args.db}  →  tabla '{args.table}'")
    print(f"🕐 dt-col: {args.dt_col}\n")

    # 1. Cargar y transformar CSV
    print("1/4  Cargando CSV...")
    df = load_csv(args.csv)
    print(f"     {len(df)} filas leídas. "
          f"Rango: {df['datetime'].min()} → {df['datetime'].max()}")

    print("2/4  Pivotando y promediando por hora...")
    hourly = pivot_and_resample(df)
    print(f"     {len(hourly)} horas únicas tras el resample.")

    # 2. Conectar a SQLite y preparar columnas
    conn = sqlite3.connect(args.db)
    print("3/4  Verificando columnas en la tabla destino...")
    add_columns_if_missing(conn, args.table)

    # 3. Actualizar
    print("4/4  Actualizando filas...")
    n = update_table(conn, args.table, hourly, args.dt_col)
    conn.close()

    print(f"\n✅  Listo. {n} filas actualizadas en '{args.table}'.\n")


if __name__ == "__main__":
    main()