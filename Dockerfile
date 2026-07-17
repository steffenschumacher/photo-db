FROM python:3.13-slim-bookworm AS base

FROM node:22.23.1-bookworm-slim AS web-build
WORKDIR /web
COPY web-ui/package.json web-ui/package-lock.json ./
RUN npm ci
COPY web-ui/ ./
RUN npm run build

FROM base AS install

ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && \
    apt-get install -y --no-install-recommends nginx supervisor && \
    useradd --no-create-home nginx && \
    rm -f /etc/nginx/sites-enabled/default


ENV PYTHONPATH="/project/"
# ENV REQUESTS_CA_BUNDLE=/etc/ssl/certs/ca-certificates.crt

# where the images and the database is stored - create volume for this
ENV PH_STORE_URL=/photodb
# PH_STORE_USER / PH_STORE_PASS must be provided at runtime (e.g. via
# `docker run -e` / compose `environment:` / a secrets store) - there is no
# usable built-in default, credentials must be set explicitly.
# image hash size - larger is more detailed, but costs CPU/mem/bw
ENV PH_HASH_SIZE=70
EXPOSE 80/tcp

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /usr/local/bin/

# Set default workdir
WORKDIR /project

# Install python dependencies (server/API side only - no ui/raw extras).
# gcc is only needed transiently to build the uwsgi wheel (it has no
# manylinux wheel for this base image) - install it, build, then purge it
# in the same layer so it never ends up in the final image size.
COPY pyproject.toml uv.lock ./
RUN set -eux; \
    savedAptMark="$(apt-mark showmanual)"; \
    apt-get update -y; \
    apt-get install -qy gcc; \
    uv sync --extra api --no-dev --no-install-project; \
    uv pip install uwsgi; \
    apt-mark auto '.*' > /dev/null; \
    [ -z "$savedAptMark" ] || apt-mark manual $savedAptMark > /dev/null; \
    apt-get purge -y --auto-remove -o APT::AutoRemove::RecommendsImportant=false; \
    rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/*

ENV PATH="/project/.venv/bin:${PATH}"

# copy server configs
COPY server-conf/nginx.conf /etc/nginx/
COPY server-conf/flask-site-nginx.conf /etc/nginx/conf.d/
COPY server-conf/uwsgi.ini /etc/uwsgi/
COPY server-conf/supervisord.conf /etc/supervisor/
COPY server-conf/docker-entrypoint.sh /usr/local/bin/docker-entrypoint.sh
RUN chmod +x /usr/local/bin/docker-entrypoint.sh
# Copy the project code to the container
COPY manage.py .
COPY pdbscanner.py .
COPY photo_db photo_db
COPY --from=web-build /web/dist/web-ui/browser photo_db/web/browser

ENTRYPOINT ["/usr/local/bin/docker-entrypoint.sh"]
