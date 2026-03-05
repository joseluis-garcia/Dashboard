import sys
from pathlib import Path
import pandas as pd
import sqlite3
import requests
from datetime import datetime, timedelta
# Añadir la raíz del repo al PYTHONPATH
repo_root = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(repo_root))
import comun.sql_utilities as db

conn, error = db.init_db()
url = "https://api.somenergia.coop/data/indexed_prices?tariff=2.0TD&geo_zone=PENINSULA"

# Fetch the data from the server
response = requests.get(url)
if response.status_code == 200:
    tarifa = response.json()
    firstDate = datetime.strptime(tarifa['data']['first_date'],'%Y-%m-%d %H:%M:%S')
    lastDate =  datetime.strptime(tarifa['data']['last_date'],'%Y-%m-%d %H:%M:%S')

    currentDate = firstDate  + timedelta(hours=-1)
    prices = []

    for price in tarifa['data']['curves']['price_euros_kwh']:
        if price is None:
            continue
        else:
            dd = currentDate.strftime("%Y-%m-%d")
            unitP = {"date": dd, "hour": currentDate.hour, "price": price}
            prices.append(unitP)
            currentDate = currentDate + timedelta(hours=1)

    df = pd.DataFrame(prices)
    df["date"] = pd.to_datetime(df["date"])

    df_pivot = df.pivot(index="date", columns="hour", values="price").reset_index()

    # Connect to SQLite database
    #conn = sqlite3.connect("../data/measures.db")

    #Previous data recorded until
    df = pd.read_sql_query("SELECT MAX(date) as maxDate FROM SOM_precios_h", conn, parse_dates=["maxDate"])
    df["maxDate"] = pd.to_datetime(df["maxDate"])
    maxDate = df["maxDate"].iloc[0]

    df_pivot['date'] = pd.to_datetime(df_pivot['date'], format='%Y-%m-%d')
    print(df_pivot.head())
    df_pivot = df_pivot[df_pivot['date']> maxDate]
    df_pivot["date"] = pd.to_datetime(df_pivot["date"]).dt.strftime("%Y-%m-%d")

    if (df_pivot.empty):
        print ("No data available after ", maxDate.strftime("%Y-%m-%d"))
    else:
        # Insert data into the table
        df_pivot.to_sql('SOM_precios_h', conn,if_exists="append", index=False)
        print(f"Data updated since {maxDate.strftime('%Y-%m-%d')} to {df_pivot['date'].max()}")

        # Commit changes and close connection
        conn.commit()
        conn.close()

else:
    print("Error de SOM Prices:" + response)

