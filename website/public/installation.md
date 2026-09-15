# Instalar Omni-Action Hub

Status: distribuição pública em preparação. Não há link de download de imagem
pública confirmado nesta página. Obtenha o repositório e digest com o mantenedor.

Pré-requisitos: Docker com Compose 2.30+, conta/linha Plow provisionada pelo fluxo
plow-agents login → seleção de linha → mint, chave API Gemini, chave Linear,
UUID do time e conversa autorizada. Cada instalação usa suas próprias credenciais.
A preparação de contas é separada do tempo de instalação do agente.

1. Na pasta do projeto, copie `.env.prod.example` para `.env`; execute `chmod 600 .env`.
2. Preencha `OMNI_IMAGE` com a imagem publicada por `@sha256:...`,
   `PLOW_CREDENTIALS_FILE` com o caminho absoluto do arquivo mintado (modo 0600),
   `GEMINI_API_KEY`, `GEMINI_MODEL`, `LINEAR_API_KEY`, `LINEAR_TEAM_ID`,
   `OMNI_ALLOWED_CHAT_ID`. Projeto e AGENT_ID são opcionais conforme configuração.
3. Execute `docker compose --env-file .env -f docker-compose.prod.yml up -d --wait`.
4. Obtenha o ID do agente com `docker compose --env-file .env -f docker-compose.prod.yml ps -q agent`.
5. Execute `docker exec ID_DO_CONTAINER /bin/sh -c 'omni doctor --deep'`.
   O diagnóstico profundo faz chamada Gemini real, com consumo de API.
6. Envie um print e “Registra esse bug” na conversa autorizada. Confira anexo e link.

A base é linux/amd64; Apple Silicon usa emulação. Nuvem requer host compatível,
disco persistente e gateway Plow acessível. Uma linha e um volume por instalação.
Não inclua chaves em Git nem em mensagens. Não exponha o Docker socket à internet.

Parar: `docker compose --env-file .env -f docker-compose.prod.yml down`.
Isso preserva o volume. Removê-lo com `down -v` apaga histórico e deduplicação;
faça isso apenas para desinstalação definitiva após backup e revisão dos dados.
Revogue credenciais nos respectivos serviços e remova os arquivos locais quando
encerrar a instalação. Tickets já criados permanecem no Linear.
