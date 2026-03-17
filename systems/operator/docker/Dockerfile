FROM python:3.11-slim

# Установка рабочей директории
WORKDIR /app

# Установка системных зависимостей
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    make \
    && rm -rf /var/lib/apt/lists/*

# Копирование файла зависимостей
COPY systems/operator/requirements.txt ./requirements.txt

# Установка Python зависимостей
RUN pip install --no-cache-dir -r requirements.txt

# Копирование исходного кода
COPY systems/operator/src/ ./src/
COPY systems/operator/__init__.py ./__init__.py

# Копирование SDK и broker (из корня репозитория)
COPY sdk/ ./sdk/
COPY broker/ ./broker/

# Установка переменных окружения по умолчанию
ENV PYTHONPATH=/app:$PYTHONPATH
ENV COMPONENT_TYPE=operator_system
ENV COMPONENT_ID=operator-01
ENV KAFKA_BOOTSTRAP_SERVERS=localhost:9092
ENV LOG_LEVEL=INFO

# Создание пользователя для безопасности (идемпотентно)
RUN if ! id -u operator >/dev/null 2>&1; then \
      useradd -m -u 1000 -g operator operator 2>/dev/null || useradd -m -u 1000 operator; \
    fi && chown -R operator:operator /app
USER operator

# Точка входа - запуск компонента в зависимости от COMPONENT_TYPE
CMD ["python", "-m", "src.run_component"]