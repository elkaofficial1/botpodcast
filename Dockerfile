# Используем официальный образ Ubuntu
FROM ubuntu:22.04

# Устанавливаем необходимые зависимости
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    python3 \
    python3-pip \
    python3-venv \
    && rm -rf /var/lib/apt/lists/*

# Создаем и активируем виртуальное окружение Python
RUN python3 -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Устанавливаем рабочую директорию
WORKDIR /app

# Копируем зависимости
COPY requirements.txt .

# Устанавливаем зависимости Python
RUN pip install --no-cache-dir -r requirements.txt

# Копируем исходный код бота
COPY . .

# Создаем файл data.json с начальными данными
RUN touch data.json && \
    echo '{"items": [{"text": "❌ Очистить весь список (нужно 3 голоса)", "votes": 0, "voted_users": [], "is_reset": true}]}' > data.json

# Устанавливаем переменные окружения
ENV PYTHONUNBUFFERED=1

# Запускаем бота
CMD ["python3", "main.py"]
