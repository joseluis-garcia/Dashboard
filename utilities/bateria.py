import pandas as pd
import numpy as np
import streamlit as st

def simular_bateria(
    df: pd.DataFrame,
    col_consumo: str,
    col_excedente: str,
    capacidad_kwh: float,
    precio_bateria_eur: float,
    soc_min_pct: float = 0.10,
    soc_max_pct: float = 0.95,
    eficiencia_carga: float = 0.95,      # eta round-trip: aplicar sqrt en c/d
    precio_compra_eur_kwh: float = 0.18,
    precio_venta_eur_kwh: float = 0.06,
    vida_util_anos: int = 10,
) -> dict:
    """
    Simula el comportamiento horario de una batería residencial.

    df debe tener índice temporal y columnas de consumo (kWh) y
    excedente solar (kWh). Ambas deben ser positivas (consumo>0
    cuando hay déficit, excedente>0 cuando hay producción sobrante).

    Devuelve dict con métricas financieras y DataFrame de simulación.
    """

    soc_min = capacidad_kwh * soc_min_pct
    soc_max = capacidad_kwh * soc_max_pct
    eta = eficiencia_carga ** 0.5          # eficiencia unidireccional

    consumo   = df[col_consumo].values
    excedente = df[col_excedente].values
    n = len(df)

    # Arrays de resultados
    soc          = np.zeros(n)
    cargado      = np.zeros(n)   # kWh efectivos entrando en batería
    descargado   = np.zeros(n)   # kWh efectivos saliendo de batería
    compra_red   = np.zeros(n)   # kWh comprados a la red
    venta_red    = np.zeros(n)   # kWh vendidos a la red
    excedente_vertido = np.zeros(n)  # sobrante que no cabe

    soc_actual = soc_min  # empieza al mínimo

    for t in range(n):
        exc = excedente[t]
        con = consumo[t]

        if exc > 0:
            # --- Hora con excedente solar: intentar cargar ---
            espacio_disponible = (soc_max - soc_actual) / eta  # kWh brutos necesarios
            a_cargar_bruto = min(exc, espacio_disponible)
            a_cargar_neto  = a_cargar_bruto * eta

            soc_actual    += a_cargar_neto
            cargado[t]     = a_cargar_neto
            sobrante       = exc - a_cargar_bruto
            venta_red[t]   = sobrante

        elif con > 0:
            # --- Hora con déficit: intentar descargar ---
            energia_disponible = (soc_actual - soc_min) * eta  # kWh netos extraíbles
            a_descargar = min(con, energia_disponible)

            soc_actual    -= a_descargar / eta   # descontar del SOC bruto
            descargado[t]  = a_descargar
            deficit        = con - a_descargar
            compra_red[t]  = deficit

        soc[t] = soc_actual

    # --- Escenario SIN batería (baseline) ---
    compra_sin_bat = np.where(consumo > 0, consumo, 0.0)
    venta_sin_bat  = np.where(excedente > 0, excedente, 0.0)

    # --- Cálculo financiero ---
    coste_sin_bat  = compra_sin_bat.sum() * precio_compra_eur_kwh
    ingreso_sin_bat = venta_sin_bat.sum() * precio_venta_eur_kwh
    balance_sin_bat = coste_sin_bat - ingreso_sin_bat

    coste_con_bat   = compra_red.sum() * precio_compra_eur_kwh
    ingreso_con_bat = venta_red.sum() * precio_venta_eur_kwh
    balance_con_bat = coste_con_bat - ingreso_con_bat

    ahorro_anual    = balance_sin_bat - balance_con_bat
    anos_datos      = (df.index[-1] - df.index[0]).days / 365.25
    ahorro_anual_norm = ahorro_anual / anos_datos if anos_datos > 0 else ahorro_anual

    payback         = precio_bateria_eur / ahorro_anual_norm if ahorro_anual_norm > 0 else np.inf
    ahorro_vida_util = ahorro_anual_norm * vida_util_anos - precio_bateria_eur  # VAN simplificado

    # --- DataFrame de simulación ---
    df_sim = df[[col_consumo, col_excedente]].copy()
    df_sim["soc_kwh"]        = soc
    df_sim["cargado_kwh"]    = cargado
    df_sim["descargado_kwh"] = descargado
    df_sim["compra_red_kwh"] = compra_red
    df_sim["venta_red_kwh"]  = venta_red

    return {
        # --- financiero ---
        "ahorro_anual_eur":        round(ahorro_anual_norm, 2),
        "payback_anos":            round(payback, 1),
        "beneficio_vida_util_eur": round(ahorro_vida_util, 2),
        "coste_sin_bat_eur":       round(coste_sin_bat / anos_datos, 2),
        "coste_con_bat_eur":       round(coste_con_bat / anos_datos, 2),
        "ingreso_sin_bat_eur":     round(ingreso_sin_bat / anos_datos, 2),
        "ingreso_con_bat_eur":     round(ingreso_con_bat / anos_datos, 2),
        # --- energético ---
        "kwh_cargados":            round(cargado.sum(), 1),
        "kwh_descargados":         round(descargado.sum(), 1),
        "kwh_comprados_sin_bat":   round(compra_sin_bat.sum(), 1),
        "kwh_comprados_con_bat":   round(compra_red.sum(), 1),
        "kwh_vendidos_sin_bat":    round(venta_sin_bat.sum(), 1),
        "kwh_vendidos_con_bat":    round(venta_red.sum(), 1),
        "autosuficiencia_pct":     round(
            (1 - compra_red.sum() / max(compra_sin_bat.sum(), 1)) * 100, 1
        ),
        "anos_simulados":          round(anos_datos, 2),
        # --- simulación horaria ---
        "df_simulacion":           df_sim,
    }

# Sidebar con parámetros
capacidad     = st.sidebar.slider("Capacidad batería (kWh)", 5.0, 20.0, 10.0, 0.5)
precio_bat    = st.sidebar.number_input("Precio batería (€)", 2000, 15000, 6000, 500)
soc_min       = st.sidebar.slider("SOC mínimo (%)", 5, 30, 10)
soc_max       = st.sidebar.slider("SOC máximo (%)", 70, 100, 95)
eta           = st.sidebar.slider("Eficiencia carga/descarga", 0.80, 0.99, 0.95)
p_compra      = st.sidebar.number_input("Precio compra red (€/kWh)", 0.10, 0.35, 0.18)
p_venta       = st.sidebar.number_input("Precio venta excedente (€/kWh)", 0.02, 0.15, 0.06)
vida_util     = st.sidebar.slider("Vida útil batería (años)", 5, 20, 10)

resultado = simular_bateria(
    df=df_horario,
    col_consumo="consumo_kwh",
    col_excedente="excedente_kwh",
    capacidad_kwh=capacidad,
    precio_bateria_eur=precio_bat,
    soc_min_pct=soc_min / 100,
    soc_max_pct=soc_max / 100,
    eficiencia_carga=eta,
    precio_compra_eur_kwh=p_compra,
    precio_venta_eur_kwh=p_venta,
    vida_util_anos=vida_util,
)

# Métricas principales
col1, col2, col3 = st.columns(3)
col1.metric("Ahorro anual", f"{resultado['ahorro_anual_eur']} €")
col2.metric("Payback", f"{resultado['payback_anos']} años")
col3.metric("Autosuficiencia", f"{resultado['autosuficiencia_pct']} %")