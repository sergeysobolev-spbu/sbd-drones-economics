# Узкий образ воркера: один домен + whitelist shared + broker/sdk.
# Сборка: build.args.DOMAIN = имя пакета (user_management, audit_log, …).
FROM python:3.13-slim

ARG DOMAIN=user_management
ENV UAS_WORKER_DOMAIN=${DOMAIN}

WORKDIR /app
COPY config/requirements.txt /app/config/requirements.txt
RUN pip install --no-cache-dir -r /app/config/requirements.txt

COPY sdk /app/sdk
COPY broker /app/broker

COPY systems/uas_dev_company/src/shared/__init__.py \
     systems/uas_dev_company/src/shared/protocols.py \
     systems/uas_dev_company/src/shared/services.py \
     systems/uas_dev_company/src/shared/storage.py \
     systems/uas_dev_company/src/shared/topics.py \
     systems/uas_dev_company/src/shared/domain_storage.py \
     systems/uas_dev_company/src/shared/models.py \
     systems/uas_dev_company/src/shared/jwt_tokens.py \
     systems/uas_dev_company/src/shared/component_base.py \
     systems/uas_dev_company/src/shared/worker_runtime.py \
     systems/uas_dev_company/src/shared/worker_deps.py \
     systems/uas_dev_company/src/shared/external_adapters_factory.py \
     systems/uas_dev_company/src/shared/analytics_ipc.py \
     systems/uas_dev_company/src/shared/audit_log_ipc.py \
     systems/uas_dev_company/src/shared/bus_integration_adapters.py \
     systems/uas_dev_company/src/shared/integration_adapters.py \
     systems/uas_dev_company/src/shared/monitor_client.py \
     systems/uas_dev_company/src/shared/monitor_proxy_unwrap.py \
     systems/uas_dev_company/src/shared/journal_startup.py \
     /app/systems/uas_dev_company/src/shared/
COPY systems/uas_dev_company/src/shared/tcb /app/systems/uas_dev_company/src/shared/tcb

COPY systems/uas_dev_company/src/${DOMAIN} /app/systems/uas_dev_company/src/${DOMAIN}

ENV PYTHONPATH=/app:/app/systems/uas_dev_company/src
CMD ["sh", "-c", "exec python -m \"$UAS_WORKER_DOMAIN\""]
