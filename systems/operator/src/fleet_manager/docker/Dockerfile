# Fleet Manager Component Dockerfile
FROM python:3.12.3-slim

# Метаданные
LABEL maintainer="operator-team"
LABEL component="fleet_manager"
LABEL version="1.0.0"

# Установка системных зависимостей
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Создание пользователя для запуска компонента
RUN useradd -m -s /bin/bash fleet_manager

# Рабочая директория
WORKDIR /app

# Копирование файлов зависимостей
COPY requirements.txt ./
COPY Pipfile* ./

# Установка Python зависимостей
RUN pip install --no-cache-dir pipenv && \
    pipenv install --system --deploy --ignore-pipfile

# Копирование исходного кода
COPY --chown=fleet_manager:fleet_manager . .

# Создание директорий для логов и данных
RUN mkdir -p /app/logs /app/data && \
    chown -R fleet_manager:fleet_manager /app/logs /app/data

# Переключение на пользователя
USER fleet_manager

# Переменные окружения по умолчанию
ENV PYTHONUNBUFFERED=1
ENV COMPONENT_ID=fleet_manager_01
ENV BROKER_TYPE=mqtt
ENV BROKER_HOST=broker
ENV BROKER_PORT=1883
ENV FLEET_MANAGER_TOPIC=operator.fleet_manager
ENV LOG_LEVEL=INFO

# Health check endpoint
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD python -c "import sys; sys.path.insert(0, '/app'); \
    from src.fleet_manager import FleetManager; \
    from broker.bus_factory import BusFactory; \
    import asyncio; \
    async def check(): \
        bus = BusFactory.create_bus('mqtt', 'localhost', 1883); \
        fm = FleetManager('health_check', bus); \
        status = fm.get_health_status(); \
        return status.get('status') == 'healthy'; \
    exit(0 if asyncio.run(check()) else 1)"

# Точка входа
ENTRYPOINT ["python", "-m", "fleet_manager"]