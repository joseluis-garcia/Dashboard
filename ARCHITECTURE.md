# Arquitectura del Dashboard Energético

## 📋 Visión General

Dashboard Energético es una aplicación integrada para visualización, análisis y predicción de precios de energía en el mercado español. Está compuesta por tres aplicaciones Streamlit especializadas que procesan datos de múltiples APIs externas.

## 🏗️ Estructura del Proyecto

```
dashboard-energy/
├── dashboard/
│   ├── __init__.py                 # Punto de entrada del paquete
│   │
│   ├── comun/                      # Funciones compartidas
│   │   ├── date_conditions.py      # Utilidades de fechas, festivos, cálculos solares
│   │   ├── get_ESIOS_*.py          # Integración con APIs de Red Eléctrica
│   │   ├── get_openmeteo.py        # Integración con OpenMeteo (meteorología)
│   │   ├── get_PVGIS.py            # Integración con PVGIS (producción solar)
│   │   ├── sql_utilities.py        # Utilidades para BD SQLite
│   │   ├── safe_request.py         # Wrapper seguro para requests HTTP
│   │   ├── async_tasks.py          # Manejo de tareas asincrónicas
│   │   ├── icons/                  # Recursos de iconos
│   │   └── services/               # PRÓXIMO: Capa de servicios (lógica de negocio)
│   │
│   └── apps/                       # Aplicaciones Streamlit
│       ├── yesterday/              # Análisis histórico
│       │   ├── app_Yesterday.py
│       │   ├── aerotermia.py
│       │   ├── energia_mes.py
│       │   ├── power_weather_correlation.py
│       │   ├── PVGIS_import.py
│       │   ├── WIBEE_update.py
│       │   └── SOM_update.py
│       │
│       ├── tomorrow/               # Pronóstico del día
│       │   └── app_Tomorrow.py
│       │
│       └── estorninos/             # Predicción de precios
│           ├── app_Estorninos.py
│           ├── historico_spot.py
│           └── historico_temperaturas.py
│
├── tests/                          # Tests unitarios e integración
│   ├── conftest.py                # Fixtures compartidas
│   ├── test_date_conditions.py
│   └── test_apis/
│
├── data/                           # Datos históricos y BD
│   ├── measures.db                # BD principal (SQLite)
│   ├── spot.csv                   # Histórico de precios spot
│   ├── temperaturas.csv           # Histórico de temperaturas
│   └── costes_regulados.json      # Costos regulados
│
├── .github/
│   └── workflows/                  # GitHub Actions CI/CD
│       └── ci.yml
│
├── .streamlit/                     # Configuración Streamlit
│   └── config.toml
│
├── pyproject.toml                  # Configuración moderno (PEP 517/518)
├── setup.py                        # Setup tradicional
├── setup.cfg                       # Configuración setuptools
├── requirements.txt                # Dependencias principales
├── requirements-dev.txt            # Dependencias desarrollo
├── README.md                       # Guía de usuario
└── ARCHITECTURE.md                 # Este archivo
```

## 📊 Flujo de Datos

```
┌─────────────────────────────────────────────────────────────┐
│                    FUENTES DE DATOS                         │
└──────┬──────────────┬──────────────┬──────────────┬─────────┘
       │              │              │              │
   ESIOS API      OpenMeteo      PVGIS API    Base de Datos
  (Red Eléctrica) (Meteorología) (Solar)       (Históricos)
       │              │              │              │
       └──────────────┴──────────────┴──────────────┘
              │
              ▼
       ┌──────────────────┐
       │  Capa Comun      │
       │  (Utilities)     │
       └────────┬─────────┘
              │
       ┌──────┴────────────────────┐
       │                           │
       ▼                           ▼
    Yesterday              Tomorrow    Estorninos
   (Histórico)            (Pronóstico) (Predicción)
```

## 🔄 Flujo por Aplicación

### Yesterday (Análisis Histórico)
1. Lee datos históricos de BD (measures.db)
2. Carga datos históricos de APIs (ESIOS, meteorología)
3. Calcula estadísticas: consumo medio, picos, correlaciones
4. Visualiza series temporales y heatmaps
5. Analiza perfil de consumo por hora del día

### Tomorrow (Pronóstico del Día)
1. Obtiene precios predichos de ESIOS para hoy
2. Carga pronóstico meteorológico de OpenMeteo
3. Calcula producción solar estimada (PVGIS + nubosidad)
4. Determina óptimas ventanas de consumo
5. Muestra alertas de precios altos/bajos

### Estorninos (Predicción de Precios)
1. Analiza histórico de precios spot (últimos meses)
2. Detecta patrones y tendencias
3. Predice precios futuros (próximas 48h - 7 días)
4. Recomienda cambios de consumo para usuarios flexibles
5. Visualiza heatmaps de precios predichos

## 🔌 APIs Integradas

### ESIOS (Red Eléctrica de España)
- **Indicador 541**: Previsión de producción eólica (MW)
- **Indicador 542**: Previsión de producción fotovoltaica (MW)
- **Indicador 603**: Demanda previsión semanal (MW)
- **Indicador 600**: Precio de mercado spot diario (€/MWh)

### OpenMeteo
- Pronóstico meteorológico (temperatura, humedad, nubosidad)
- Datos históricos de temperatura
- Resolución: cada 1 hora

### PVGIS
- Estimación de producción fotovoltaica
- Basado en irradiancia solar
- Ajustado por nubosidad (del pronóstico de OpenMeteo)

## 💾 Base de Datos

### SQLite (data/measures.db)
Almacena:
- Lecturas de energía (consumo, generación)
- Histórico de precios spot
- Datos meteorológicos históricos
- Medidas de sistemas de aerotermia

**Esquema aproximado:**
```sql
-- Tabla principal de medidas
CREATE TABLE measures (
    datetime DATETIME,
    value FLOAT,
    type TEXT  -- 'consumption', 'price', 'temperature', etc.
);

-- Índice para búsquedas rápidas
CREATE INDEX idx_datetime ON measures(datetime);
```

## 🔐 Variables de Entorno

Las credenciales y configuración sensible se almacenan en:
- `.streamlit/secrets.toml` (local)
- Variables de GitHub Secrets (producción)

Ejemplos:
```toml
[api_keys]
esios_token = "..."
openmeteo_key = "..."

[database]
db_path = "data/measures.db"
```

## 🧪 Testing

### Estructura
```
tests/
├── conftest.py              # Fixtures compartidas
├── test_date_conditions.py  # Tests de utilidades de fecha
├── test_sql_utilities.py    # Tests de BD
└── apis/
    ├── test_esios.py        # Tests de APIs (con mocks)
    ├── test_openmeteo.py
    └── test_pvgis.py
```

### Ejecución
```bash
# Todos los tests
pytest

# Con coverage
pytest --cov=dashboard

# Tests específicos
pytest tests/test_date_conditions.py -v
```

## 📈 Rendimiento y Optimizaciones

### Caching
- `@st.cache_data`: Cachea resultados de funciones costosas (1 hora por defecto)
- `@st.cache_resource`: Reutiliza conexiones de BD entre reruns
- Caching HTTP con `requests-cache` para APIs externas

### Lazy Loading
- Cargar solo rango de fechas necesario (no todo el histórico)
- Resamplear datos para visualizaciones grandes
- Usar Plotly con `renderer: svg` para gráficos más rápidos

### Connection Pooling
- SQLite con StaticPool para Streamlit
- Reutilizar conexión en toda la sesión

## 🚀 Deployment

### Local Development
```bash
pip install -e ".[dev]"
streamlit run dashboard/apps/estorninos/app_Estorninos.py
```

### Docker (Próximo)
```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY . .
RUN pip install -e .
CMD ["streamlit", "run", "dashboard/apps/estorninos/app_Estorninos.py"]
```

### Streamlit Cloud
1. Push a GitHub
2. Conectar repo en Streamlit Cloud
3. Configurar `secrets.toml` en dashboard
4. Deploy automático en cada push a main

### Production
- Usar `gunicorn` + `supervisord` para monitoreo
- Logs rotados (evitar llenar disco)
- Health checks periódicos
- Alertas de error (Sentry, DataDog)

## 📝 Convenciones de Código

### Estilo
- **Formatter**: Black (línea máx 100 caracteres)
- **Linter**: Flake8
- **Type Checker**: mypy
- **Import Sorter**: isort

### Docstrings
Usar formato Google:
```python
def get_energy_data(rango: RangoFechas) -> pd.DataFrame:
    """
    Obtiene datos de energía del rango especificado.
    
    Args:
        rango: Diccionario con start_date y end_date
        
    Returns:
        DataFrame con columnas eolica, solar, demanda
        
    Raises:
        APIError: Si falla la llamada a ESIOS
    """
```

### Type Hints
- Obligatorio para parámetros y retornos en funciones nuevas
- Usar `typing` para tipos complejos
- Ignorar imports de librerías sin tipos (Streamlit, Plotly)

## 🔮 Próximas Mejoras

- [ ] Crear `dashboard/comun/services/` (Energy, Weather, Forecast services)
- [ ] Migrar a `sqlalchemy` para mejor manejo de BD
- [ ] Agregar tests completos (70%+ coverage)
- [ ] GitHub Actions CI/CD
- [ ] Docker containerization
- [ ] Documentación Sphinx
- [ ] API REST para terceros
- [ ] Dashboard de administración

## 📚 Referencias

- [Streamlit Docs](https://docs.streamlit.io)
- [Plotly Docs](https://plotly.com/python/)
- [ESIOS API](https://www.esios.ree.es/es/aapi)
- [OpenMeteo API](https://open-meteo.com)
- [PVGIS API](https://re.jrc.ec.europa.eu/pvg_tools/en/)
