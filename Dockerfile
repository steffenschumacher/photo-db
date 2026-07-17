FROM python:3.13-slim-bookworm AS base

FROM base AS install

ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && \
    apt-get install -y --no-install-recommends nginx supervisor && \
    useradd --no-create-home nginx && \
    rm -f /etc/nginx/sites-enabled/default


ENV PYTHONPATH="${PYTHONPATH}:/project/"
# ENV REQUESTS_CA_BUNDLE=/etc/ssl/certs/ca-certificates.crt

# where the images and the database is stored - create volume for this
ENV PH_STORE_URL=/photodb
# PH_STORE_USER / PH_STORE_PASS must be provided at runtime (e.g. via
# `docker run -e` / compose `environment:` / a secrets store) - there is no
# usable built-in default, credentials must be set explicitly.
# image hash size - larger is more detailed, but costs CPU/mem/bw
ENV PH_HASH_SIZE=70
EXPOSE 80/tcp

RUN set -eux; \
    \
    savedAptMark="$(apt-mark showmanual)"; \
    apt-get update -y;  \
    apt-get install -qy gcc; \
    apt-mark auto '.*' > /dev/null; \
	  [ -z "$savedAptMark" ] || apt-mark manual $savedAptMark > /dev/null; \
	  apt-get purge -y --auto-remove -o APT::AutoRemove::RecommendsImportant=false; \
   	rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/*

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /usr/local/bin/

# Set default workdir
WORKDIR /project

# Install python dependencies (server/API side only - no ui/raw extras)
COPY pyproject.toml uv.lock ./
RUN uv sync --extra api --no-dev --no-install-project && \
    uv pip install uwsgi

ENV PATH="/project/.venv/bin:${PATH}"

# copy server configs
COPY server-conf/nginx.conf /etc/nginx/
COPY server-conf/flask-site-nginx.conf /etc/nginx/conf.d/
COPY server-conf/uwsgi.ini /etc/uwsgi/
COPY server-conf/supervisord.conf /etc/supervisor/
# Copy the project code to the container
COPY manage.py .
COPY photo_db photo_db

CMD ["/usr/bin/supervisord", "-c", "/etc/supervisor/supervisord.conf"]
