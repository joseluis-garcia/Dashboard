import pandas as pd
import sqlite3

TABLE_NAME = "DATADIS"

conn = sqlite3.connect("./dashboard/data/measures.db")

# 1. Leer toda la tabla
df = pd.read_sql(f"SELECT * FROM {TABLE_NAME}", conn)
df["datetime"] = pd.to_datetime(df["datetime"])

# 2. Partir en buenos y malos
cutoff = pd.Timestamp("2025-10-26 01:00:00")
df_good = df[df["datetime"] < cutoff].copy()
df_bad  = df[df["datetime"] >= cutoff].copy()

# 3. Corregir los malos: localizar como Europe/Madrid → convertir a UTC → quitar tzinfo
import pytz
madrid = pytz.timezone("Europe/Madrid")

df_bad["datetime"] = (
    df_bad["datetime"]
    .dt.tz_localize("Europe/Madrid", ambiguous=False)  # gestionar DST automáticamente
    .dt.tz_convert("UTC")
    .dt.tz_localize(None)  # dejar naive como el resto
)

# 4. Concatenar y ordenar
df_final = pd.concat([df_good, df_bad]).sort_values("datetime").reset_index(drop=True)

# 5. Volcar a CSV (opcional, para tener un backup) y a la base de datos (sobrescribiendo)
#df_final.to_csv(f"./dashboard/data/{TABLE_NAME}_corrected.csv", index=False, sep=";", encoding="utf-8-sig")
df_final.to_sql("DATADIS_1", conn, if_exists="replace", index=False)
