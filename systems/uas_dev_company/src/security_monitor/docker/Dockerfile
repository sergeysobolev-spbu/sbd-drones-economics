# Минимальный образ security_monitor: брокер + политики + запись в audit по шине (Задача 23).
FROM python:3.13-slim

WORKDIR /app
COPY config/requirements.txt /app/config/requirements.txt
RUN pip install --no-cache-dir -r /app/config/requirements.txt

COPY sdk /app/sdk
COPY broker /app/broker

COPY systems/uas_dev_company/src/security_monitor/__init__.py \
     systems/uas_dev_company/src/security_monitor/__main__.py \
     /app/systems/uas_dev_company/src/security_monitor/

COPY systems/uas_dev_company/src/shared/__init__.py \
     systems/uas_dev_company/src/shared/models.py \
     systems/uas_dev_company/src/shared/topics.py \
     systems/uas_dev_company/src/shared/audit_log_ipc.py \
     systems/uas_dev_company/src/shared/journal_bootstrap.py \
     systems/uas_dev_company/src/shared/security_monitor.py \
     systems/uas_dev_company/src/shared/security_policies.py \
     /app/systems/uas_dev_company/src/shared/
COPY systems/uas_dev_company/src/shared/tcb /app/systems/uas_dev_company/src/shared/tcb

ENV PYTHONPATH=/app:/app/systems/uas_dev_company/src
CMD ["python", "-m", "security_monitor"]
