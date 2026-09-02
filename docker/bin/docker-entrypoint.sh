#!/bin/bash
set -e

export MEDIA_ROOT="${MEDIA_ROOT:-/var/run/app/media}"
export STATIC_ROOT="${STATIC_ROOT:-/var/run/app/static}"
export MPLCONFIGDIR="${MPLCONFIGDIR:-/var/run/app/.matplotlib}"
export UWSGI_PROCESSES="${UWSGI_PROCESSES:-4}"
export DJANGO_SETTINGS_MODULE="${DJANGO_SETTINGS_MODULE:-hope_documents.config.settings}"

mkdir -p /var/run "${MEDIA_ROOT}" "${STATIC_ROOT}" "${MPLCONFIGDIR}"
# /var/run often symlinks to /run — chown the real paths, not only /var
chown -R hope:unicef /var "${MEDIA_ROOT}" "${STATIC_ROOT}" "${MPLCONFIGDIR}"

# One-shot upgrade (no Circus)
if [ "${1:-}" = "upgrade" ] && [ "$#" -eq 1 ]; then
  exec django-admin upgrade --with-check
fi

# Default role when none provided (image CMD)
if [ "$#" -eq 0 ]; then
  set -- web
fi

is_role() {
  case "$1" in
    web|run|celery|worker|beat|flower|streaming|stream-listener|upgrade)
      return 0
      ;;
    *)
      return 1
      ;;
  esac
}

# Passthrough for shell, check.sh, django-admin, etc.
if ! is_role "$1"; then
  exec "$@"
fi

export WEB_ENABLE=false
export CELERY_ENABLE=false
export BEAT_ENABLE=false
export FLOWER_ENABLE=false
export STREAM_DEFAULT_ENABLE=false
STREAMING=false
RUN_UPGRADE=false

for arg in "$@"; do
  case "$arg" in
    web|run)
      export WEB_ENABLE=true
      ;;
    celery|worker)
      export CELERY_ENABLE=true
      ;;
    beat)
      export BEAT_ENABLE=true
      ;;
    flower)
      export FLOWER_ENABLE=true
      ;;
    streaming|stream-listener)
      STREAMING=true
      ;;
    upgrade)
      RUN_UPGRADE=true
      ;;
    *)
      echo "Unknown role: ${arg}" >&2
      echo "Supported: web|run celery|worker beat flower streaming|stream-listener upgrade" >&2
      exit 1
      ;;
  esac
done

if [ "${WEB_ENABLE}" != true ] && [ "${CELERY_ENABLE}" != true ] && [ "${BEAT_ENABLE}" != true ] \
  && [ "${FLOWER_ENABLE}" != true ] && [ "${STREAMING}" != true ]; then
  echo "No process roles selected." >&2
  exit 1
fi

if [ "${WEB_ENABLE}" = true ] || [ "${RUN_UPGRADE}" = true ]; then
  django-admin upgrade --with-check
fi

# Build "-q a -q b" from a comma/space-separated STREAM_N_QUEUES value
stream_queue_args() {
  local queues="$1"
  local args="" q
  queues="${queues//,/ }"
  for q in ${queues}; do
    [ -z "${q}" ] && continue
    args="${args} -q ${q}"
  done
  # shellcheck disable=SC2086
  echo ${args}
}

# Always define stream slot envs so Circus can parse the ini
for i in 1 2 3 4 5; do
  eval "export STREAM_${i}_ENABLE=false"
  eval "queues=\"\${STREAM_${i}_QUEUES:-disabled}\""
  eval "export STREAM_${i}_QUEUES=\"${queues}\""
  eval "export STREAM_${i}_QUEUE_ARGS=\"$(stream_queue_args "${queues}")\""
  eval "export STREAM_${i}_CALLBACK=\"\${STREAM_${i}_CALLBACK:-disabled}\""
  eval "export STREAM_${i}_WORKERS=\"\${STREAM_${i}_WORKERS:-1}\""
done

if [ "${STREAMING}" = true ]; then
  echo "Configuring RabbitMQ topology (stream configure --queues)"
  stream configure --queues || echo "stream configure skipped"

  has_custom=false
  for i in 1 2 3 4 5; do
    eval "queues=\"\${STREAM_${i}_QUEUES}\""
    eval "callback=\"\${STREAM_${i}_CALLBACK}\""
    eval "workers=\"\${STREAM_${i}_WORKERS}\""

    if [ -n "${queues}" ] && [ "${queues}" != "disabled" ]; then
      if [ -z "${callback}" ] || [ "${callback}" = "disabled" ]; then
        echo "STREAM_${i}_CALLBACK is required when STREAM_${i}_QUEUES is set" >&2
        exit 1
      fi
      has_custom=true
      eval "export STREAM_${i}_ENABLE=true"
      eval "export STREAM_${i}_QUEUE_ARGS=\"$(stream_queue_args "${queues}")\""
      if [ -z "${workers}" ]; then
        eval "export STREAM_${i}_WORKERS=1"
        echo "Stream ${i}: queues=${queues} workers=1 (default)"
      else
        echo "Stream ${i}: queues=${queues} workers=${workers}"
      fi
    else
      eval "export STREAM_${i}_ENABLE=false"
      eval "export STREAM_${i}_QUEUES=disabled"
      eval "export STREAM_${i}_QUEUE_ARGS=\"-q disabled\""
      eval "export STREAM_${i}_CALLBACK=disabled"
      eval "export STREAM_${i}_WORKERS=1"
    fi
  done

  if ! $has_custom; then
    export STREAM_DEFAULT_ENABLE=true
    echo "Streaming: no STREAM_N_* overrides — starting default listener (settings queues/callback)"
  fi
fi

echo "Starting Circus (web=${WEB_ENABLE} celery=${CELERY_ENABLE} beat=${BEAT_ENABLE} flower=${FLOWER_ENABLE} stream_default=${STREAM_DEFAULT_ENABLE})"
export PATH="/venv/bin:/usr/local/bin:${PATH}"
export CIRCUSCTL_ENDPOINT="${CIRCUSCTL_ENDPOINT:-tcp://127.0.0.1:17955}"
CIRCUSD="${CIRCUSD:-/venv/bin/circusd}"
if [ ! -x "${CIRCUSD}" ]; then
  echo "circusd not found at ${CIRCUSD}." >&2
  echo "The image was built before circus was added. Rebuild it:" >&2
  echo "  docker compose -f compose.yml build --no-cache" >&2
  echo "  # or: make build" >&2
  exit 127
fi
exec "${CIRCUSD}" /conf/circus.ini
