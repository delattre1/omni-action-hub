# Roteiro reproduzível de avaliação — Omni-Action Hub

Este roteiro avalia o produto; não é documentação oficial de regras do hackathon.
Marque cada passo como executado, pendente ou não aplicável e registre evidências.

## Preparação e instalação

**Pré-requisitos:** Docker/Compose, contas e chaves Gemini/Linear, credencial de
agente Plow emitida para a conversa autorizada e acesso à imagem publicada.
No estado atual deste trabalho, a publicação da imagem ainda está pendente.

Obtenha `docker-compose.prod.yml` e `.env.prod.example`; copie o segundo para
`.env`, restrinja-o a 0600 e preencha as variáveis. `PLOW_CREDENTIALS_FILE` deve
apontar para o arquivo de credenciais Plow, não para uma chave colada qualquer.
Use `OMNI_IMAGE=registro/namespace/imagem@sha256:DIGEST_REAL`.

```sh
chmod 600 .env /caminho/para/plow-credentials
docker compose --env-file .env -f docker-compose.prod.yml up -d --wait
```

Não use simplesmente `docker compose up -d`: esse nome de arquivo não é o padrão
de descoberta do Compose. Registre tempo de pull, início, saúde e primeiro relato.
Não declare a meta de cinco minutos cumprida sem medir uma instalação independente.

## Experiência de uma pessoa

1. Na conversa autorizada, envie um screenshot com erro visível.
2. Envie `/bug O botão de checkout sumiu da tela principal` em até 60 segundos.
   Alternativamente, responda ao balão da foto com esse comando.
3. Registre: horário do envio, ACK, eventual aviso de retry e resposta final.
4. Abra o link e confira título, evidência, prioridade sugerida e anexo.
5. Compare o texto do relatório com a imagem: marque afirmações sem evidência.

A foto sozinha deve ficar em silêncio. Uma descrição sem `/bug` ou outro comando
aceito deve receber orientação, sem criar ticket. Os tempos anteriores são
referências históricas, não limites garantidos de entrega.

## Diagnóstico e infraestrutura

Para a instalação atual, use diretamente o container informado:

```sh
docker exec -i omni-action-hub-agent-1 /bin/sh -c 'omni doctor --deep'
docker inspect omni-action-hub-agent-1 --format '{{.State.Health.Status}} {{.HostConfig.Memory}} {{.HostConfig.PidsLimit}} {{.Config.Healthcheck.Interval}}'
```

Em outra instalação, obtenha o ID com `docker compose --env-file .env -f
docker-compose.prod.yml ps -q agent` e use-o no lugar do nome acima. `--deep`
usa tokens reais; não cria tickets. Para a configuração de produção proposta,
espere memória de 2147483648 bytes, limite de 256 processos e intervalo de
30000000000 ns. `0` em memória não significa consumo zero: significa ausência
de limite específico do container.

## Performance offline

Em um ambiente Python com o projeto e as dependências de teste instalados:

```sh
python -m pytest -q -s tests/test_assessment.py
python scripts/benchmark-vision.py
```

O benchmark retorna bytes, dimensões e duração. Não procure uma linha de
compressão nos logs até que essa instrumentação exista. Para avaliar OCR, use
capturas com texto conhecido e compare com o relatório; reduzir bytes não prova
redução proporcional de tokens nem preservação universal da legibilidade.

## Falhas controladas

```sh
python -m pytest -q tests/test_product.py tests/test_clients.py tests/test_workflow.py
```

Critérios separados:

- **503/timeout transitório do Gemini:** até três tentativas, aviso único e
  fallback marcado `ai-pending`, desde que Plow e Linear continuem acessíveis.
- **401/403:** mensagem de erro de configuração, sem retry automático nem fallback.
- **Criação Linear com resultado incerto:** reconciliação pelo UUID; sem nova
  mutação quando a dúvida persiste.
- **Falha de resposta após criação:** reutiliza o ticket salvo.

Use as injeções dos testes. Não troque a chave real nem desligue toda a rede
para fingir indisponibilidade apenas do Gemini. Um teste de desconexão total é
outro cenário e não pode exigir que serviços remotos continuem funcionando.

## Concorrência e isolamento

O teste offline usa 24 jobs por limite de workers e verifica pico de inferência,
ACKs, tickets únicos e esvaziamento da fila. Registre que as APIs são simuladas.
Para testar três pessoas, prepare três instalações/conversas autorizadas com
credenciais próprias. Pessoas não autorizadas na mesma instalação devem ser
rejeitadas, não usadas como prova de processamento concorrente.

## Registro de aprovação

Para cada pessoa, registre: instalação assistida ou não, tempo de preparação,
tempo da instalação, ACK, conclusão, correção do relatório e utilidade de 1 a 5.
Anote falhas observadas e passos necessários para recuperação. Não selecione
apenas os exemplos bem-sucedidos para declarar a validação concluída.
