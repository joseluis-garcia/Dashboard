import requests

API_TOKEN = "d24bdfb17a69ea6568815918ee3309c3233ab055fe96340da8cd78e71ee9170e"
url = "https://api.esios.ree.es/archives"  # list todos los widgets
headers = {
    "Authorization": f'Token token="{API_TOKEN}"',
    "Accept": "application/json"
    "user-Agent: TomorrowIO/1.0"
}

r = requests.get(url, headers=headers)
print(r.status_code)
print(r.text)
