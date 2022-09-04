FROM python:3.10-slim

LABEL org.opencontainers.image.source=https://github.com/Wriveted/wriveted-api

WORKDIR /app/

# Allow statements and log messages to immediately appear in the Knative logs
ENV PYTHONUNBUFFERED=True \
    PIP_NO_CACHE_DIR=1 \
    POETRY_NO_INTERACTION=1 \
    PYTHONPATH=/app \
    PORT=8000 \
    POETRY_HOME=/opt/poetry \
    VIRTUAL_ENV=/poetry-env \
    PATH="/poetry-env/bin:/opt/poetry/bin:$PATH"

# Install Poetry
# hadolint ignore=DL3013
RUN /usr/local/bin/python -m pip install --upgrade pip --no-cache-dir \
    && python3 -m venv "${POETRY_HOME}" \
    && "${POETRY_HOME}/bin/pip" install poetry

# Copy poetry.lock* in case it doesn't exist in the repo
COPY \
     ./pyproject.toml \
     ./poetry.lock* \
     alembic.ini  \
     /app/

# Allow installing dev dependencies to run tests
ARG INSTALL_DEV=false
# We install the dependencies in a separate step from installing the app to take advantage of docker caching
RUN bash -c "python3 -m venv ${VIRTUAL_ENV}; \
             if [ $INSTALL_DEV == 'true' ] ; then \
               poetry install --no-root --no-interaction --no-ansi -vvv ; \
             else \
               poetry install --no-root --no-dev --no-interaction --no-ansi -vvv ; \
               rm -rf ~/.cache/pypoetry/{cache,artifacts} ; \
             fi"

COPY scripts/ /app/scripts
COPY alembic/ /app/alembic
COPY app/ /app/app

# Now install the application itself
RUN bash -c "python3 -m venv ${VIRTUAL_ENV}; \
             if [ $INSTALL_DEV == 'true' ] ; then \
               poetry install --no-interaction --no-ansi; \
             else \
               poetry install --no-interaction --no-ansi --no-dev; \
             fi; \
             rm -rf ~/.cache/pypoetry/{cache,artifacts}";

# Port is set via the env var `UVICORN_PORT`
#CMD ["uvicorn", "app.main:app", "--proxy-headers", "--host", "0.0.0.0"]

# Run under gunicorn
# No need for gunicorn threads https://github.com/tiangolo/fastapi/issues/551#issuecomment-584308118
# If we would rather have multiple processes in our container
# Timeout is set to 0 to disable the timeouts of the workers to allow Cloud Run to handle instance scaling.
# hadolint ignore=DL3025
CMD gunicorn --bind :$PORT --workers 1 --worker-class uvicorn.workers.UvicornWorker --threads 1 app.main:app --timeout 0
