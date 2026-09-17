#!/usr/bin/env python3
"""Local setup with standard-library Python; secrets never travel through chat."""
import argparse
import getpass
import json
import os
import re
import shlex
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def ask(label, default="", secret=False):
    prompt = label + (f" [{default}]" if default else "") + ": "
    value = (getpass.getpass(prompt) if secret else input(prompt)).strip() or default
    if "\n" in value or "\r" in value or "\x00" in value:
        raise ValueError("Entrada inválida")
    return value


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--chat-id", action="store_true", help="Print authorized chat ID without prompting for API keys")
    args = parser.parse_args()
    os.umask(0o077)
    print("Configure o Plow primeiro: plow-agents login; plow-agents lines; plow-agents mint <linha>.")
    print("Execute mint nesta pasta. O comando grava plow-credentials antes do Docker iniciar.")
    credentials = ROOT / "plow-credentials"
    if not credentials.is_file():
        raise SystemExit("Falta plow-credentials. Consulte o README e execute novamente.")
    os.chmod(credentials, 0o600)
    target = ROOT / "omni.env"
    if target.exists() and not args.chat_id:
        raise SystemExit("omni.env já existe. Edite-o localmente para alterar a configuração.")
    # Read mint's dotenv as data, never source a shell file.
    pairs = {}
    for line in credentials.read_text().splitlines():
        words = shlex.split(line, comments=True)
        if len(words) == 1 and "=" in words[0]:
            key, value = words[0].split("=", 1)
            pairs[key] = value
    base = pairs.get("PLOW_API_BASE", "")
    if base not in ("https://api.plow.co", "https://api.plow.dev") or not pairs.get("PLOW_AGENT_TOKEN"):
        raise SystemExit("Credencial Plow inválida. Execute mint novamente.")
    try:
        request = urllib.request.Request(base + "/v1/agents/cloud/me",
            headers={"Authorization": "Bearer " + pairs["PLOW_AGENT_TOKEN"]})
        with urllib.request.urlopen(request, timeout=20) as response:
            identity = json.load(response)
        homes = []
        for chat in identity["chats"]:
            members = [p for p in chat.get("participants", []) if p.get("type") == "member"]
            agents = [p for p in chat.get("participants", []) if p.get("type") == "agent"]
            if chat.get("status") == "active" and len(members) == len(agents) == 1 and members[0].get("role") == "owner" and agents[0].get("relationship") == "self":
                homes.append(chat["uid"])
        if len(homes) != 1:
            raise ValueError("ambiguous home")
    except Exception:
        raise SystemExit("Não consegui identificar a conversa principal. Revise o acesso Plow; nenhum segredo foi exibido.")
    if args.chat_id:
        print(homes[0])
        return
    print("Conversa principal identificada pelo Plow. O agente aceitará somente pedidos do proprietário nela.")
    values = {
        "OMNI_ALLOWED_CHAT_ID": homes[0],
        "GEMINI_API_KEY": ask("Chave da API Gemini", secret=True),
        "GEMINI_MODEL": ask("Modelo Gemini", "gemini-3.8-flash"),
        "LINEAR_API_KEY": ask("Chave pessoal Linear", secret=True),
        "LINEAR_TEAM_ID": ask("UUID do time Linear"),
        "LINEAR_PROJECT_ID": ask("UUID do projeto Linear (opcional)"),
        "AGENT_ID": ask("ID registrado no Agent Index (vazio durante desenvolvimento)"),
    }
    for key in ("OMNI_ALLOWED_CHAT_ID", "GEMINI_API_KEY", "LINEAR_API_KEY", "LINEAR_TEAM_ID"):
        if not values[key]:
            raise SystemExit("Campo obrigatório não preenchido; nenhum arquivo foi gravado.")
    if not re.fullmatch(r"cht_[A-Za-z0-9_-]+", values["OMNI_ALLOWED_CHAT_ID"]):
        raise SystemExit("UID de conversa inválido")
    fd = os.open(target, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, "w") as f:
        for key, value in values.items():
            f.write(key + "=" + value + "\n")
    print("Configuração salva em omni.env (0600). Imagens serão enviadas ao Gemini e ao Linear.")
    print("A edição de competição reporta contagens de tokens ao Agent Index quando AGENT_ID está configurado.")
    print("Configuração de desenvolvimento: docker compose -f compose.yml up --build -d")


if __name__ == "__main__":
    main()
