import requests
import json
from datetime import datetime, timedelta
import pytz
import pandas as pd

API_TOKEN = "d24bdfb17a69ea6568815918ee3309c3233ab055fe96340da8cd78e71ee9170e"
indicator_id = 603  # Precio medio diario en España
url = f"https://api.esios.ree.es/indicators/{indicator_id}"  # indicador

tz = pytz.timezone("Europe/Madrid")
today = tz.localize(datetime.now().replace(minute=0, second=0, microsecond=0))
start_date = today + timedelta(days=-1)
end_date = today + timedelta(days=1)

rango = {
    'start_date': start_date.strftime('%Y-%m-%dT%H:%M:%S'),
    'end_date': end_date.strftime('%Y-%m-%dT%H:%M:%S')
}

rango = {
            'start_date': "2026-05-01T23:00:00Z",
            'end_date': "2026-05-03T22:59:59Z"
}



headers = {
    "x-api-key": f"{API_TOKEN}",
    "Accept": "application/json;  application/vnd.esios-api-v1+json",
    "Content-Type": "application/json",
    "Host":"api.esios.ree.es",
    "Cookie":""
}

# PARAMS = {
#     "start_date": start_date.isoformat(),
#     "end_date": end_date.isoformat(),
#     "time_trunc" : "hour"
# }

# print(rango)

PARAMS = {
    "start_date": rango['start_date'],
    "end_date": rango["end_date"],
    "time_trunc" : "hour"
}
print("PARAMS:", PARAMS)
print("request", url, headers, PARAMS)
r = requests.get(url, headers=headers, params=PARAMS).json()
#print("Devuelto request:", r)
# print(r["indicator"]["values"]) #[0].keys())
# print(json.dumps(r, indent=1, ensure_ascii=False))
data = r["indicator"]["values"]

ind = r["indicator"]
print(f"[{ind['id']}] {ind['name']}")
print(f"  short name  : {ind['short_name']}")
print(f"  time_agg : {ind.get('time_agg')}")
print(f"  geo_agg  : {ind.get('geo_agg')}")
print(f"  step_type: {ind.get('step_type')}") 

df = pd.DataFrame(data)
if indicator_id == 600:
        df = df[df['geo_name'] == 'España']
print("TEST ESIOS 1", df)
df["datetime"] = pd.to_datetime(df["datetime"], utc=True)
# UTC # df["datetime"] = df["datetime"].dt.tz_localize(None)
df = df.set_index("datetime").sort_index()
df_hourly = df.select_dtypes(include='number').resample('h').mean()
# print(r.status_code)
print("TEST ESIOS 2",df_hourly)

# with open("indicador.txt", "w", encoding="utf-8") as f:
#     f.write(r.text)
