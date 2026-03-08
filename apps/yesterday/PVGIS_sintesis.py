import sys
from pathlib import Path
import pandas as pd
from datetime import datetime
# Añadir la raíz del repo al PYTHONPATH
repo_root = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(repo_root))
import comun.sql_utilities as db
from comun.date_conditions import day_of_year_no_leap

# Function to convert time format (assuming UTC already)
def format_utc_time(raw_time):
    dt = datetime.strptime(raw_time, "%Y-%m-%d %H%M")  # Convert string to datetime
    return dt.strftime("%Y-%m-%d %H:00:00") 

try:
    # Connect to the SQLite database
    # Connect to SQLite database
    conn, error = db.init_db()

    # Load the table into a Pandas DataFrame
    df = pd.read_sql_query("SELECT * FROM PVGIS", conn, parse_dates=["datetime"])

    df["dayIndex"] = df["datetime"].apply(day_of_year_no_leap)
    df["hour"] = df["datetime"].dt.hour
    df_avg = df.groupby(["dayIndex", "hour"])["power_Wh"].mean().reset_index()

    # Create the table if it doesn't exist
    cursor = conn.cursor()
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS PVGIS_sintesis (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        dayIndex INTEGER,
        hour INTEGER,
        power_Wh REAL
    )
    ''')

    # Insert data into the table
    df_avg.to_sql('PVGIS_sintesis', conn, if_exists='replace', index=False)

    # Commit changes and close connection
    conn.commit()
    conn.close()
    print("Data successfully sintesis into SQLite PVGIS_sintesis from PVGIS!")

except Exception as err:
    print(f"Error from PVGIS_sintesis {err=}, {type(err)=}")