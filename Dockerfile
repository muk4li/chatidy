FROM python:3.13.11-slim-bookworm@sha256:20080e807bfc404f8450b185cf0fc95d553462673598549613735f70a5b4d5d0
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PIP_DISABLE_PIP_VERSION_CHECK=1 \
    CHATIDY_DB=/data/registry.sqlite3
WORKDIR /app
COPY requirements-auth.txt ./
RUN --mount=type=secret,id=build_ca \
    if [ -f /run/secrets/build_ca ]; then export PIP_CERT=/run/secrets/build_ca; fi; \
    python -m pip install --no-cache-dir --only-binary=:all: -r requirements-auth.txt \
    && mkdir /data && chown 10001:10001 /data && chmod 700 /data
COPY chatidy/ ./chatidy/
COPY web/ ./web/
RUN chmod -R a=rX /app
USER 10001:10001
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD ["python", "-m", "chatidy.healthcheck"]
CMD ["sh", "-c", "umask 077; exec python -m chatidy"]
