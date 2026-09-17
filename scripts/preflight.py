#!/usr/bin/env python3
"""Validate resolved production Compose without displaying credentials or starting services."""
import json
import re
import subprocess
from pathlib import Path


def validate(config, root):
    problems = []
    service = config.get("services", {}).get("agent", {})
    if "build" in service:
        problems.append("Use COMPOSE_FILE=docker-compose.prod.yml no .env.")
    if not re.fullmatch(r"ghcr\.io/fecabrall/omni-action-hub@sha256:[a-f0-9]{64}", service.get("image", "")):
        problems.append("Informe o digest oficial da imagem em OMNI_IMAGE.")
    env = service.get("environment", {})
    for key in ("GEMINI_API_KEY", "GEMINI_MODEL", "LINEAR_API_KEY", "LINEAR_TEAM_ID", "OMNI_ALLOWED_CHAT_ID"):
        if not env.get(key):
            problems.append(f"Preencha {key} no .env.")
    if not re.fullmatch(r"cht_[A-Za-z0-9_-]+", env.get("OMNI_ALLOWED_CHAT_ID", "")):
        problems.append("OMNI_ALLOWED_CHAT_ID deve ser a conversa autorizada cht_...")
    mounts = [m for m in service.get("volumes", []) if m.get("target") == "/var/lib/plow/credentials.host"]
    if len(mounts) != 1 or not mounts[0].get("read_only"):
        problems.append("Monte apenas o arquivo Plow, em modo somente leitura.")
    else:
        path = Path(mounts[0].get("source", ""))
        if not path.is_absolute():
            path = root / path
        if path.is_symlink() or not path.is_file():
            problems.append("Execute plow-agents mint nesta pasta; falta arquivo Plow regular.")
        elif path.stat().st_mode & 0o077:
            problems.append("Aplique chmod 600 ao arquivo de credenciais Plow.")
    env_path = root / ".env"
    if not env_path.is_file() or env_path.is_symlink() or env_path.stat().st_mode & 0o077:
        problems.append("O .env deve ser arquivo regular privado: chmod 600 .env.")
    return problems


def main():
    root = Path(__file__).resolve().parent.parent
    try:
        result = subprocess.run(["docker", "compose", "config", "--format", "json"],
                                cwd=root, capture_output=True, text=True, timeout=30)
        if result.returncode:
            print("Configuração incompleta. Preencha .env a partir de .env.example; verifique Docker Compose 2.30+.")
            return 1
        problems = validate(json.loads(result.stdout), root)
    except (OSError, ValueError, subprocess.TimeoutExpired):
        print("Não consegui validar o Compose. Verifique Docker e os arquivos de configuração.")
        return 1
    for message in problems:
        print(message)
    if not problems:
        print("Configuração local válida. Credenciais externas, disponibilidade da imagem e tempo de instalação ainda não foram testados.")
    return int(bool(problems))


if __name__ == "__main__":
    raise SystemExit(main())
