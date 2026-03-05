import streamlit as st
import pandas as pd
import tkinter as tk
from tkinter import ttk
import sqlite3
from datetime import datetime
import numpy as np
import pytz
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import calendar
import mplcursors
import scipy.stats

def cleanSolar( row):
    return row['extra_Wh'] - row['solar_Wh'] if row['extra_Wh'] > row['solar_Wh'] else 0

def mostrar_energia_mes():

    # Connect to SQLite database
    conn = sqlite3.connect("measures.db")

    #Previous data recorded until
    query = "SELECT date, solar_Wh, power_Wp from SWIBE_v"
    swibe = pd.read_sql_query(query, conn, parse_dates=["date"])
    swibe['date'] = pd.to_datetime(swibe['date'], format='%Y-%m-%d', errors='coerce')

    dateMin = swibe['date'].min().year
    dateMax = swibe['date'].max().year
    print(f"SWIBE since {dateMin} to {dateMax}")

    swibe['year'] = swibe['date'].dt.year
    swibe['month'] = swibe['date'].dt.month
    swibe['solar_Wh'] = swibe['solar_Wh'] / swibe['power_Wp'] / 1000 * 6.6
    swibe.drop(columns='date')

    df_monthly = swibe.groupby([swibe["year"], swibe["month"]])["solar_Wh"].sum().reset_index()
    df_monthly_t = df_monthly.pivot(index="year", columns ="month", values= "solar_Wh").reset_index()

    # Compute min, mean, and max
    
    min_values = df_monthly_t.iloc[:, 1:].min(axis=0).tolist()   # Min per month
    mean_values = df_monthly_t.iloc[:, 1:].mean(axis=0).tolist() # Mean per month
    max_values = df_monthly_t.iloc[:, 1:].max(axis=0).tolist()   # Max per month
    df_monthly_t["Total"] = df_monthly_t.iloc[:, 1:].sum(axis=1)

    print("MONTHLY_T",df_monthly_t, min_values, mean_values, max_values)
    df_monthly_avg = df_monthly.groupby([df_monthly['month']])['solar_Wh'].mean().reset_index()

    print("MONTHLY",df_monthly)
    print("MONTHLY_AVG", df_monthly_avg)
    df_current_year = df_monthly[df_monthly['year'] == datetime.now().year]

    figura, ax1 = plt.subplots()
    # Add labels, legend, and title
    plt.xlabel('Mes')
    plt.ylabel('Produccion (kWh)')
    months = list(range(1, 13))  # Months 1-12
    ax1.set_xticks(months)

    # Plot scatter points
    ax1.plot(df_current_year["month"], df_current_year["solar_Wh"], marker="o", linestyle="-", label="Producción", color='blue')
    ax1.plot(months, min_values, marker="o", linestyle="-", label="Mínimo", color='red')
    ax1.plot(months, max_values, marker="o", linestyle="-", label="Máximo", color='green')
    ax1.plot(months, df_monthly_avg['solar_Wh'], marker="o", linestyle="dotted", label="Promedio", color='black')
    # Fill area between y1 and y2
    ax1.fill_between(months, min_values, max_values, color="gray", alpha=0.3)    
    # Optional: Rotate labels for better readability
    ax1.set_xticks(months)  # Set tick positions
    ax1.set_xticklabels([calendar.month_abbr[m] for m in months])  # Short month names (Jan, Feb, ...)
    plt.xticks(rotation=45)
    plt.legend()
    plt.grid(True)

    st.subheader("Mapa de temperaturas y precios históricos")
    st.pyplot(figura, width='stretch')

    column_config = { col: st.column_config.NumberColumn(col, format="%.0f") for col in df_monthly_t.select_dtypes(include="number").columns } 
    st.data_editor(df_monthly_t, hide_index=True, column_config=column_config)

        # column_config={
        #     "date": st.column_config.TextColumn(
        #         "Fecha",
        #         width="medium"
        #     ),
        #     "costDay": st.column_config.NumberColumn(
        #         "Precio",
        #         format="%.2f €"
        #     ),

        #     "energyDay": st.column_config.NumberColumn(
        #         "Consumo",
        #         format="%.2f kWh"
        #     )
        # }
    


    # # Crear el Treeview para la tabla
    # tabla = ttk.Treeview(frame)

    # # Definir encabezados de la tabla
    # tabla['columns'] = list(df_monthly_t.columns)
    # # Format Columns
    # tabla.column("#0", width=0, stretch=tk.NO)  # Hide default empty column
    # for col in df_monthly_t.columns:
    #     tabla.column(col, anchor=tk.CENTER, width=80)
    #     tabla.heading(col, text=col, anchor=tk.CENTER)

    # # Insert data into the table
    # for index, row in df_monthly_t.iterrows():
    #     formatted_row = [int(row['year'])] + [f"{int(value)}" if not pd.isna(value) else "NaN" for value in row[1:]]
    #     tabla.insert("", "end", values=formatted_row)

    
    # avg_values = ["Media"] + [f"{int(value)}" if not pd.isna(value) else "NaN" for value in mean_values] 
    # tabla.insert("", "end", values=avg_values, tags=("summary",))

    # # Apply Formatting for Summary Row
    # tabla.tag_configure("summary", background="lightgray", font=("Arial", 12, "bold"))
    # # Add the Treeview widget to the frame
    # tabla.pack(fill="both", expand=True)
