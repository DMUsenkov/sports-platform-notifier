FROM python:3.11-slim

WORKDIR /app

# Установка системных зависимостей
RUN apt-get update && apt-get install -y \
    gcc \
    python3-dev \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Установка pip и обновление setuptools
RUN pip install --no-cache-dir --upgrade pip setuptools wheel

# Копирование и установка requirements
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Копирование кода приложения
COPY . .

# Переменные окружения
ENV PYTHONPATH=/app

# Создание директории для логов
RUN mkdir -p /app/logs

# Запуск бота
CMD ["python", "-m", "bot.main"]