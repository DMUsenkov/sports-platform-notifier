FROM python:3.11-slim

WORKDIR /app

# Установка зависимостей
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
