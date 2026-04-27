import pandas as pd
import calendar

from datetime import datetime, date
import pytz

from dashboard.comun.date_conditions import periodo_2_0TD
from dashboard.comun.sql_utilities import read_sql_ts
from dashboard.comun.get_ESIOS_data import get_ESIOS_spot

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

def mostrar_factura(conn, month, year, source):

    mes_factura = f"{year}-{month:02d}"
    _ , days_in_month = calendar.monthrange(year, month)

    tz = pytz.timezone("Europe/Madrid")

    # Primer instante del mes en hora local → UTC
    start_local = tz.localize(datetime(year, month, 1))
    # Primer instante del mes siguiente → UTC
    if month == 12:
        end_local = tz.localize(datetime(year + 1, 1, 1))
    else:
        end_local = tz.localize(datetime(year, month + 1, 1))
    print("LOCAL",start_local, end_local)
    start_utc = start_local.astimezone(pytz.utc).strftime("%Y-%m-%d %H:%M:%S")
    end_utc   = end_local.astimezone(pytz.utc).strftime("%Y-%m-%d %H:%M:%S")

    print("UTC", start_utc,end_utc)
    try:
        if (source == 'DATADIS'):
            query = f"SELECT datetime, consumption_Wh as consumo, surplus_Wh as excedente from DATADIS_v where datetime >= ? and datetime < ?"
            energy = pd.read_sql(query, conn, params=(start_utc, end_utc), index_col="datetime", parse_dates="datetime")

        else:
            query = "SELECT datetime, general_Wh / 1000. as general_Wh from WIBEE where datetime >= ? and datetime < ?"
            energy = pd.read_sql(query, conn, params=(start_utc, end_utc), index_col="datetime", parse_dates="datetime")
            energy[["consumo", "excedente"]] = energy["general_Wh"].apply(compute_values)

        energy["local_time"] = energy.index.tz_localize("UTC").tz_convert(tz)
        energy['tarifa'] = energy["local_time"].apply(periodo_2_0TD)
        if energy.empty:
            raise ValueError("The Source DataFrame is empty!")

    # Buscamos los precios
        if year <= 2025:
            tabla = "SOM_precios_indexada_real"
        else:
            tabla = "SOM_precio_indexada"

        query = f"SELECT * from {tabla} where datetime >= ? and datetime < ?"
        prices_Som =  pd.read_sql(query, conn, params=(start_utc, end_utc), index_col="datetime", parse_dates="datetime")
        if prices_Som.empty:
            raise ValueError("The Som Prices DataFrame is empty!")
        
        col = '"Mercado SPOT"'
        query = f"SELECT datetime, {col} from  ESIOS_data where datetime >= ? and datetime < ?"
        prices_SPOT = pd.read_sql(query, conn, params=(start_utc, end_utc), index_col="datetime", parse_dates='datetime')

        if prices_SPOT.empty:
            raise ValueError("The SPOT Prices DataFrame is empty!")
        prices_SPOT['Mercado SPOT'] = prices_SPOT['Mercado SPOT'] / 1000   
        prices_20TD = {'P1':0.229,'P2':0.153,'P3':0.125, 'Excedente':0.03}
        df_cost = energy.join([prices_Som, prices_SPOT], how='inner')
               
        def calcular_coste(row):
            consumo = row['consumo']
            excedente = row['excedente']
            precio_cargo = row['price']
            if excedente > 0:
                return pd.Series({
                    'cargo': 0,
                    'cargo_20TD': 0,
                    'compensacion': excedente * row['Mercado SPOT'],
                    'compensacion_20TD': excedente * prices_20TD['Excedente']
                })
            else:
                return pd.Series({
                    'cargo': consumo * precio_cargo,
                    'cargo_20TD': consumo * prices_20TD[row['tarifa']],
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

        # Group by month and sum values
        # df_monthly = df_cost.groupby(df_cost['datetime'].dt.to_period('M'))['costDay'].sum().reset_index()
        # df_monthly['datetime'] = df_monthly['datetime'].astype(str)
        df_monthly = df_cost

        euro_coste = df_monthly['cargo'].sum()
        euro_coste_20TD = df_monthly['cargo_20TD'].sum()
        euro_excedente = df_monthly['compensacion'].sum()
        euro_excedente_20TD = df_monthly['compensacion_20TD'].sum()
        
        total_energy = energy['consumo'].sum()
        total_excedente = energy['excedente'].sum()

        bono_social = cteBonoSocial * days_in_month

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
            
