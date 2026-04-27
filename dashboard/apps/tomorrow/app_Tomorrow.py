import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parents[2]))  # sube hasta la raíz del repo

import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import pytz

import dashboard.apps.config as TCB

from dashboard.comun import date_conditions as dc
from dashboard.comun import sql_utilities as db
from dashboard.comun.get_user_location import borrar_user_location, get_user_location

from dashboard.comun.grafico_openmeteo import grafica_openmeteo
from dashboard.comun.grafico_prices_Som import grafico_prices_Som
from dashboard.comun.grafico_solar_today import grafico_solar_today
from dashboard.comun.grafico_prices_forecast import grafico_prices_forecast

# Función para centrar el texto de los headers
def header_centrado(texto):
    st.markdown(
        f"<h2 style='text-align: center;'>{texto}</h2>",
        unsafe_allow_html=True
    )
# =========================
# Rango temporal de analisis hoy menos 5 dias y hoy mas 10 dias en futuro
# =========================
tz = pytz.timezone("Europe/Madrid")
today = tz.localize(datetime.now().replace(minute=0, second=0, microsecond=0))
start_date = today + timedelta(days=-5)
end_date = today + timedelta(days=10)
# Para probar fechas fijas
# start_date = tz.localize( datetime(2026, 1, 1).replace(minute=0, second=0, microsecond=0))
# end_date = tz.localize( datetime(2026, 1, 8).replace(minute=0, second=0, microsecond=0))
rango = {
    "start_date": start_date,
    "end_date": end_date,
}
conn, error = db.init_db() # Inicializar acceso a la base de datos
if conn is None:
    st.error(f"Error al conectar a la base de datos: {error}")
    sys.exit(1)
    
dc.date_conditions_init(rango)  # Inicializar condiciones de fecha (festivos, fines de semana, hoy)
# =========================
#Definicion de estilos CSS para hacer el dashboard responsive y convertir los paneles a una sola columna si el ancho de pantalle es < 700px
# =========================
st.markdown("""
<style>
@media (max-width: 700px) {
    .stColumn {
        flex-direction: column !important;
    }
}
</style>
""", unsafe_allow_html=True)
# ---------------------------------------------------------
# TÍTULO PRINCIPAL
# ---------------------------------------------------------
st.set_page_config(layout="wide")

st.title(f"Dashboard Meteorológico y de Precios de la Energía - {today.strftime('%Y-%m-%d %H:%M')}")
# ---------------------------------------------------------
# Obtenemos localizacion del usuario para utilizar en meteo y pvgis.
# Si no se obtiene autorizaci
# Se ofrece un botón para borrar la cookie y olvidar la ubicación.
# ---------------------------------------------------------
lat, lon = get_user_location()
if lat is None or lon is None:
    st.warning("No se pudo obtener la localización.")
    colA, colB = st.columns(2)
    #si no hay geolocalizacion usamos la Puerta del Sol de Madrid 
    with colA: lat = st.number_input("Latitud", value=TCB.PUERTA_SOL["lat"]) 
    with colB: lon = st.number_input("Longitud", value=TCB.PUERTA_SOL["lon"])
# ---------------------------------------------------------
# Mostrar la localización lat, lon y ofrecer opción de borrar cookie
#- ---------------------------------------------------------
col1, col2 = st.columns([4,1])
with col1:
    st.success(f"📍Localización de trabajo: {float(lat):.4f}, {float(lon):.4f}")
with col2:
    borrar = st.button("🗑️ Olvidar mi ubicación") 
    if borrar: 
        borrar_user_location()
# ---------------------------------------------------------
# Opciones para mostrar u ocultar cada panel
# ---------------------------------------------------------
col1, col2, col3 = st.columns(3)
with col1:
    mostrar_precios = st.checkbox("Mostrar precios horarios (Som Energia)", value=True)
with col2:
    mostrar_meteo = st.checkbox("Mostrar forecast meteorológico (Open‑Meteo)", value=True)
with col3:
    mostrar_solar = st.checkbox("Mostrar forecast produccion fotovoltaica hoy", value=False)
# ---------------------------------------------------------
# PANEL PRECIOS
# ---------------------------------------------------------
if mostrar_precios:
    header_centrado("⚡ Estimación de Precios horarios")
    col1, col2 = st.columns(2)
    # Precios Som Energia
    with col1:
        st.header("Precios [SOM Energia](https://www.somenergia.coop/es)")
        with st.expander("ℹ️ Ver nota"):
            st.write("""
            Los precios mostrados en este gráfico provienen del API de Som Energía que retorna los precios estimados de la tarifa indexada de la cooperativa para hoy y a partir de las 14:00 los precios para el día de mañana.
            """)
        fig_precios, error = grafico_prices_Som()
        if error:
            st.error(error)
        else:
            st.plotly_chart(fig_precios, width='stretch', config={"renderer": "svg"})

    # Precios estimados según ESIOS
    with col2:
        st.header("Predicción Precios [ESIOS](https://www.esios.ree.es/es)")
        with st.expander("ℹ️ Ver nota"):
            st.write("""
            Los precios estimados en este gráfico se han calculado asumiendo una relación entre el precio final de la energía en el mercado spot diario y el porcentaje de energía eólica + fotovoltaica (prevista a varios días en la plataforma ESIOS según indicadores 541 y 542) sobre la demanda total (prevista a un dia en la plataforma ESIOS según indicador 603).
            Solo es válida la forma de la curva y sirve para detectar puntos de precios muy altos o bajos.
            Cuando la curva de precios estimados es muy negativa es probable que el precio real sea cercano a cero.
            """)
        fig_forecast, error = grafico_prices_forecast(conn, rango)
        if error:
            st.error(error)
        else:
            st.plotly_chart(fig_forecast, width='stretch', config={"renderer": "svg"})
# ---------------------------------------------------------
# PANEL METEO
# ---------------------------------------------------------
if mostrar_meteo:
    header_centrado("Forecast meteo by <a href='https://open-meteo.com' target='_blank'>Open-Meteo</a>")
    col1, col2 = st.columns(2)
    # Panel Forecast 7 dias
    with col1:
        st.header("📅 Forecast 7 dias")
        fig_meteo_7D, error = grafica_openmeteo(lat,lon,TCB.AZIMUTH)
        if error:
            st.error(error)
        else:
            st.plotly_chart(fig_meteo_7D, width='stretch', config={"renderer": "svg"})  
    # Panel Próximas X horas segun slider
    with col2:
        col21, col22 = st.columns([3,1])
        horas = 12
        with col22:
            horas = st.slider("Horizonte horario(h)", 12, 120, 24)
        with col21:
            st.header(f"⏱️ Próximas {horas} horas")
        fig_horas, error = grafica_openmeteo(lat,lon,TCB.AZIMUTH, time_unit=horas)
        if error:
            st.error(error)
        else:
            st.plotly_chart(fig_horas, width='stretch', config={"renderer": "svg"})
# ---------------------------------------------------------
# Panel predicción PVGIS
# ---------------------------------------------------------
if mostrar_solar:
    header_centrado("Predicción producción fotovoltaica de hoy")
    with st.expander("ℹ️ Ver nota"):
        st.write("""
        A continuación se muestra la curva de potencia disponible en los paneles solares por cada kWp instalado según la plataforma PVGIS asumiendo condiciones ideales de los paneles solares en cuanto a orientación e inclinación, datos historicos reales de WIBEE y producción actual de WIBEE para hoy.
        Si has autorizado la geolocalización, la curva se ajustará a tu ubicación. Si no, se mostrará la predicción para la Puerta del Sol de Madrid (40.4169, -3.7038).
        """)

    fig_solar, error = grafico_solar_today(conn, method="lr")
    if error:
        st.error(error)
    else:
        st.plotly_chart(fig_solar, width='stretch', config={"renderer": "svg"})