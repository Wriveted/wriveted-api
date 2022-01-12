FROM python:3.10-slim
#FROM tiangolo/uvicorn-gunicorn-fastapi:python3.9

LABEL org.opencontainers.image.source=https://github.com/Wriveted/wriveted-api

# Allow statements and log messages to immediately appear in the Knative logs
ENV PYTHONUNBUFFERED True

WORKDIR /app/

RUN apt-get update -y \
    && apt-get install -y gcc libpq-dev

# Install Poetry
RUN /usr/local/bin/python -m pip install --upgrade pip
RUN pip install poetry && \
    poetry config virtualenvs.create false

# Copy poetry.lock* in case it doesn't exist in the repo
COPY ./pyproject.toml ./poetry.lock* /app/
COPY alembic.ini /app/

# Useful if we install Python packages from private repositories
#RUN mkdir -p -m 0600 ~/.ssh && ssh-keyscan github.com >> ~/.ssh/known_hosts

# Allow installing dev dependencies to run tests
ARG INSTALL_DEV=false
# We install the dependencies in a separate step from installing the app to take advantage of docker caching
RUN bash -c "if [ $INSTALL_DEV == 'true' ] ; then \
      poetry install --no-root --no-interaction --no-ansi -vvv ; \
    else \
    poetry install --no-root --no-dev --no-interaction --no-ansi -vvv ;\
    fi"

COPY alembic/ /app/alembic
COPY app/ /app/app

# Now install the application itself
RUN bash -c "if [ $INSTALL_DEV == 'true' ] ; then poetry install ; else poetry install --no-dev ; fi"

ENV PYTHONPATH=/app
ENV PORT=8000

#CMD uvicorn "app.main:app" --port $PORT --host 0.0.0.0

# If we would rather have multiple processes in our container
CMD gunicorn --bind :$PORT --workers 1 --worker-class uvicorn.workers.UvicornWorker --threads 8 app.main:app