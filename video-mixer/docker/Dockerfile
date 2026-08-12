FROM python:3.11-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    libva2 \
    libva-drm2 \
    mesa-va-drivers \
    intel-media-va-driver \
    vainfo \
    gosu \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/* \
    && groupadd --gid 1000 app \
    && useradd --uid 1000 --gid app --create-home app

WORKDIR /app

COPY requirements.txt /app/
RUN pip install --no-cache-dir -r requirements.txt \
    && python -c "import flask, waitress, requests"

COPY docker/entrypoint.sh /usr/local/bin/video-matrix-entrypoint
RUN chmod +x /usr/local/bin/video-matrix-entrypoint \
    && mkdir -p /config \
    && chown app:app /config

ENV PYTHONUNBUFFERED=1 \
    HOME=/home/app \
    REMOTE_CLIENT_DATA_DIR=/config \
    HOST_MACHINE_ID_FILE=/host/etc/machine-id \
    HOST_OS_TYPE=linux

ENTRYPOINT ["/usr/local/bin/video-matrix-entrypoint"]
CMD ["python", "app.py"]
