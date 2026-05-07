FROM python:3.13-slim

WORKDIR /app
COPY config/requirements.txt /app/config/requirements.txt
RUN pip install --no-cache-dir -r /app/config/requirements.txt

COPY sdk /app/sdk
COPY broker /app/broker
COPY systems/uas_dev_company /app/systems/uas_dev_company

ENV PYTHONPATH=/app:/app/systems/uas_dev_company/src
CMD ["python", "-m", "audit_log"]
