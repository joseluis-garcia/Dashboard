import requests

def send_poll(chat_id, token):
    url = f"https://api.telegram.org/bot{token}/sendPoll"
    payload = {
        "chat_id": chat_id,
        "question": "¿Qué te parece el precio de la luz hoy?",
        "options": ["Muy caro", "Normal", "Barato"],
        "is_anonymous": True,        # False si quieres ver quién vota
        "allows_multiple_answers": False
    }
    response = requests.post(url, json=payload)
    return response.json()

# Parámetro Descripción
# is_anonymous True por defecto — votos anónimos
# allows_multiple_answers Permite seleccionar varias opciones
# type "regular" (votación) o "quiz" (respuesta correcta)
# correct_option_id Solo para type="quiz"
# explanation Texto que aparece al revelar la respuesta correcta (quiz)open_period Segundos que está abierta (60–600)
# close_date Timestamp Unix de cierre

#quiz
# payload = {
#     "chat_id": chat_id,
#     "question": "¿A qué hora suele ser más barata la luz?",
#     "options": ["6:00–8:00", "14:00–16:00", "23:00–1:00"],
#     "type": "quiz",
#     "correct_option_id": 2,
#     "explanation": "Las horas valle suelen ser de madrugada"
# }