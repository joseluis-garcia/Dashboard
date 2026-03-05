import sqlite3
import pandas as pd
from pathlib import Path

repo_root = Path(__file__).resolve().parents[1]
DB_PATH = repo_root / "data" / "measures.db"

# conectar SQLite
conn = sqlite3.connect(DB_PATH)

# leer tabla
df = pd.read_sql("SELECT * FROM SOM_precios_h where date > '2026-01-31'", conn)
print(df.head())
# convertir formato ancho → largo
df_long = df.melt(
    id_vars="date",
    var_name="hour",
    value_name="price"
)
print(df_long.head())

# construir datetime
df_long["datetime"] = (
    pd.to_datetime(df_long["date"])
    + pd.to_timedelta(df_long["hour"].astype(int), unit="h")
)

# añadir UTC
df_long["date"] = df_long["datetime"].dt.tz_localize("UTC")

# quedarnos con columnas finales
df_final = df_long[["date", "price"]]
print(df_final.head())

# exportar CSV
df_final.to_sql("SOM_precio_indexada", conn, if_exists="append", index=False)

# df_final.to_csv(
#     "output.csv",
#     sep=";",
#     index=False,
#     date_format="%Y-%m-%d %H:%M:%S%z"
# )