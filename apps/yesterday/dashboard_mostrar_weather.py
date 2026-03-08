import requests
import pandas as pd
import matplotlib.pyplot as plt
import sqlite3
import tkinter as tk
import numpy as np
from scipy.interpolate import make_interp_spline
from zoneinfo import ZoneInfo  # Use zoneinfo for Python 3.9+
from datetime import datetime
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import matplotlib.pyplot as plt
from tkcalendar import Calendar
from datetime import date
import mplcursors
import scipy.stats

def day_of_year_no_leap(date):
    """Compute day index (1-365) ignoring February 29"""
    #date = datetime.strptime(date_str, "%Y-%m-%d %H:%M:%S")
    
    # Adjust for leap years by skipping February 29
    day_index = date.timetuple().tm_yday
    if date.month > 2 and (date.year % 4 == 0 and (date.year % 100 != 0 or date.year % 400 == 0)):
        day_index -= 1  # Remove leap day offset
    
    return day_index

def mostrar_weather( frame, header):

    right_header_prompt = tk.Label(header, text="Relación solar radiation vs producción", bg="white", font=("Arial", 20))
    right_header_prompt.grid(row=0, column=0, sticky="new", padx=10, pady=5)

    try:
        # # Connect to the SQLite database
        conn = sqlite3.connect("measures.db")

        #sql = "select S.date as date, S.solar_Wh as solar_Wh, S.power_Wp as power_Wp, V.solarradiation as solarradiation from SWIBE_v as S, VXSING_hours as V where S.date = V.date and ORDER by s.date;"

        #sql = "select S.date as date, S.solar_Wh as solar_Wh, S.power_Wp as power_Wp, V.solarradiation as solarradiation from SWIBE_v as S, VXSING_hours as V where S.date = V.date and date(S.date) = '2024-09-30'" 

        #sql = "SELECT S.date, S.solar_Wh, S.power_Wp, V.solarradiation FROM SWIBE_v S JOIN VXSING_hours V ON DATE(S.date) = DATE(V.date) AND strftime('%H', S.date) = strftime('%H', V.date) ORDER BY S.date;"

        sql = f"SELECT date, cloudcover, solarradiation FROM VXSING_hours where solarradiation > 200 order by date;"
        vxsing = pd.read_sql_query(sql, conn, index_col=None, coerce_float=True, params=None, parse_dates=True, chunksize=None, dtype=None)
        vxsing["date"] = pd.to_datetime(vxsing["date"])
        vxsing["date"] = vxsing["date"].dt.tz_localize('Europe/Madrid')
        print (vxsing[vxsing['date'].dt.strftime("%Y-%m-%d") == '2024-09-30'].head(10))

        sql = f"SELECT date, solar_Wh, power_Wp FROM SWIBE_v where solar_Wh > 50 order by date;"
        swibe = pd.read_sql_query(sql, conn, index_col=None, coerce_float=True, params=None, parse_dates=True, chunksize=None, dtype=None)
        swibe["date"] = pd.to_datetime(swibe["date"])
        swibe["date"] = swibe["date"].dt.tz_localize('UTC')
        swibe["date"] = swibe["date"].dt.tz_convert('Europe/Madrid')
        
        print (swibe[swibe['date'].dt.strftime("%Y-%m-%d") == '2024-09-30'].head(10))
        # cursor = conn.cursor()
        # cursor.execute(sql)
        # print(cursor.fetchall())



    #     df = pd.read_sql_query(sql, conn, index_col=None, coerce_float=True, params=None, parse_dates=True, chunksize=None, dtype={
    #     "solar_Wh": int, 
    #     "power_Wp": float, 
    #     "solarradiation": float
    # })
    #     df["date"] = pd.to_datetime(df["date"])


    #     print(sql)
    #     print("df1\n", df[df["date"].dt.strftime("%Y-%m-%d") == '2024-09-30'])

        df = pd.merge(vxsing, swibe, on='date', how='inner' )
        # df["date"] = pd.to_datetime(df["date"])
        # df["dayIndex"] = df['date'].apply(day_of_year_no_leap)
        # df['hour'] = df['date'].dt.hour
        print("MERGE 1\n", df.head(5))

        # sql = f"SELECT * FROM PVGIS_sintesis_v"
        # sintesis = pd.read_sql_query(sql, conn, index_col=None, coerce_float=True, params=None, parse_dates=True, chunksize=None, dtype=None)
        # print(sql)
        # print("SINTESIS-\n", sintesis.head(5))
        # df = pd.merge(df, sintesis, on=['dayIndex','hour'])
        # df['power_Wh'] = df['power_Wh'] * df['power_Wp']

        # # Define the local timezone (e.g., Madrid, Spain)
        # local_zone = ZoneInfo("Europe/Madrid")
        # # Convert UTC timestamps to local timezone
        # df["date"] = df["date"].dt.tz_localize("UTC").dt.tz_convert(local_zone)

        #Unify power from original solar installation in 3.9kWp to new 6.6kWp
        df['solar_Wh'] = df['solar_Wh'] / df['power_Wp'] * 6.6
        df_final = df[df["solar_Wh"] > 5] #filter SWIBE error
        #df_final = df_final[df_final['date'].dt.strftime("%Y-%m-%d") == '2024-09-30']
        print(df_final)


        print(f"Numero de elementos considerados: {len(df_final)} desde {df_final['date'].min()} hasta {df_final['date'].max()}")

        # Perform linear regression
        slopeEnergy, interceptEnergy, r_valueEnergy, p_valueEnergy, std_errEnergy = scipy.stats.linregress(df_final["solarradiation"], df_final["solar_Wh"])

        # Calculate predicted values
        print(f"Equation -> WIBEE production (Wh) = {interceptEnergy:.2f} {slopeEnergy:.2f} * VXSING radiation\nstd_error: {std_errEnergy:.2f}\nr_value: {r_valueEnergy}\np_value:{p_valueEnergy}")

        # Create correlation line
        correlation_line = slopeEnergy * df_final["solarradiation"] + interceptEnergy
          
        figura = plt.figure(figsize=(10,5))
        # Plot scatter points
        plt.scatter(df_final["solarradiation"], df_final["solar_Wh"], color='blue', label='WIBEE')
  
        # Plot correlation line
        plt.plot(df_final["solarradiation"], correlation_line, color='red', label=f'Correlation Line: y = {interceptEnergy:.2f} + {slopeEnergy:.2f}x')

        # Add labels, legend, and title
        plt.xlabel('Solar radiation')
        plt.ylabel('Produccion (Wh)')
        plt.title('Scatter Plot with Correlation Line')
        plt.legend()

        # Enable tooltips using mplcursors
        cursor = mplcursors.cursor(hover=True)
        @cursor.connect("add")
        def on_add(sel):
            index = int(round(sel.index))  # Get the index of the hovered point
            sel.annotation.set_text(f"Date: {df_final['date'].iloc[index]}\n WIBEE:{df_final['solar_Wh'].iloc[index]:.0f} Wh- VXING: {df_final['solarradiation'].iloc[index]:.0f} W/m2")  # Set the tooltip text
            bbox = sel.annotation.get_bbox_patch()
            bbox.set_facecolor("lightblue")  # Change background color
            bbox.set_alpha(1) 

        # figura = plt.figure(figsize=(10,5))
        # plt.plot(df["date"], df["power_Wh"], marker="o", linestyle="-", label="PVGIS")
        # plt.plot(df["date"], df["solarradiation"], marker="o", linestyle="-", label="solarradiation")
        # plt.plot(df["date"], df["solar_Wh"], marker="o", linestyle="-", label="WIBEE")
        # plt.xlabel("Day")
        # plt.xticks(df["date"])
        # plt.ylabel("Energia")
        # plt.legend()
        # plt.xticks(rotation=45)  # Rotate x-axis labels for better readability
        # plt.grid(True)  # Add grid
        # #plt.show()

        # Mostrar el gráfico en el frame derecho
        canvas = FigureCanvasTkAgg(figura, master=frame)
        canvas.get_tk_widget().pack(fill="both", expand=True)
        canvas.draw()

    except Exception as err:
    # Crear un Label para mostrar el mensaje
        label = tk.Label(frame, 
                         text=f"Error de GRAPH {err=}, {type(err)=}", font=("Arial", 12), bg="white", fg="red")
        label.pack(fill="both", expand=True)
        print(f"Error de GRAPH {err=}, {type(err)=}")

