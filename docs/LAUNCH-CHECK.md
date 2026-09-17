# Revisão pré-lançamento — 16/09/2026

## Blind test técnico

Clone limpo do repositório mais patch da entrega, sem credenciais reais:

- `.env.example` sem chaves: Compose recusa iniciar por campos obrigatórios.
- `.env` preenchido com valores fictícios: `docker compose config` resolve
  `docker-compose.prod.yml` pelo `COMPOSE_FILE`; não há `build`.
- Imagem fixada por digest; memória 2.147.483.648 bytes; limite 256 processos.
- Arquivo Plow montado read-only e sem criação automática de diretório.
- `scripts/preflight.py` aprovado com arquivos 0600; testes cobrem ausência,
  permissões abertas, imagem mutável e seleção acidental do Compose de build.
- Chave sintética contendo `$` e `#` preservada em um container de prova com
  rede desabilitada. A saída serializada do Compose escapa `$` como `$$`; isso
  não é corrupção da variável entregue ao processo.
- Nenhuma segunda instância do agente foi iniciada na linha real.

Resultados: [launch-config-results.json](launch-config-results.json).
Suíte Python: **115 passed em 9,47 s**; Ruff sem erros.
O teste não mede o tempo completo de criação de contas/download/uso por terceiros.
Não se anuncia instalação em dois minutos, nem três testes humanos concluídos.

## Distribuição

O workflow v0.1.0 concluiu testes, landing e publicação da imagem:
https://github.com/fecabrall/omni-action-hub/actions/runs/34916273136
O primeiro pull sem acesso ao pacote privado retornou unauthorized. A abertura de
repositório e imagem foi autorizada pelo proprietário nesta rodada; o pull por digest passou após abrir o pacote.

v0.1.1 inclui MIT para código próprio, preservação de licenças upstream e ajustes
de instalação. Use o digest final da release indicado no `.env.example`.

## Segurança e limites

.gitignore ampliado para .env, backups de segredos, SQLite/sidecars, caches e
credenciais. Ele não impede inclusão forçada nem resolve vazamentos passados.
Chaves reais permanecem locais. Histórico e arquivos são revisados antes de abrir.

Pendentes: vídeo real publicado, registro/AGENT_ID confirmado, telemetria recebida
no servidor oficial, verificação pela equipe, testes humanos e prazo/hora oficiais.
O kit em AGENT-INDEX-SUBMISSION.md não afirma que a submissão já foi feita.

## Confirmação pública final

Repositório clonado sem credential helper. GHCR respondeu anonimamente ao manifest
de v0.1.1, cujo SHA-256 foi calculado e comparado ao header do registry.
Digest: `sha256:35abfee2a453caa0e22d92abe43799b28a4dd0b890a04fd1eded808bd544c4ee`.
Workflow: https://github.com/fecabrall/omni-action-hub/actions/runs/35169891728

O `.env.example` de `main` é atualizado após a publicação, para conter o digest
resultante do build. Para instalar, use `main` conforme o README; o arquivo de
configuração dentro de um arquivo-fonte da tag pode referenciar a release anterior.
