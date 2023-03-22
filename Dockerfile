FROM python:3.11

LABEL org.opencontainers.image.source=https://github.com/Wriveted/wriveted-api

WORKDIR /app/
SHELL ["/bin/bash", "-c"]

ENV PIP_NO_CACHE_DIR=1 \
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
  && "${POETRY_HOME}/bin/pip" install poetry --no-cache-dir \
  # https://python-poetry.org/blog/announcing-poetry-1.4.0/#faster-installation-of-packages
  # a somewhat breaking change was introduced in 1.4.0 that requires this config or else certain packages fail to install
  # in our case it was the openai package
  && "${POETRY_HOME}/bin/poetry" config installer.modern-installation false

# Copy poetry.lock* in case it doesn't exist in the repo
COPY \
  ./pyproject.toml \
  ./poetry.lock* \
  alembic.ini  \
  /app/

# Allow installing dev dependencies to run tests
ARG INSTALL_DEV=false

# We install the dependencies in a separate step from installing the app to take advantage of docker caching
RUN python3 -m venv ${VIRTUAL_ENV} \
  && if [ $INSTALL_DEV == 'true' ] ; then \
  poetry install --no-root --no-interaction --no-ansi -vvv; \
  else \
  poetry install --no-root --only main --no-interaction --no-ansi -vvv; \
  fi \
  && rm -rf ~/.cache/pypoetry/{cache,artifacts}

COPY scripts/ /app/scripts
COPY alembic/ /app/alembic
COPY app/ /app/app

RUN python3 -m venv ${VIRTUAL_ENV} \
  && if [ $INSTALL_DEV == 'true' ] ; then \
  poetry install --no-interaction --no-ansi; \
  else \
  poetry install --no-interaction --no-ansi --only main; \
  fi \
  && rm -rf ~/.cache/pypoetry/{cache,artifacts}

# Port is set via the env var `UVICORN_PORT`
#CMD ["uvicorn", "app.main:app", "--proxy-headers", "--host", "0.0.0.0"]

# Run under gunicorn
# No need for gunicorn threads https://github.com/tiangolo/fastapi/issues/551#issuecomment-584308118
# If we would rather have multiple processes in our container
# Timeout is set to 0 to disable the timeouts of the workers to allow Cloud Run to handle instance scaling.
# When the PORT environment variable is defined, the default bind is ['0.0.0.0:$PORT']
ENTRYPOINT ["gunicorn", "--workers", "1", "--worker-class", "uvicorn.workers.UvicornWorker", "--threads", "1", "--timeout", "0"]
CMD ["app.main:app"]

# To run internal api use the following command:
#CMD ["gunicorn", "--workers", "1", "--worker-class", "uvicorn.workers.UvicornWorker", "--threads", "1", "--timeout", "0", "app.internal_api:internal_app"]
