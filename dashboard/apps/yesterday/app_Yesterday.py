import pandas as pd
import streamlit as st

# Añadir la raíz del repo al PYTHONPATH
from dashboard.comun.mensaje import render_df_proportional
from dashboard.apps.yesterday.energia_mes import get_energia_mes, grafico_energia_mes
from dashboard.comun import sql_utilities as db
from dashboard.apps.yesterday.aerotermia import get_aerotermia_data, grafico_aerotermia, tabla_aerotermia
from dashboard.apps.yesterday.power_weather_correlation import power_weather_correlation, grafico_prediccion
import WIBEE_update
import SOM_update

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

pagina = st.sidebar.radio("Ir a:", ["Aerotermia", "Producción mes", "Correlacion", "Ajustes"])
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

elif pagina == "Correlacion":
    df = power_weather_correlation( conn)
    fig = grafico_prediccion(df)
    st.plotly_chart(fig, width='stretch')

elif pagina == "Ajustes":
    st.header("Ajustes")
    st.write("Datos actalización de tablas")
    
    st.write("### Tabla con acciones por fila")
    tables = ['DATADIS_v',"PVGIS", "SOM_precio_indexada", "WIBEE", "METEO" ]
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
                st.success(f"Ejecutando acción para concepto {row['Tabla']} (fila {idx})")
                
                if idx == 2:
                    error = SOM_update.update_data(conn)
                    st.error(error)
                if idx == 3:
                    error = WIBEE_update.update_data(conn)
                    st.error(error)

