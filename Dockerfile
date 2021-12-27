FROM python:3.9
#FROM tiangolo/uvicorn-gunicorn-fastapi:python3.9

LABEL org.opencontainers.image.source=https://github.com/Wriveted/wriveted-api

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

EXPOSE 8000
CMD uvicorn "app.main:app" --port 8000 --host 0.0.0.0
