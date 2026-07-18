FROM python:3.13-slim

LABEL org.opencontainers.image.title="MP-Gateway" \
      org.opencontainers.image.description="Multi-Protokoll-Gateway für KNX, MQTT, UDP, Loxone und InfluxDB" \
      org.opencontainers.image.version="33.4.68-rc1"

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    MQTT2LOX_APP_ROOT=/app \
    MQTT2LOX_CONFIG_DIR=/app/config \
    MQTT2LOX_DATA_DIR=/app/data \
    MQTT2LOX_BACKUP_DIR=/app/backups

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends mosquitto mosquitto-clients ca-certificates \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt /app/requirements.txt
RUN python -m pip install --upgrade pip \
    && python -m pip install -r /app/requirements.txt

COPY . /app

RUN mkdir -p /app/config /app/data /app/backups \
    && chmod +x /app/docker-entrypoint.sh

EXPOSE 8099/tcp

HEALTHCHECK --interval=30s --timeout=5s --start-period=30s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8099/startup_status', timeout=3).read()" || exit 1

ENTRYPOINT ["/app/docker-entrypoint.sh"]
CMD ["python", "-u", "app/main.py"]
