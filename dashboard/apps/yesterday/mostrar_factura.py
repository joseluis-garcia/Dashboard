import pandas as pd
from dashboard.comun.sql_utilities import read_sql_ts
import tkinter as tk
from tkinter import ttk
import sqlite3
from datetime import datetime, date
from tkcalendar import Calendar
import calendar
from dashboard.comun.date_conditions import periodo_2_0TD

# # List of months
# months = [
#     "January", "February", "March", "April", "May", "June",
#     "July", "August", "September", "October", "November", "December"
# ]

potenciaContratada_valle = 8
potenciaContratada_punta = 6
precio_valle = 2.955
precio_punta = 29.934
impuesto_electricidad = 5.11269
SOMCorrection = 0.02  #Subida del precio que da la web de SOM
cteBonoSocial = 0.012742
precio_excedente = 0.015
source = 'WIBEE'

def compute_values(x):
    if (x > 0):
        consumo = x
        excedente = 0
    else:
        consumo = 0
        excedente = -x

    return pd.Series([consumo, excedente])  # Return as Series

def mostrar_factura(conn, month, year):

    mes_factura = f"{year}-{month:02d}"
    _ , days_in_month = calendar.monthrange(year, month)
    try:
        if (source == 'DATADIS'):
            query = f"SELECT datetime, consumption_Wh as consumo, surplus_Wh as excedente from DATADIS_v where strftime('%Y-%m', datetime) = '{mes_factura}';"
            energy = read_sql_ts(query, conn)
        else:
            query = f"SELECT datetime, general_Wh from WIBEE where strftime('%Y-%m', datetime) = '{mes_factura}';"
            energy = read_sql_ts(query, conn)
            energy[["consumo", "excedente"]] = energy["general_Wh"].apply(compute_values)

        energy['tarifa'] = energy.index.map(lambda x:periodo_2_0TD(x))
        print(query)         
        print("Consumo", energy['consumo'].sum())
        print("Excedente", energy['excedente'].sum())    
        print( energy.head(24))

        if energy.empty:
            raise ValueError("The Source DataFrame is empty!")

    # Buscamos los precios

        if year <= 2025:
            tabla = "SOM_precios_indexada_real"
        else:
            tabla = "SOM_precio_indexada"

        query = f"SELECT * from {tabla} where strftime('%Y-%m', datetime) = '{mes_factura}';"

        print(query)
        prices = read_sql_ts(query, conn)

        if prices.empty:
            raise ValueError("The Prices DataFrame is empty!")
    

        #prices['datetime'] = pd.to_datetime(prices['datetime'], format='%Y-%m-%d %H:%M:%S', errors='coerce')
        print("Prices\n")
        print(prices)

        price_20TD = {'P1':0.229,'P2':0.153,'P3':0.125, 'Excedente':0.03}
        # #Ensure that the date columns are the same format
        # energy['datetime'] = pd.to_datetime(energy['datetime'])
        # prices['datetime'] = pd.to_datetime(prices['datetime'])

        # # Set the date columns as index to align both DataFrames on date
        # energy.set_index('datetime', inplace=True)
        # prices.set_index('datetime', inplace=True)

        # Perform the multiplication on the numeric columns only
        # df_cost = energy.multiply(prices)
        df_cost = energy.merge(prices, left_index=True, right_index=True, how='inner')
        print(df_cost.head(5))

        # Reset the index to bring 'date' back as a column
        # df_cost.reset_index(inplace=True)
        # energy.reset_index(inplace=True)

        def calcular_coste(row):
            consumo = row['consumo']
            excedente = row['excedente']
            precio_cargo = row['price']
            if excedente > 0:
                return pd.Series({
                    'cargo': 0,
                    'cargo_20TD': 0,
                    'compensacion': excedente * precio_excedente / 1000,
                    'compensacion_20TD': excedente * price_20TD['Excedente'] / 1000
                })
            else:
                return pd.Series({
                    'cargo': consumo * precio_cargo / 1000,
                    'cargo_20TD': consumo * price_20TD[row['tarifa']] / 1000,
                    'compensacion': 0,
                    'compensacion_20TD': 0
                })
            
        df_cost[['cargo', 'cargo_20TD','compensacion','compensacion_20TD']] = df_cost.apply(calcular_coste, axis=1)
        # Separate date column and sort the rest numerically
        # non_date_cols = [col for col in df_cost if col != "datetime"]  # Exclude "date"
        # sorted_cols = ["datetime"] + sorted(non_date_cols, key=int) 
        # df_cost=df_cost[sorted_cols]

        # Show the result
        #df_cost["costDay"] = df_cost.drop(columns="datetime").sum(axis=1)
        print("COST:\n", df_cost)

        # Group by month and sum values
        # df_monthly = df_cost.groupby(df_cost['datetime'].dt.to_period('M'))['costDay'].sum().reset_index()
        # df_monthly['datetime'] = df_monthly['datetime'].astype(str)
        df_monthly = df_cost

        print("Monthly:\n", df_monthly)
        euro_coste = df_monthly['cargo'].sum()
        euro_coste_20TD = df_monthly['cargo_20TD'].sum()
        euro_excedente = df_monthly['compensacion'].sum()
        euro_excedente_20TD = df_monthly['compensacion_20TD'].sum()
        
        #df_monthly['energy'] = df_energy['consumo'].sum()
        total_energy = energy['consumo'].sum() / 1000
        total_excedente = energy['excedente'].sum() / 1000

        bono_social = cteBonoSocial * days_in_month

        print("MONTHLY", df_monthly, "TOTAL", total_energy)

        # Insert text with formatting
        reporte = f"Factura del mes de {mes_factura}\n\n"
        reporte += f"Dias {days_in_month}\n\n"
        coste_valle = potenciaContratada_valle * precio_valle * days_in_month / 365
        coste_punta =  potenciaContratada_punta * precio_punta * days_in_month / 365
        reporte += f"PotenciaContratada valle { potenciaContratada_valle}kW ({precio_valle} €/kW/año) => {coste_valle:.2f} \n\n"
        reporte += f"PotenciaContratada punta { potenciaContratada_punta}kW ({precio_punta} €/kW/año) => {coste_punta:.2f} \n\n"
        reporte += f"Total termino de potencia: {(coste_valle + coste_punta):.2f} €\n\n"
        reporte += f"Energía total consumida: {total_energy:.2f} kWh\n\n"
        reporte += f"Precio de la energía indexada: {euro_coste:.2f} €\n\n"
        reporte += f"Precio de la energía 2.0TD: {euro_coste_20TD:.2f} €\n\n"

        reporte += f"Bono social: {bono_social:.2f} €\n\n"

        reporte += f"Energía total excedentaria: {total_excedente:.2f} kWh\n\n"
        reporte += f"Compensación excedentes: {euro_excedente:.2f} €\n\n"
        reporte += f"Compensación excedentes 20TD: {euro_excedente_20TD:.2f} €\n\n"

        total_preImpuesto = coste_valle + coste_punta + euro_coste + bono_social - euro_excedente
        impuestoElectricidad = total_preImpuesto * impuesto_electricidad / 100
        reporte += f"Impuesto electricidad: ({total_preImpuesto:.2f} € *{impuesto_electricidad}%) => {impuestoElectricidad:.2f} €\n\n"

        total_preIVA = total_preImpuesto + impuestoElectricidad
        IVA = total_preIVA * 0.21
        reporte += f"IVA: {IVA:.2f} €\n\n"
        reporte += f"Total: {total_preIVA + IVA:.2f} €\n\n"
        return reporte

    except Exception as err:
    # Crear un Label para mostrar el mensaje

        print(f"Error de Factura {err=}, {type(err)=}")
            
