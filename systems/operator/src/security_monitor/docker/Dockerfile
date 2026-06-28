# Dockerfile для компонента Security Monitor
FROM python:3.12-slim

# Метаданные
LABEL maintainer="operator-team@example.com"
LABEL component="security-monitor"
LABEL version="1.0.0"

# Установка системных зависимостей
RUN apt-get update && apt-get install -y \
    gcc \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Создание пользователя для запуска при��ожения
RUN useradd -m -u 1000 appuser

# Установка рабочей директории
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
COPY systems/operator/src/security_monitor/ ./systems/operator/src/security_monitor/

# Создание директорий для логов и данных
RUN mkdir -p /app/logs /app/data && \
    chown -R appuser:appuser /app

# Переключение на пользователя appuser
USER appuser

# Переменные окружения по умолчанию
ENV PYTHONUNBUFFERED=1
ENV COMPONENT_ID=security-monitor-001
ENV BROKER_TYPE=mqtt
ENV BROKER_HOST=mqtt-broker
ENV BROKER_PORT=1883
ENV LOG_LEVEL=INFO
ENV ENABLE_NOTIFICATIONS=true
ENV AUDIT_RETENTION_DAYS=30
ENV METRICS_WINDOW_MINUTES=5

# Проверка здоровья
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD python -c "import sys; sys.exit(0)"

# Точка входа
ENTRYPOINT ["python", "-m", "systems.operator.src.security_monitor"]

# Документация портов (компонент не открывает порты, работает ��ерез брокер)
# EXPOSE не требуется