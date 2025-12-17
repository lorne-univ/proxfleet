# Dockerfile for Proxmox VM Bulk Management
# Base: Python Alpine (lightweight and secure)

FROM python:alpine3.23

# Metadata
LABEL maintainer=""
LABEL description="Proxmox VM Bulk Management Tool"
LABEL version="1.0.0"

# Python environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Install system dependencies required for Python packages
# gcc, musl-dev, libffi-dev are needed to compile some Python packages
RUN apk add --no-cache \
    gcc \
    musl-dev \
    libffi-dev \
    && rm -rf /var/cache/apk/*

# Set working directory
WORKDIR /app

# Copy requirements.txt first (Docker cache optimization)
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Remove build dependencies to reduce image size
RUN apk del gcc musl-dev

# Copy application source code
COPY bulk_vm_management.py .
COPY bulk_vm_management_main.py .
COPY proxmox_manager.py .
COPY proxmox_vm.py .
COPY proxmox_csv.py .
COPY config.yaml .

# Create non-root user for security
RUN adduser -D -u 1000 appuser && \
    chown -R appuser:appuser /app

# Switch to non-root user
USER appuser

# Entry point: main Python script
ENTRYPOINT ["python", "bulk_vm_management_main.py"]

# Default command: show help
CMD ["--help"]