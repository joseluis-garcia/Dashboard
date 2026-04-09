"""
This script processes the PVGIS data stored in the SQLite database, calculates the average power output for each hour of the day across all days, and saves the results in a new table called PVGIS_sintesis. This allows for quick retrieval of average hourly power output for any given day of the year without needing to process the raw PVGIS data each time.
"""
from dashboard.comun import sql_utilities as db
from dashboard.comun.date_conditions import day_of_year_no_leap

try:
    # Connect to the SQLite database
    conn, error = db.init_db()

    # Load the table into a Pandas DataFrame
    df = db.read_sql_ts("SELECT * FROM PVGIS", conn)

    df_local = df.tz_convert("Europe/Madrid")
    df_local["dayIndex"] = df_local.index.map(day_of_year_no_leap)
    df_local["hour"] = df_local.index.hour
    df_avg = df_local.groupby(["dayIndex", "hour"])["power_Wh"].mean().reset_index()

    #Create the table if it doesn't exist
    cursor = conn.cursor()
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS PVGIS_sintesis_1 (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        dayIndex INTEGER,
        hour INTEGER,
        power_Wh REAL
    )
    ''')

    #Insert data into the table
    df_avg.to_sql('PVGIS_sintesis_1', conn, if_exists='replace', index=False)

    #Commit changes and close connection
    conn.commit()
    conn.close()
    print("Data successfully sintesis into SQLite PVGIS_sintesis from PVGIS!")

except Exception as err:
    print(f"Error from PVGIS_sintesis {err=}, {type(err)=}")