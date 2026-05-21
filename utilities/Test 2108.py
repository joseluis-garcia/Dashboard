import requests
import pandas as pd
from io import StringIO
from datetime import datetime, timedelta

import requests
import pandas as pd
from io import StringIO

def get_prices_2108(
    start_date: str,
    end_date: str,
    cache_period: str | None = None,
) -> pd.DataFrame:
    
    session = requests.Session()
    
    # 1. Obtener cookies visitando la página de análisis primero
    page_url = (
        "https://www.esios.ree.es/es/analisis/2108"
        f"?start_date={start_date}&end_date={end_date}"
        "&geoids=8741&groupby=hour"
    )
    session.get(page_url, headers={"User-Agent": "Mozilla/5.0"})
    
    # 2. Ahora descargar el CSV con las cookies de sesión
    download_url = "https://www.esios.ree.es/es/analysis/download_analysis/2108"
    params = {
        "start_date": start_date,
        "end_date":   end_date,
        "geoids":     "8741",
        "groupby":    "hour",
    }
    headers = {
        "User-Agent":      "Mozilla/5.0",
        "Accept":          "text/csv, application/csv, */*",
        "Referer":         page_url,
        "X-Requested-With": "XMLHttpRequest",  # simula llamada AJAX
        "Accept-Language": "es-ES,es;q=0.9",
    }
    
    response = session.get(download_url, params=params, headers=headers, timeout=30)
    response.raise_for_status()
    
    print(response.status_code)
    print(response.headers.get("Content-Type"))
    print(raw[:200])

    raw = response.text
    if raw.startswith("data:"):
        raw = raw.split(",", 1)[1]
    
    return pd.read_csv(StringIO(raw), sep=";", parse_dates=["datetime"])

# Últimos 3 días como prueba
end = datetime.now()
start = end - timedelta(days=3)

df = get_prices_2108(
    start_date=start.strftime("%d-%m-%YT%H:%M"),
    end_date=end.strftime("%d-%m-%YT%H:%M"),
    cache_period=None,  # Sin cache para prueba
)

print(df.shape)
print(df.head())
print(df.dtypes)