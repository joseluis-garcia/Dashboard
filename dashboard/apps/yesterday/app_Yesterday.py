import pandas as pd
import streamlit as st
import sys
from datetime import datetime

from dashboard.apps.yesterday.analysis_energy_spot_correlation import grafico_prediccion_energia
from dashboard.apps.yesterday.analysis_power_weather_correlation import grafico_prediccion_simple
import dashboard.comun.sql_utilities as db


from dashboard.comun.mensaje import render_df_proportional
from dashboard.apps.yesterday.energia_mes import get_energia_mes, grafico_energia_mes
from dashboard.comun.grafico_solar_today import grafico_solar_today
from dashboard.apps.yesterday.mostrar_factura import mostrar_factura
from dashboard.apps.yesterday.aerotermia import get_aerotermia_data, grafico_aerotermia, tabla_aerotermia
from dashboard.apps.yesterday.power_weather_correlation import power_weather_correlation, grafico_prediccion

from dashboard.comun.get_openmeteo import update_openmeteo_history
from dashboard.comun.get_Som_data import update_Som_history
from dashboard.comun.get_ESIOS_data import update_ESIOS_history
from dashboard.comun.get_WIBEE_data import update_WIBEE_history

conn, error = db.init_db()
if conn is None:
    st.error(f"Error al conectar a la base de datos: {error}")
    sys.exit(1)
# =========================
# DEFINICION UI
# =========================
st.markdown("""
<style>

/* Contenedor general de las tabs */
.stTabs [data-baseweb="tab-list"] {
    gap: 14px !important;                 /* separación entre pestañas */
    padding-top: 6px !important;
    padding-bottom: 6px !important;
}

/* Cada pestaña (texto y padding) */
.stTabs [data-baseweb="tab"] {
    font-size: 22px !important;           /* tamaño del texto */
    font-weight: 600 !important;          /* grosor */
    padding: 12px 22px !important;        /* tamaño de la pestaña */
    border-radius: 6px !important;
}

/* Pestaña seleccionada */
.stTabs [aria-selected="true"] {
    background-color: #1f77b4 !important; /* color de fondo */
    color: white !important;              /* color del texto */
}

/* Pestañas no seleccionadas */
.stTabs [aria-selected="false"] {
    background-color: #e6e6e6 !important;
    color: #333 !important;
}

</style>
""", unsafe_allow_html=True)
st.set_page_config(layout="wide")
st.sidebar.title("Menú")

pagina = st.sidebar.radio("Ir a:", ["Aerotermia", "Producción mes", "Producción dia", "Correlacion Solar", "Correlacion Energia Spot", "Factura", "Ajustes"])
if pagina == "Aerotermia":
    with st.container():
        st.header("Consumo aerotermia vs temperaturas")
        df = get_aerotermia_data(conn)
        fig = grafico_aerotermia(df)
        st.plotly_chart(fig, width='stretch')
        st.subheader("Coste y consumo mensual")
        table = tabla_aerotermia(df)
        st.markdown(table, unsafe_allow_html=True)

elif pagina == "Producción mes":
    st.header("Datos mensuales de producción, consumo, autoconsumo y excedente")
    df_monthly, df_monthly_solar, df_monthly_excedente, df_monthly_consumo, df_monthly_general, df_monthly_autoconsumo = get_energia_mes(conn)

    col1, col2 = st.columns(2, border=True)
    with col1:
        st.subheader("Producción mensual de energía solar (kWh)")
        fig = grafico_energia_mes(df_monthly_solar, title="Producción mensual de energía solar (kWh) por año")
        st.plotly_chart(fig, width='stretch')
        with st.expander("ℹ️ Ver datos"):
            df2 = df_monthly_solar.copy()
            # Columnas numéricas excepto 'year'
            num_cols = df2.select_dtypes(include="number").columns.drop("year")
            # Formateo a string con 2 decimales
            df2[num_cols] = df2[num_cols].map(lambda x: f"{x:.0f}")
            msg = render_df_proportional(df2, widths=[], width_percent=90)
            st.markdown(msg, unsafe_allow_html=True)
    with col2:
        st.subheader("Excedente mensual de energía solar (kWh)")
        fig = grafico_energia_mes(df_monthly_excedente, title="Excedente mensual de energía solar (kWh) por año")
        st.plotly_chart(fig, width='stretch')

    col3, col4 = st.columns(2, border=True)
    with col3:
        st.subheader("Consumo mensual de energía (kWh)")
        fig = grafico_energia_mes(df_monthly_consumo, title="Consumo mensual de energía (kWh) por año")
        st.plotly_chart(fig, width='stretch')
    with col4:
        st.subheader("Autoconsumo mensual de energía (kWh)")
        fig = grafico_energia_mes(df_monthly_autoconsumo, title="Autoconsumo mensual de energía (kWh) por año")
        st.plotly_chart(fig, width='stretch')

elif pagina == "Producción dia":
    st.header("Datos diarios de producción de energía solar")
    grafico_solar, error = grafico_solar_today(conn)
    if error:
        st.error(error)
    else:
        st.plotly_chart(grafico_solar, width='stretch')

elif pagina == "Correlacion Solar":
    # df = power_weather_correlation( conn)
    # fig = grafico_prediccion(df)
    fig = grafico_prediccion_simple(conn)
    st.plotly_chart(fig, width='stretch')

elif pagina == "Correlacion Energia Spot":
    # df = power_weather_correlation( conn)
    # fig = grafico_prediccion(df)
    fig = grafico_prediccion_energia(conn)
    st.plotly_chart(fig, width='stretch')

elif pagina == "Factura":
    col1, col2, col3 = st.columns(3)

    with col1:
        month = st.selectbox("Mes", range(1, 13), format_func=lambda x: datetime(2000, x, 1).strftime('%B'))

    with col2:
        year = st.selectbox("Año", range(2024, 2027))

    with col3:
        st.write("")  # spacer para alinear el botón
        st.write("")
        ejecutar = st.button("Cargar datos")

    if ejecutar:
        texto = mostrar_factura(conn, month, year, "WIBEE")
        st.write(texto)

elif pagina == "Ajustes":
    st.header("Ajustes")
    st.write("Datos actalización de tablas")
    
    st.write("### Tabla con acciones por fila")
    tables = ['DATADIS_v',"PVGIS", "SOM_precio_indexada", "WIBEE", "METEO", "ESIOS_data"]
    df, error = db.get_tables_info(conn, tables)
    if error:
        st.error(f"Error al obtener información de tablas: {error}")
    else:

        # Cabecera
        col1, col2, col3, col4 = st.columns([2, 2, 2, 1])
        col1.write("**Tabla**")
        col2.write("**Desde**")
        col3.write("**Hasta**")
        col4.write("**Acción**")

        # Filas
        for idx, row in df.iterrows():
            col1, col2, col3, col4 = st.columns([2, 2, 2, 1])

            col1.write(row["Tabla"])
            col2.write(row["Desde"])
            col3.write(row["Hasta"])

            # Botón único por fila
            if col4.button("▶", key=f"btn_{idx}"):
                # Acción dependiente del concepto
                placeholder = st.empty()
                placeholder.success(f"Ejecutando acción para concepto {row['Tabla']} (fila {idx})")
                if idx == 1:
                    st.success("Nada que actualizar")
                if idx == 2:
                    resultado, error = update_Som_history(conn)
                    if error:
                        placeholder.error(error)
                    else:
                        placeholder.success(resultado)
                if idx == 3:
                    resultado, error = update_WIBEE_history(conn)
                    if error:
                        placeholder.error(error)
                    else:
                        placeholder.success(resultado)
                if idx == 4:
                    resultado, error = update_openmeteo_history(conn)
                    if error:
                        placeholder.error(error)
                    else:
                        placeholder.success(resultado)
                if idx == 5:
                    resultado, error = update_ESIOS_history(conn)
                    if error:
                        placeholder.error(error)
                    else:
                        placeholder.success(resultado)

