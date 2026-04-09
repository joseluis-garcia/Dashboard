import pandas as pd
import sqlite3

def import_csv_to_sqlite(csv_path: str, db_path: str, table_name: str, local_tz: str = "Europe/Madrid"):
    df = pd.read_csv(csv_path, sep=",")  # ajusta sep si es necesario
    
    df["datetime"] = (
        pd.to_datetime(df["datetime"])
        .dt.tz_localize(local_tz, ambiguous=False, nonexistent="shift_forward")
        .dt.tz_convert("UTC")
        .dt.strftime("%Y-%m-%d %H:%M:%S")
    )
    
    with sqlite3.connect(db_path) as conn:
        df.to_sql(table_name, conn, if_exists="append", index=False)

    print(f"Insertados {len(df)} registros en '{table_name}'")

if __name__ == "__main__":
    import_csv_to_sqlite("meteo.csv", "../dashboard/data/measures.db", "METEO_1")