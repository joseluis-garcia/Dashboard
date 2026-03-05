import sys
from pathlib import Path
import streamlit as st

# Añadir la raíz del repo al PYTHONPATH
repo_root = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(repo_root))

import comun.sql_utilities as db
from get_aerotermia import get_aerotermia_data, grafico_aerotermia, tabla_aerotermia
from app_mostrar_energia_mes import mostrar_energia_mes

from pathlib import Path
import os

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
# with st.sidebar.expander("Opciones", expanded=False):
#     pagina = st.selectbox("Selecciona análisis", ["Aerotermia", "Producción mes", "Ajustes"])

pagina = st.sidebar.radio("Ir a:", ["Aerotermia", "Producción mes", "Ajustes"])
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
    st.header("Producción mensual")
    #mostrar_energia_mes()

elif pagina == "Ajustes":
    st.header("Ajustes")
    st.write("Opciones de configuración")
