# Dockerfile для компонента Business Logic

# Базовый образ
FROM python:3.12.3-slim

# Метаданные
LABEL maintainer="Operator System Team"
LABEL description="Business Logic component for Operator System"
LABEL version="1.0.0"

# Установка системных зависимостей
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Создание рабочей директории
WORKDIR /app

# Копирование файлов зависимостей
COPY Pipfile Pipfile.lock ./

# Установка pipenv и зависимостей
RUN pip install --no-cache-dir pipenv && \
    pipenv install --system --deploy --ignore-pipfile

# Копирование исходного кода
COPY sdk/ ./sdk/
COPY broker/ ./broker/
COPY systems/operator/src/topics.py ./systems/operator/src/
COPY systems/operator/src/__init__.py ./systems/operator/src/
COPY systems/operator/src/business_logic/ ./systems/operator/src/business_logic/

# Создание пользователя для запуска приложения
RUN useradd -m -u 1000 appuser && \
    chown -R appuser:appuser /app

# Переключение на пользователя
USER appuser

# Переменные окружения по умолчанию
ENV PYTHONUNBUFFERED=1
ENV COMPONENT_ID=business-logic-001
ENV BROKER_TYPE=mqtt
ENV BROKER_HOST=mqtt-broker
ENV BROKER_PORT=1883
ENV LOG_LEVEL=INFO

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import sys; sys.exit(0)"

# Точка входа
ENTRYPOINT ["python", "-m", "systems.operator.src.business_logic"]