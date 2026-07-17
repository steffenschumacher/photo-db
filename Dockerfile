FROM python:3.11-slim-bullseye AS base

FROM base AS install

ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && \
    apt-get install -y --no-install-recommends nginx supervisor && \
    useradd --no-create-home nginx && \
    rm -f /etc/nginx/sites-enabled/default


ENV PYTHONPATH "${PYTHONPATH}:/project/"
# ENV REQUESTS_CA_BUNDLE=/etc/ssl/certs/ca-certificates.crt

# where the images and the database is stored - create volume for this
ENV PH_STORE_URL=/photodb
ENV PH_STORE_USER=someshareduser
ENV PH_STORE_PASS=somesharedpass!QAZ2wsx
# image hash size - larger is more detailed, but costs CPU/mem/bw
ENV PH_HASH_SIZE=70
EXPOSE 80/tcp

RUN set -eux; \
    \
    savedAptMark="$(apt-mark showmanual)"; \
    apt-get update -y;  \
    apt-get install -qy gcc; \
    pip install --no-cache-dir uwsgi; \
    apt-mark auto '.*' > /dev/null; \
	  [ -z "$savedAptMark" ] || apt-mark manual $savedAptMark > /dev/null; \
	  apt-get purge -y --auto-remove -o APT::AutoRemove::RecommendsImportant=false; \
   	rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/*


# Set default workdir
WORKDIR /project


# Install python dependencies
COPY ./requirements-api.txt .
RUN pip install --no-cache-dir -r requirements-api.txt


# copy server configs
COPY server-conf/nginx.conf /etc/nginx/
COPY server-conf/flask-site-nginx.conf /etc/nginx/conf.d/
COPY server-conf/uwsgi.ini /etc/uwsgi/
COPY server-conf/supervisord.conf /etc/supervisor/
# Copy the project code to the container
COPY manage.py .
COPY photo_db photo_db

CMD ["/usr/bin/supervisord", "-c", "/etc/supervisor/supervisord.conf"]
