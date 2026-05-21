import requests
"""
Devuelve el ID del usuario Telegram que hubiera escrito un mensaje al bot. Es necesario para enviarle mensajes posteriormente.
"""
TOKEN = "8599651548:AAEnxS66J9_uSv8Yjj-GWpXUVkmzIMh-qZI"
# 1. Envíate un mensaje a tu bot primero
# 2. Luego ejecuta:
r = requests.get(f"https://api.telegram.org/bot{TOKEN}/getUpdates")
updates = r.json()
print(updates['result'][0]['message']['from']['id'])