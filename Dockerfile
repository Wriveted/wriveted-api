FROM python:3.10-slim

LABEL org.opencontainers.image.source=https://github.com/Wriveted/wriveted-api

WORKDIR /app/

# Allow statements and log messages to immediately appear in the Knative logs
ENV PYTHONUNBUFFERED=True \
    PIP_NO_CACHE_DIR=1 \
    POETRY_NO_INTERACTION=1 \
    PYTHONPATH=/app \
    PORT=8000 \
    UVICORN_PORT=8000

# Install Poetry
# hadolint ignore=DL3013
RUN /usr/local/bin/python -m pip install --upgrade pip --no-cache-dir \
    && pip install poetry --no-cache-dir \
    && poetry config virtualenvs.create false

# Copy poetry.lock* in case it doesn't exist in the repo
COPY \
     ./pyproject.toml \
     ./poetry.lock* \
     alembic.ini  \
     /app/

# Allow installing dev dependencies to run tests
ARG INSTALL_DEV=false
# We install the dependencies in a separate step from installing the app to take advantage of docker caching
RUN bash -c "if [ $INSTALL_DEV == 'true' ] ; then \
               poetry install --no-root --no-interaction --no-ansi -vvv ; \
             else \
               poetry install --no-root --no-dev --no-interaction --no-ansi -vvv ; \
               rm -rf ~/.cache/pypoetry/{cache,artifacts} ; \
             fi"

COPY scripts/ /app/scripts
COPY alembic/ /app/alembic
COPY app/ /app/app

# Now install the application itself
RUN bash -c "if [ $INSTALL_DEV == 'true' ] ; then \
               poetry install --no-interaction --no-ansi; \
             else \
               poetry install --no-interaction --no-ansi --no-dev; \
             fi; \
             rm -rf ~/.cache/pypoetry/{cache,artifacts}"

# Port is set via the env var `UVICORN_PORT`
CMD ["uvicorn", "app.main:app", "--proxy-headers", "--host", "0.0.0.0"]
