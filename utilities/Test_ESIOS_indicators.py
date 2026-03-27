import requests

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
print(r.text)

with open("indicadores.txt", "w", encoding="utf-8") as f:
    f.write(r.text)

