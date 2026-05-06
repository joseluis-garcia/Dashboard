import requests
from datetime import datetime, timedelta

API_TOKEN = "d24bdfb17a69ea6568815918ee3309c3233ab055fe96340da8cd78e71ee9170e"
url = "https://api.esios.ree.es/es/analisis"  
headers = {
    "Authorization": f'Token token="{API_TOKEN}"',
    "Accept": "application/json"
}

rango = {
    'start_date': datetime(2026, 5, 1).strftime('%Y-%m-%dT%H:%M:%S'),
    'end_date': datetime(2026, 5, 6).strftime('%Y-%m-%dT%H:%M:%S')
}
print(rango)

PARAMS = {
    "start_date": rango['start_date'],
    "end_date": rango["end_date"],
    "groupby" : "day"
}

r = requests.get(url, headers=headers)
print(r.status_code)
print(r.text)
