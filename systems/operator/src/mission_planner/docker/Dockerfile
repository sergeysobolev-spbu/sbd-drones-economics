# Mission Planner Component Dockerfile

# Build stage
FROM python:3.9-slim as builder

# Install build dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    python3-dev \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /build

# Copy requirements
COPY systems/operator/requirements.txt ./requirements.txt

# Install Python dependencies
RUN pip install --no-cache-dir --user -r requirements.txt

# Runtime stage
FROM python:3.9-slim

# Install runtime dependencies
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user
RUN useradd -m -u 1000 -s /bin/bash appuser

# Set working directory
WORKDIR /app

# Copy Python dependencies from builder
COPY --from=builder /root/.local /home/appuser/.local

# Copy application code
COPY --chown=appuser:appuser sdk/ ./sdk/
COPY --chown=appuser:appuser broker/ ./broker/
COPY --chown=appuser:appuser systems/operator/src/topics.py ./systems/operator/src/topics.py
COPY --chown=appuser:appuser systems/operator/src/mission_planner/ ./systems/operator/src/mission_planner/

# Set Python path
ENV PYTHONPATH=/app:/home/appuser/.local/lib/python3.9/site-packages
ENV PATH=/home/appuser/.local/bin:$PATH

# Environment variables with defaults
ENV COMPONENT_ID=mission-planner-001
ENV BROKER_TYPE=mqtt
ENV BROKER_HOST=localhost
ENV BROKER_PORT=1883
ENV SYSTEM_ID=operator-001
ENV LOG_LEVEL=INFO
ENV MAX_CONCURRENT_MISSIONS=10
ENV MISSION_RETENTION_DAYS=90
ENV ENABLE_ROUTE_OPTIMIZATION=true

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8080/health || exit 1

# Switch to non-root user
USER appuser

# Expose metrics port (if needed)
EXPOSE 8080

# Run the component
CMD ["python", "-m", "systems.operator.src.mission_planner"]

# Labels
LABEL maintainer="Operator System Team"
LABEL component="mission_planner"
LABEL version="1.0.0"
LABEL description="Mission Planner component for UAS mission management"