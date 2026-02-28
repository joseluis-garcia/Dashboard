import streamlit as st
import pandas as pd
import comun.date_conditions as dc
from datetime import date, datetime, timedelta
import pytz
from comun.async_tasks import run_async, async_placeholder
from comun.get_ESIOS_data import get_ESIOS_energy, get_ESIOS_spot
from comun.get_user_location import borrar_user_location, get_user_location
from comun.get_prices_Som import grafico_prices_Som, get_prices_Som
from comun.get_prices_forecast import get_prices_forecast, grafico_prices_forecast
from comun.get_openmeteo import (get_meteo_7D, get_meteo_hours, grafica_meteo)
from comun.get_PVGIS import (get_PVGIS_data, grafico_PVGIS)

Puerta_Sol = dict(lat=40.4169, lon=-3.7033)

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
# rango = {
#     "start_date": start_date.isoformat(),
#     "end_date": end_date.isoformat(),
# }
rango = {
    "start_date": start_date,
    "end_date": end_date,
}
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
st.title("Dashboard Meteorológico y de Precios de la Energía")
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
    with colA: lat = st.number_input("Latitud", value=Puerta_Sol["lat"]) 
    with colB: lon = st.number_input("Longitud", value=Puerta_Sol["lon"])
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
    mostrar_PVGIS = st.checkbox("Mostrar forecast produccion fotovoltaica (PVGIS)", value=False)
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
        df_precios, error = get_prices_Som()
        if error:
            st.error("No se han podido obtener los precios de SOM Energia.")
            st.error(error)
        else:
            fig_precios = grafico_prices_Som(df_precios)
            st.plotly_chart(fig_precios, width='stretch')

    # Precios estimados según ESIOS
    with col2:
        st.header("Predicción Precios [ESIOS](https://www.esios.ree.es/es)")
        with st.expander("ℹ️ Ver nota"):
            st.write("""
            Los precios estimados en este gráfico se han calculado asumiendo una relación entre el precio final de la energía en el mercado spot diario y el porcentaje de energía eólica + fotovoltaica (prevista a varios días en la plataforma ESIOS según indicadores 541 y 542) sobre la demanda total (prevista a un dia en la plataforma ESIOS según indicador 603).
            Solo es válida la forma de la curva y sirve para detectar puntos de precios muy altos o bajos.
            Cuando la curva de precios estimados es muy negativa es probable que el precio real sea cercano a cero.
            """)
        df_energy, error = get_ESIOS_energy(rango)
        if error:
            st.error("No se han podido obtener los datos de energía de ESIOS.")
            st.error(error)
        else:
            df_spot, error = get_ESIOS_spot(rango)
            if error:
                st.error("No se han podido obtener los datos de precio spot de ESIOS.")
                st.error(error)
            else:
                df_final = get_prices_forecast(df_energy, df_spot)
                fig_forecast = grafico_prices_forecast(df_final)
                st.plotly_chart(fig_forecast, width='stretch', config={"renderer": "svg"})
# ---------------------------------------------------------
# PANEL METEO
# ---------------------------------------------------------
if mostrar_meteo:
    azimuth = -45
    df_7D, error = get_meteo_7D(lat, lon, azimuth)
    if error:
        st.error("No se han podido obtener los datos meteorológicos de Open-Meteo.")
        st.error(error)
    else:
        header_centrado("Forecast meteo by <a href='https://open-meteo.com' target='_blank'>Open-Meteo</a>")
        col1, col2 = st.columns(2)
        # Panel Forecast 7 dias
        with col1:
            st.header("📅 Forecast 7 dias")
            fig_meteo_7D = grafica_meteo(df_7D)
            st.plotly_chart(fig_meteo_7D, width='stretch')  
        # Panel Próximas X horas segun slider
        with col2:
            col21, col22 = st.columns([3,1])
            horas = 12
            with col22:
                horas = st.slider("Horizonte horario(h)", 12, 120, 24)
            with col21:
                st.header(f"⏱️ Próximas {horas} horas")
            df_horas = get_meteo_hours(df_7D, horas)
            fig_horas = grafica_meteo(df_horas)
            st.plotly_chart(fig_horas, width='stretch')
# ---------------------------------------------------------
# Panel predicción PVGIS
# ---------------------------------------------------------
if mostrar_PVGIS:
    header_centrado("Predicción producción fotovoltaica de hoy según <a href='https://joint-research-centre.ec.europa.eu/photovoltaic-geographical-information-system-pvgis_en' target='_blank'>PVGIS</a>")
    with st.expander("ℹ️ Ver nota"):
        st.write("""
        A continuación se muestra la curva de potencia disponible en los paneles solares por cada kWp instalado según la plataforma PVGIS asumiendo condiciones ideales de los paneles solares en cuanto a orientación e inclinación.
        Si has autorizado la geolocalización, la curva se ajustará a tu ubicación. Si no, se mostrará la predicción para la Puerta del Sol de Madrid (40.4169, -3.7038).
        """)
# 1) Lanzar la tarea en segundo plano
    task_key = f"pvgis_{lat}_{lon}"
    run_async(task_key, get_PVGIS_data, lat, lon, date.today())
# 2) Renderizar según estado
    def render_pvgis(df):
        #sunData = getSunData(lat, lon, date.today()) 
        #fig = grafico_PVGIS(df, sunData) 
        fig = grafico_PVGIS(df, lat, lon, date.today())
        st.plotly_chart(fig, width='stretch', config={"renderer": "svg"})
    async_placeholder( task_key, render_pvgis, loading_message="Obteniendo datos de PVGIS…" )