ARG BASE_IMAGE=operator-base:latest
FROM ${BASE_IMAGE}

WORKDIR /app

# Копирование исходного кода
COPY systems/operator/src/ ./systems/operator/src/
COPY systems/operator/__init__.py ./systems/operator/__init__.py

# Копирование SDK и broker (из корня репозитория)
COPY sdk/ ./sdk/
COPY broker/ ./broker/

# Установка переменных окружения по умолчанию
ENV COMPONENT_TYPE=operator_system
ENV COMPONENT_ID=operator-01
ENV KAFKA_BOOTSTRAP_SERVERS=localhost:9092
ENV LOG_LEVEL=INFO

# Точка входа - запуск компонента в зависимости от COMPONENT_TYPE
CMD ["python", "-m", "systems.operator.src.run_component"]