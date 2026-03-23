"""
Módulo para obtener datos historicos de ESIOS (demanda, spot).

Proporciona funciones para obtener y visualizar:
- Previsión de energía eólica
- Previsión de energía solar fotovoltaica
- Previsión de demanda
- Precio del mercado spot diario
"""

from typing import Tuple, Optional, Dict, Any
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from dashboard.comun.get_ESIOS_indicator import get_indicator
from dashboard.comun import date_conditions as dc
from dashboard.comun.date_conditions import RangoFechas


# Códigos de indicadores ESIOS
IND_DEMANDA = 1293  # Demanda real
IND_SPOT = 600      # Precio mercado spot diario


def get_ESIOS_energy(rango: RangoFechas) -> Tuple[Optional[pd.DataFrame], Optional[str]]:
    """
    Obtiene datos de energía (eólica, solar y demanda) de ESIOS.
    
    Obtiene las previsiones de energía eólica, solar fotovoltaica y demanda
    del sistema eléctrico español para el rango de fechas especificado.
    
    Args:
        rango: Diccionario con 'start_date' y 'end_date'
        
    Returns:
        Tupla (dataframe, error) donde:
        - dataframe: DataFrame con columnas ['eolica', 'solar', 'demanda', 'renovable']
        - error: None si es exitoso, mensaje de error si falla
        
    Raises:
        Exception: Se captura cualquier error de API
        
    Example:
        >>> rango = {
        ...     'start_date': datetime(2026, 3, 1),
        ...     'end_date': datetime(2026, 3, 31)
        ... }
        >>> df, error = get_ESIOS_energy(rango)
        >>> if not error:
        ...     print(df.head())
    """
    # Obtener datos de demanda
    df_demanda, error = get_indicator(IND_DEMANDA, rango)
    if error:
        return None, error

    
    # Obtener datos de precio spot
    df_dem, error = get_indicator(IND_SPOT, rango)
    if error:
        return None, error

    # Combinar datos en un solo DataFrame
    df_energy = eolica.join(solar, how="outer").join(demanda, how="outer")
    df_energy["renovable"] = df_energy["eolica"] + df_energy["solar"]
    
    return df_energy, None


def get_ESIOS_spot(rango: RangoFechas) -> Tuple[Optional[pd.DataFrame], Optional[str]]:
    """
    Obtiene datos de precio spot diario de ESIOS.
    
    Obtiene el precio del mercado spot diario para España (Península Ibérica)
    del sistema eléctrico español.
    
    Args:
        rango: Diccionario con 'start_date' y 'end_date'
        
    Returns:
        Tupla (dataframe, error) donde:
        - dataframe: DataFrame con columna 'precio_spot'
        - error: None si es exitoso, mensaje de error si falla
        
    Example:
        >>> rango = {
        ...     'start_date': datetime(2026, 3, 1),
        ...     'end_date': datetime(2026, 3, 31)
        ... }
        >>> df, error = get_ESIOS_spot(rango)
        >>> if not error:
        ...     print(f"Precio promedio: {df['precio_spot'].mean():.2f} €/MWh")
    """
    df, error = get_indicator(IND_SPOT, rango)
    if error:
        return None, error
    
    # Filtrar solo valores de España (Península)
    spot = df[df['geo_name'] == 'España']
    spot = spot[["value"]].rename(columns={"value": "precio_spot"})
    
    return spot, None


def grafico_ESIOS_energy(df_energia: pd.DataFrame) -> go.Figure:
    """
    Crea gráfico de previsión de energía eólica, solar y demanda.
    
    Genera un gráfico interactivo con:
    - Áreas stacked de eólica y solar
    - Línea de demanda (eje Y izquierdo)
    - Línea de porcentaje renovable sobre demanda (eje Y derecho)
    - Rectángulos para fines de semana y festivos
    - Línea vertical marcando el día actual
    
    Args:
        df_energia: DataFrame con columnas ['eolica', 'solar', 'demanda', 'renovable']
        
    Returns:
        Figura Plotly (go.Figure)
        
    Example:
        >>> df, _ = get_ESIOS_energy(rango)
        >>> fig = grafico_ESIOS_energy(df)
        >>> fig.show()
    """
    # Crear figura con doble eje Y
    fig = make_subplots(
        rows=1, cols=1,
        specs=[[{"secondary_y": True}]]
    )

    # Área de energía eólica
    fig.add_trace(
        go.Scatter(
            x=df_energia.index,
            y=df_energia["eolica"],
            mode="lines",
            name="Eólica",
            line=dict(color="#00A000", width=1),
            fillcolor="rgba(0, 200, 0, 0.2)",
            stackgroup="energia"
        )
    )

    # Área de energía solar (stacked sobre eólica)
    fig.add_trace(
        go.Scatter(
            x=df_energia.index,
            y=df_energia["solar"],
            name="Solar",
            mode="lines",
            line=dict(color="#E6C300", width=1),
            fillcolor="rgba(230, 195, 0, 0.2)",
            stackgroup="energia"
        )
    )

    fig.update_layout(barmode="stack")

    # Línea de demanda
    fig.add_trace(
        go.Scatter(
            x=df_energia.index,
            y=df_energia["demanda"],
            mode="lines",
            name="Demanda",
            line=dict(color="blue", width=2)
        )
    )

    # Línea de porcentaje renovable sobre demanda (eje derecho)
    fig.add_trace(
        go.Scatter(
            x=df_energia.index,
            y=df_energia["renovable"] / df_energia["demanda"] * 100,
            mode="lines",
            name="%EO+FV / Demanda",
            line=dict(color="tomato", width=2, shape="spline", smoothing=1.3),
            yaxis="y2"
        )
    )

    # Asegurar que la línea de renovables queda por encima
    fig.data[-1].update(zorder=10)

    # Añadir rectángulos en los fines de semana
    if dc.weekends:
        for start, end in dc.weekends:
            fig.add_shape(
                type="rect",
                x0=start,
                x1=end,
                y0=0,
                y1=1,
                xref="x",
                yref="paper",
                line=dict(color="rgba(150,150,150,0.6)", width=1.5),
                fillcolor="rgba(100,100,100,0.2)",
                layer="above"
            )

    # Añadir rectángulos en los días festivos
    if dc.festivos:
        for festivo in dc.festivos:
            fig.add_vrect(
                x0=festivo, x1=festivo + pd.Timedelta(days=1),
                fillcolor="indianred",
                opacity=0.15,
                line_width=0
            )

    # Configuración de ejes
    fig.update_yaxes(
        title_text="MW",
        showgrid=True,
        zeroline=False,
        secondary_y=False
    )

    fig.update_yaxes(
        title_text="%",
        showgrid=False,
        zeroline=False,
        secondary_y=True,
        overlaying="y"
    )

    fig.update_layout(
        title="Previsión de energía eólica, solar y demanda",
        xaxis_title="Fecha",
        yaxis_title="MW",
        legend=dict(
            orientation="h",
            yanchor="top",
            y=-0.6,
            xanchor="center",
            x=0.5
        ),
        hovermode="x unified"
    )

    # Línea vertical para marcar el día actual
    if dc.today:
        fig.add_vline(
            x=dc.today,
            line_width=4,
            line_dash="dash",
            line_color="green",
            name="Hoy"
        )

    fig.update_xaxes(dtick="D1", tickangle=45)

    return fig


__all__ = ["get_ESIOS_energy", "get_ESIOS_spot", "grafico_ESIOS_energy"]
