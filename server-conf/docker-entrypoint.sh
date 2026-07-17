#!/bin/sh
# Dispatches between the two things this image can do:
#
#   docker run <image>                          -> starts the web API
#                                                    (nginx + uwsgi via
#                                                    supervisord), same as
#                                                    before this file existed.
#   docker run <image> scan -s /import -l /photodb
#                                                -> runs pdbscanner.py (the
#                                                    headless "scan only"
#                                                    CLI) with the given
#                                                    arguments, then exits.
#
# The "scan" form is handy for a one-off `docker run --rm -v ...` import
# job against a store that's either a mounted local volume or a remote
# webservice URL - it doesn't need nginx/uwsgi running at all.
set -e

if [ "$1" = "scan" ]; then
    shift
    exec python /project/pdbscanner.py "$@"
fi

# uwsgi (see server-conf/uwsgi.ini) drops privileges to the unprivileged
# "nginx" user before serving requests, so the store directory - freshly
# created inside the image, or a bind-mounted host volume that's typically
# owned by root/whatever UID owns it on the host - needs to be writable by
# that user before the app can create/open its sqlite db and write photos.
STORE_PATH="${PH_STORE_URL:-/photodb}"
case "$STORE_PATH" in
    http://* | https://*)
        # Remote store - nothing local to fix up.
        ;;
    *)
        mkdir -p "$STORE_PATH"
        chown -R nginx:nginx "$STORE_PATH"
        ;;
esac

exec /usr/bin/supervisord -c /etc/supervisor/supervisord.conf
