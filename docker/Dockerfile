# Multi-stage Dockerfile for TraceOne Monitoring Service

# Build stage
FROM python:3.11-slim as builder

# Set build arguments
ARG BUILD_ENV=production

# Install system dependencies for building
RUN apt-get update && apt-get install -y \
    build-essential \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy requirements first (for better caching)
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt

# Copy source code
COPY src/ ./src/
COPY setup.py .
COPY README.md .

# Install the application
RUN pip install -e .

# Production stage
FROM python:3.11-slim as production

# Install runtime dependencies
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/* \
    && useradd --create-home --shell /bin/bash traceone

# Set working directory
WORKDIR /app

# Copy Python environment from builder
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Copy application code
COPY --from=builder /app/src ./src
COPY --from=builder /app/setup.py .
COPY --from=builder /app/README.md .

# Copy configuration files
COPY config/ ./config/
COPY examples/ ./examples/

# Create necessary directories
RUN mkdir -p /app/logs /app/data \
    && chown -R traceone:traceone /app

# Switch to non-root user
USER traceone

# Set environment variables
ENV PYTHONPATH=/app/src
ENV PYTHONUNBUFFERED=1
ENV ENVIRONMENT=production

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "from traceone_monitoring import DNBMonitoringService; \
                   service = DNBMonitoringService.from_config(); \
                   exit(0 if service.health_check() else 1)"

# Expose ports
EXPOSE 8080 9090

# Default command
CMD ["python", "-m", "traceone_monitoring.server", "--config", "config/prod.yaml"]

# Labels
LABEL maintainer="TraceOne Development Team <dev@traceone.com>"
LABEL version="1.0.0"
LABEL description="D&B Direct+ API Integration for Real-time Company Data Monitoring"
