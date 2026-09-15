# Da pasta local à distribuição verificável

Estado: workflow preparado; **nenhuma imagem nova foi publicada por esta mudança**.
Repositório privado: https://github.com/fecabrall/omni-action-hub. O namespace é
derivado de `github.repository` quando o workflow roda. Não implica acesso público.

## Publicar

1. Coloque **o conteúdo de omni-action-hub na raiz** do repositório GitHub escolhido.
   Respeite `.gitignore`: nunca versione `omni.env`, `.env`, `plow-credentials`,
   `work/`, datasets privados ou volumes. Não crie o repositório no diretório pai.
2. Ative GitHub Actions e permissão de escrita de packages para o workflow.
   Proteja `main` e tags `v*` com rulesets: somente mantenedores publicam versões.
3. Abra PR; jobs `tests` e `website` validam Python, TypeScript e build estático.
   A criação de imagem só ocorre em push de tag `vMAJOR.MINOR.PATCH`, após ambos.
4. No checkout revisado, crie e envie uma tag de versão, ou use Actions →
   Verify and publish → Run workflow em `main`, informando `v0.1.0`. O job `image` publica
   `ghcr.io/<owner>/<repository>:<tag>` e `:sha-<commit>`. O resumo e o artifact
   `image-reference` contêm `OMNI_IMAGE=ghcr.io/...@sha256:...`.
5. Defina visibilidade do pacote conforme a distribuição desejada. Faça um pull
   limpo pelo **digest** em outra máquina. Pacotes privados requerem login GHCR.
   Nenhuma credencial Gemini/Linear/Plow é necessária para o build.

Actions fixadas por SHA, token de leitura fora do job de publicação, SBOM e
proveniência BuildKit. Isso fornece rastreabilidade; não equivale a assinatura
independente, scanner integral ou ausência de vulnerabilidades. Tags podem mudar;
o digest identifica os bytes a implantar. A base Docker já está fixada por digest.
Dependabot propõe atualizações; elas ainda precisam passar na revisão e nos testes.

## Implantar a imagem pronta

```sh
cp .env.prod.example .env
chmod 600 .env
# Preencha localmente; use o digest do artifact, nunca uma chave no shell history.
docker compose --env-file .env -f docker-compose.prod.yml up -d --wait
# Na instalação atual:
docker exec omni-action-hub-agent-1 /bin/sh -c 'omni doctor --deep'
```

Em outra pasta, obtenha o nome/ID com `docker compose --env-file .env -f
docker-compose.prod.yml ps -q agent` e use-o em `docker exec`.
O Compose aplica 2 GB / 256 processos, mas não valida o formato de `OMNI_IMAGE`;
cabe preencher o digest publicado. Não rode `docker compose config` em logs
públicos: ele pode expandir chaves.

## VPS / AWS / GCP

O mesmo Compose é um deploy de **host único**, Linux amd64 com Docker/Compose
2.30+, saída TLS e disco persistente. Requer credencial de linha Plow válida,
pré-provisionada e acessível nesse host. A portabilidade do gateway depende do
serviço Plow e não foi validada em uma nuvem nesta entrega. Não implica ECS,
Cloud Run, autoscaling nem alta disponibilidade. Não compartilhe a mesma linha
ou volume entre dois agentes ativos. Faça backup consistente do volume antes de
migrar; pare o agente antigo antes de ativar o substituto.

Rollback: volte `OMNI_IMAGE` para um digest conhecido e execute Compose novamente,
verificando compatibilidade do schema SQLite. Não apague o volume para recomeçar:
isso remove a memória de deduplicação. Alterações de schema exigem plano próprio.

A landing é independente, exportada em `website/out`, sem segredos nem API no
browser. Hospede essa pasta em um provedor estático. Seu deploy não inicia o agente.

Referência: [GitHub — Publishing Docker images](https://docs.github.com/en/actions/tutorials/publish-packages/publish-docker-images).
