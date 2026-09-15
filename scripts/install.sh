#!/bin/sh
set -eu
umask 077
cd "$(dirname "$0")/.."
for cmd in python3 git docker; do
  command -v "$cmd" >/dev/null 2>&1 || { echo "Instale $cmd antes de continuar." >&2; exit 1; }
done
docker info >/dev/null 2>&1 || { echo "Abra o Docker Desktop e aguarde o serviço iniciar." >&2; exit 1; }
docker compose version >/dev/null
# This directory is ignored by git; it holds only the official credential CLI.
pin=8ce907e220ab67018d6857e8054a41eed4ecd279
if [ ! -d work/plow-agents/.git ]; then
  mkdir -p work
  git clone https://github.com/plow-pbc/plow-agents.git work/plow-agents
fi
git -C work/plow-agents checkout --detach "$pin"
if [ ! -f plow-credentials ]; then
  work/plow-agents/bin/plow-agents login
  work/plow-agents/bin/plow-agents lines
  echo "Escolha uma linha livre (ln_...). Se não houver, use login --new-line."
  IFS= read -r line
  case "$line" in ln_*) ;; *) echo "Linha inválida" >&2; exit 1 ;; esac
  work/plow-agents/bin/plow-agents mint "$line"
fi
if [ ! -f omni.env ]; then python3 scripts/setup.py; fi
if [ -n "${OMNI_IMAGE:-}" ]; then
  docker compose pull
  docker compose up --no-build -d
else
  docker compose up --build -d
fi
echo "Iniciado. Execute: sh scripts/control.sh doctor"
