import sqlite3
import pandas as pd

conn = sqlite3.connect("./dashboard/data/measures.db")
TABLE_NAME = "WIBEE"

df = pd.read_sql(f"SELECT * FROM {TABLE_NAME}", conn)
df.to_csv(f"./dashboard/data/{TABLE_NAME}.csv", index=False, sep=";", encoding="utf-8-sig")

conn.close()