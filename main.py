import json
import requests
from time import sleep

TOKEN = "8162382973:AAFUoO9JdktTBE6lzHjhMAjHf2jBgvl8sMw"
JSON_FILE = "data.json"
USERS_FILE = "users.json"  # Файл для хранения ID пользователей
API_URL = f"https://api.telegram.org/bot{TOKEN}/"


# Загрузка и сохранение данных
def load_data():
    try:
        with open(JSON_FILE, "r") as f:
            data = json.load(f)
            # Добавляем нулевой пункт, если его нет
            if not data.get("items") or not any(item.get("is_reset") for item in data["items"]):
                data["items"] = [create_reset_item()] + data.get("items", [])
            return data
    except (FileNotFoundError, json.JSONDecodeError):
        return {"items": [create_reset_item()]}


def save_data(data):
    with open(JSON_FILE, "w") as f:
        json.dump(data, f, indent=2)


# Загрузка и сохранение пользователей
def load_users():
    try:
        with open(USERS_FILE, "r") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {"users": []}


def save_users(users_data):
    with open(USERS_FILE, "w") as f:
        json.dump(users_data, f, indent=2)


def add_user(user_id):
    """Добавляет нового пользователя в список рассылки"""
    users_data = load_users()
    if user_id not in users_data["users"]:
        users_data["users"].append(user_id)
        save_users(users_data)


def create_reset_item():
    """Создает нулевой пункт для очистки списка"""
    return {
        "text": "❌ Очистить весь список (нужно 3 голоса)",
        "votes": 0,
        "voted_users": [],
        "is_reset": True  # Флаг, что это пункт для сброса
    }


# Отправка сообщений
def send_message(chat_id, text):
    try:
        requests.post(
            API_URL + "sendMessage",
            json={"chat_id": chat_id, "text": text, "parse_mode": "Markdown"},
            timeout=10
        )
    except requests.exceptions.RequestException:
        pass  # Игнорируем ошибки отправки


def broadcast_message(text):
    """Рассылает сообщение всем пользователям"""
    users_data = load_users()
    for user_id in users_data["users"]:
        send_message(user_id, text)
        sleep(0.1)  # Небольшая задержка чтобы не превысить лимиты API


# Генерация руководства
def get_help_message():
    return """
*📚 Руководство по использованию бота:*

бот для помощи с подкастами.

*/start* - Показать это руководство
*/add <текст>* - Добавить новый пункт в список
*/list* - Показать текущий список
*/run <номер>* - Проголосовать за удаление пункта

*Примеры:*
`/add про чай`
`/list`
`/run 1` голос за удаление темы
`/run 0` голос за очистку всего списка

Когда пункт получает 2 голоса - он автоматически удаляется!
Для очистки всего списка нужно 3 голоса за пункт 0.
"""


# Обработка команд
def process_command(chat_id, command, args, user_id):
    if command == "start":
        # Добавляем пользователя в список рассылки при старте
        add_user(user_id)
        return get_help_message()

    data = load_data()

    if command == "add":
        if not args:
            return "❌ Используйте: /add <текст>"

        # Добавляем нового пользователя при добавлении пункта
        add_user(user_id)

        # Добавляем новый пункт после нулевого
        new_item_text = " ".join(args)
        new_item = {
            "text": new_item_text,
            "votes": 0,
            "voted_users": [],
            "is_reset": False
        }
        data["items"].append(new_item)
        save_data(data)
        
        # Рассылка уведомления всем пользователям
        broadcast_message(f"📝 Добавлен новый пункт: '{new_item_text}'")
        
        return f"✅ Добавлено: '{new_item_text}'"

    elif command == "list":
        if len(data["items"]) <= 1:  # Только нулевой пункт
            return "📭 Список пуст"

        return "📋 Список:\n" + "\n".join(
            f"{i}. {item['text']} (Голосов: {item['votes']})"
            for i, item in enumerate(data["items"])
        )

    elif command == "run":
        if not args:
            return "❌ Используйте: /run <номер>"

        try:
            num = int(args[0])
        except ValueError:
            return "❌ Номер должен быть числом"

        if num < 0 or num >= len(data["items"]):
            return "❌ Неверный номер пункта"

        item = data["items"][num]
        if user_id in item["voted_users"]:
            return "⚠️ Вы уже голосовали за этот пункт"

        item["votes"] += 1
        item["voted_users"].append(user_id)

        # Обработка обычных пунктов (2 голоса)
        if not item.get("is_reset", False) and item["votes"] >= 2:
            removed_item = data["items"].pop(num)
            save_data(data)
            # Рассылка уведомления об удалении
            broadcast_message(f"🗑️ Удалено: '{removed_item['text']}'")
            return f"🗑️ Удалено: '{removed_item['text']}'"

        # Обработка нулевого пункта (3 голоса)
        elif item.get("is_reset", False) and item["votes"] >= 3:
            data["items"] = [create_reset_item()]  # Оставляем только нулевой пункт
            save_data(data)
            # Рассылка уведомления об очистке
            broadcast_message("♻️ Весь список очищен!")
            return "♻️ Весь список очищен!"

        else:
            save_data(data)
            votes_needed = 3 if item.get("is_reset", False) else 2
            return f"✅ Голос учтён. Осталось: {votes_needed - item['votes']}"

    else:
        return "❌ Неизвестная команда\n" + get_help_message()


# Основной цикл бота
def main():
    offset = None
    while True:
        updates = get_updates(offset)
        for update in updates:
            offset = update["update_id"] + 1

            if "message" not in update:
                continue

            message = update["message"]
            chat_id = message["chat"]["id"]
            user_id = message["from"]["id"]

            # Добавляем пользователя при любом сообщении
            add_user(user_id)

            if "text" not in message:
                continue

            text = message["text"].strip()
            if not text.startswith("/"):
                continue

            parts = text[1:].split()
            command = parts[0].lower()
            args = parts[1:] if len(parts) > 1 else []

            response = process_command(chat_id, command, args, user_id)
            send_message(chat_id, response)

        sleep(1)


def get_updates(offset=None):
    params = {"timeout": 30}
    if offset:
        params["offset"] = offset
    response = requests.get(API_URL + "getUpdates", params=params)
    return response.json().get("result", [])


if __name__ == "__main__":
    main()
