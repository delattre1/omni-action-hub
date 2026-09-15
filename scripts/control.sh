#!/bin/sh
set -eu
cd "$(dirname "$0")/.."
# No execlineb/ifelse dependency. The CLI itself reads bootstrap's protected
# Plow environment. Direct docker exec remains the recommended diagnostic path.
container=${OMNI_CONTAINER:-$(docker compose ps -q agent)}
[ -n "$container" ] || { echo "Container do agente não encontrado" >&2; exit 1; }
exec docker exec -i "$container" /bin/sh -c 'exec omni "$@"' sh "$@"
