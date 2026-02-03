FROM python:3.14-slim

LABEL org.opencontainers.image.source=https://github.com/Wriveted/wriveted-api

WORKDIR /app/
SHELL ["/bin/bash", "-c"]

ENV USERNAME=wriveted \
  USER_UID=1000 \
  USER_GID=1000 \
  PIP_NO_CACHE_DIR=1 \
  POETRY_NO_INTERACTION=1 \
  PYTHONPATH=/app \
  PORT=8000 \
  POETRY_HOME=/home/wriveted/poetry \
  VIRTUAL_ENV=/home/wriveted/poetry-env \
  PATH="/home/wriveted/poetry-env/bin:/home/wriveted/poetry/bin:$PATH"

# hadolint ignore=DL3008
RUN apt-get update \
  && apt-get install --no-install-recommends -y \
    curl \
  && apt-get autoremove -y \
  && apt-get clean \
  && rm -rf /var/lib/apt/lists/* \
  && groupadd --gid ${USER_GID} ${USERNAME} \
  && useradd --uid ${USER_UID} --gid ${USER_GID} -m ${USERNAME}

USER ${USERNAME}

# Install Poetry
# hadolint ignore=DL3013
RUN /usr/local/bin/python -m pip install --upgrade pip --no-cache-dir \
  && /usr/local/bin/python -m pip install --upgrade setuptools --no-cache-dir \
  && python3 -m venv "${POETRY_HOME}" \
  && "${POETRY_HOME}/bin/pip" install poetry --no-cache-dir

# Copy poetry.lock* in case it doesn't exist in the repo
COPY --chown=${USERNAME}:${USER_GID} \
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

COPY --chown=${USERNAME}:${USER_GID} scripts/ /app/scripts
COPY --chown=${USERNAME}:${USER_GID} alembic/ /app/alembic
COPY --chown=${USERNAME}:${USER_GID} app/ /app/app

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
