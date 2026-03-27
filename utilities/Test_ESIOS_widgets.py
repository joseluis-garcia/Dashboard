import requests

API_TOKEN = "d24bdfb17a69ea6568815918ee3309c3233ab055fe96340da8cd78e71ee9170e"
url = "https://api.esios.ree.es/widgets/4773?locale=es"  # list todos los widgets
headers = {
    "Authorization": f'Token token="{API_TOKEN}"',
    "Accept": "application/json"
}

r = requests.get(url, headers=headers)
print(r.status_code)
print(r.text)
