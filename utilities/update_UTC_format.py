import sqlite3
import pandas as pd

conn = sqlite3.connect("../dashboard/data/measures.db")

df = pd.read_sql("SELECT rowid, datetime FROM ESIOS_data where datetime < '2026-01-01'", conn)
df['datetime'] = pd.to_datetime(df['datetime'], utc=True).dt.tz_localize(None).dt.strftime('%Y-%m-%d %H:%M:%S')

for _, row in df.iterrows():
    conn.execute("UPDATE ESIOS_data SET datetime = ? WHERE rowid = ?", (row['datetime'], row['rowid']))

conn.commit()
conn.close()