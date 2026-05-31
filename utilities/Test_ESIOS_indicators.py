import requests
import json

API_TOKEN = "d24bdfb17a69ea6568815918ee3309c3233ab055fe96340da8cd78e71ee9170e"
url = "https://api.esios.ree.es/indicators"  # list todos los indicadores
headers = {
    "x-api-key": f"{API_TOKEN}",
    "Accept": "application/json;  application/vnd.esios-api-v1+json",
    "Content-Type": "application/json",
    "Host":"api.esios.ree.es",
    "Cookie":""
}

r = requests.get(url, headers=headers)
print(r.status_code)
#print(r.json())

from html import unescape

def unescape_recursive(obj):
    if isinstance(obj, str):
        return unescape(obj)
    elif isinstance(obj, dict):
        return {k: unescape_recursive(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [unescape_recursive(i) for i in obj]
    return obj

data = unescape_recursive(r.json())

with open("indicadores.json", "w", encoding="utf-8") as f:
    json.dump(data, f, ensure_ascii=False, indent=2)

