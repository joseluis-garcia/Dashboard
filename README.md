# 📊 Dashboard Energético

Aplicación integrada para visualización, análisis y predicción de precios de energía en el mercado español.

## 🎯 Descripción

Este proyecto contiene **tres aplicaciones Streamlit especializadas**:

- **Yesterday** ⏰: Análisis histórico de precios de energía, consumo y correlaciones meteorológicas
- **Tomorrow** 📅: Pronóstico de precios para el día actual, meteorología y potencial fotovoltaico
- **Estorninos** 🔮: Predicción de precios futuros (48h - 7 días) con recomendaciones de flexibilidad de demanda

Todas las aplicaciones consumen datos de APIs públicas españolas:
- 🔌 **ESIOS**: Red Eléctrica de España (precios, energía renovable, demanda)
- 🌦️ **OpenMeteo**: Datos meteorológicos históricos y pronósticos
- ☀️ **PVGIS**: Estimación de producción solar fotovoltaica

## 🚀 Instalación

### Requisitos
- Python 3.9 o superior
- pip (gestor de paquetes)
- Git

### Pasos

1. **Clonar el repositorio**
```bash
git clone https://github.com/joseluis-garcia/Dashboard.git
cd Dashboard
```

2. **Crear entorno virtual (opcional pero recomendado)**
```bash
# En Windows
python -m venv venv
venv\Scripts\activate

# En macOS/Linux
python3 -m venv venv
source venv/bin/activate
```

3. **Instalar dependencias**

**Opción A**: Instalación rápida
```bash
pip install -r requirements.txt
```

**Opción B**: Instalación como paquete desarrollo (recomendado)
```bash
pip install -e ".[dev]"
```

Esta opción instala todas las dependencias + herramientas de desarrollo.

4. **Verificar instalación**
```bash
python -c "import dashboard; print(f'✓ Dashboard v{dashboard.__version__}')"
```

## 💻 Uso

### Ejecutar las aplicaciones

**Yesterday** (Análisis histórico):
```bash
streamlit run dashboard/apps/yesterday/app_Yesterday.py
```

**Tomorrow** (Pronóstico del día):
```bash
streamlit run dashboard/apps/tomorrow/app_Tomorrow.py
```

**Estorninos** (Predicción de precios):
```bash
streamlit run dashboard/apps/estorninos/app_Estorninos.py
```

Las aplicaciones se abrirán automáticamente en `http://localhost:8501`

### Configuración

Crear archivo `.streamlit/secrets.toml` si se necesitan credenciales:
```toml
[api_keys]
# Opcional: claves de APIs (por defecto usan endpoints públicos)

[database]
db_path = "data/measures.db"
```

## 📁 Estructura del Proyecto

```
dashboard-energy/
├── dashboard/                 # Paquete principal
│   ├── comun/                # Funciones compartidas
│   │   ├── date_conditions.py       # Utilidades de fechas
│   │   ├── get_ESIOS_data.py        # APIs de Red Eléctrica
│   │   ├── get_openmeteo.py         # APIs meteorológicas
│   │   ├── get_PVGIS.py             # APIs solares
│   │   ├── sql_utilities.py         # Utilidades de BD
│   │   └── icons/                   # Recursos gráficos
│   │
│   └── apps/                 # Aplicaciones Streamlit
│       ├── yesterday/        # Histórico
│       ├── tomorrow/         # Pronóstico
│       └── estorninos/       # Predicción
│
├── tests/                    # Tests unitarios
├── data/                     # Datos históricos y BD
├── ARCHITECTURE.md           # Documentación técnica
├── pyproject.toml           # Configuración del paquete
├── requirements.txt         # Dependencias
└── README.md               # Este archivo
```

Ver [`ARCHITECTURE.md`](ARCHITECTURE.md) para documentación técnica completa.

## 🧪 Testing

Ejecutar tests:
```bash
pytest                           # Todos los tests
pytest --cov=dashboard          # Con coverage report
pytest tests/test_date_conditions.py -v  # Test específico
```

## 🛠️ Desarrollo

### Configurar pre-commit hooks
```bash
pre-commit install
```

Esto ejecuta automaticamente linting, formatting y type checking antes de cada commit.

### Code Quality Tools

**Formatting con Black**:
```bash
black dashboard tests
```

**Linting con Flake8**:
```bash
flake8 dashboard tests
```

**Type checking con mypy**:
```bash
mypy dashboard --ignore-missing-imports
```

**Sort imports con isort**:
```bash
isort dashboard tests
```

## 📚 Documentación

- **[ARCHITECTURE.md](ARCHITECTURE.md)**: Documentación técnica, flujo de datos, APIs
- **[README.md](README.md)**: Este archivo (instrucciones de instalación y uso)
- **Docstrings en código**: Las funciones incluyen documentación en formato Google

## 🔗 APIs Utilizadas

### ESIOS (Red Eléctrica de España)
- Indicador 541: Previsión eólica
- Indicador 542: Previsión solar
- Indicador 603: Previsión demanda
- Indicador 600: Precio spot

Docs: https://www.esios.ree.es/es/aapi

### OpenMeteo
- Pronóstico meteorológico
- Datos históricos de temperatura
- Acceso público (sin API key)

Docs: https://open-meteo.com

### PVGIS
- Estimación producción solar fotovoltaica
- Basado en irradiancia solar
- Acceso público

Docs: https://re.jrc.ec.europa.eu/pvg_tools/en/

## ⚙️ Requisitos del Sistema

| Componente | Versión |
|-----------|---------|
| Python | ≥ 3.9 |
| Streamlit | ≥ 1.54.0 |
| Pandas | ≥ 2.0.0 |
| Plotly | ≥ 6.0.0 |
| NumPy | ≥ 2.0.0 |

Ver [`requirements.txt`](requirements.txt) para lista completa.

## 🐛 Troubleshooting

### "ModuleNotFoundError: No module named 'dashboard'"
```bash
pip install -e .
```

### Problemas con imports
Asegúrate de estar en el directorio raíz del proyecto y haber activado el entorno virtual.

### Errores de conexión a APIs
- Verifica tu conexión a internet
- Las APIs públicas pueden tener límites de rate limiting
- Los datos antiguos pueden requerir autenticación

### La BD (measures.db) está muy pesada
Puedes hacer limpieza de datos antiguos:
```python
from dashboard.comun.sql_utilities import init_db
conn, error = init_db()
# Eliminar datos anteriores a cierta fecha
conn.execute("DELETE FROM measures WHERE datetime < '2024-01-01'")
conn.commit()
```

## 📊 Rendimiento

- **Yesterday**: Cargas 5+ años de histórico → tarda 30-60s la primera vez
- **Tomorrow**: Realtime, datos frescos → 10-15s
- **Estorninos**: Análisis de predicción → 20-30s

Los resultados se cachean automáticamente (Streamlit cache).

## 🚀 Próximas Mejoras

- [ ] Tests con 70%+ coverage
- [ ] GitHub Actions CI/CD
- [ ] Containerización con Docker
- [ ] API REST para terceros
- [ ] Dashboard de administración
- [ ] Mejora de UI/UX
- [ ] Soporte para otras regiones (Portugal, Francia)

## 📝 Licencia

MIT License - Ver `LICENSE` para detalles.

## 👤 Autor

**José Luis García**

- GitHub: [@joseluis-garcia](https://github.com/joseluis-garcia)
- Proyecto: [Dashboard](https://github.com/joseluis-garcia/Dashboard)

## 💬 Support

Para reportar bugs o sugerencias:
- Abre un issue en GitHub
- Discussiones: GitHub Discussions
- Email: tu.email@example.com

## 🙏 Agradecimientos

- ⚡ [Red Eléctrica de España](https://www.ree.es) - Datos ESIOS
- 🌡️ [Open-Meteo](https://open-meteo.com) - Datos meteorológicos
- ☀️ [PVGIS](https://re.jrc.ec.europa.eu/pvg_tools/en/) - Estimaciones solares
- 🎨 [Streamlit](https://streamlit.io) - Framework
- 📈 [Plotly](https://plotly.com) - Visualizaciones

---

**¡Espero que disfrutes usando Dashboard Energético!** 🎉

Si te resulta útil, considera dar una ⭐ en GitHub.
