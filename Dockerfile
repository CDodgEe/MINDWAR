FROM python:3.12-slim

# Установка системных зависимостей
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Копирование файла зависимостей
COPY pyproject.toml .

# Установка зависимостей проекта
RUN pip install --no-cache-dir pip setuptools wheel && \
    pip install --no-cache-dir .

# Копирование исходного кода приложения
COPY . .

# Переменные окружения по умолчанию
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

CMD ["python", "-m", "app.main"]
