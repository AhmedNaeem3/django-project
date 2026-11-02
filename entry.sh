#!/bin/sh
set -e

case "$1" in
  web)
    exec python manage.py runserver "0.0.0.0:${CONTAINER_PORT}"
    ;;
  worker)
    exec celery -A config worker -l info
    ;;
  beat)
    exec celery -A config beat -l info --schedule=/tmp/celerybeat-schedule
    ;;
  *)
    echo "Error: Unknown service '$1'"
    echo "Usage: entry.sh {web|worker|beat}"
    exit 1
    ;;
esac
