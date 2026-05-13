# Узкий образ api_gateway для UAS_GATEWAY_BACKEND=bus (Задача 23). Без sqlite_context и без доменных пакетов.
FROM python:3.13-slim

WORKDIR /app
COPY config/requirements.txt /app/config/requirements.txt
RUN pip install --no-cache-dir -r /app/config/requirements.txt

COPY sdk /app/sdk
COPY broker /app/broker

COPY systems/uas_dev_company/src/gateway/__init__.py \
     systems/uas_dev_company/src/gateway/__main__.py \
     systems/uas_dev_company/src/gateway/bus_backend.py \
     systems/uas_dev_company/src/gateway/server.py \
     /app/systems/uas_dev_company/src/gateway/

COPY systems/uas_dev_company/src/shared/__init__.py \
     systems/uas_dev_company/src/shared/jwt_tokens.py \
     systems/uas_dev_company/src/shared/models.py \
     systems/uas_dev_company/src/shared/topics.py \
     systems/uas_dev_company/src/shared/audit_log_ipc.py \
     systems/uas_dev_company/src/shared/journal_bootstrap.py \
     systems/uas_dev_company/src/shared/monitor_proxy_unwrap.py \
     /app/systems/uas_dev_company/src/shared/
COPY systems/uas_dev_company/src/shared/tcb /app/systems/uas_dev_company/src/shared/tcb

ENV PYTHONPATH=/app:/app/systems/uas_dev_company/src
CMD ["python", "-m", "gateway"]
