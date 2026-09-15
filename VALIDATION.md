# Validação — 12/09/2026

## Ambiente real

- Container `omni-action-hub-agent-1`: **running / healthy**.
- Diagnóstico direto por `docker exec`: **Gemini ok; Linear ok; Plow ok**.
- Número da identidade Plow corresponde a **+16503156604**.
- WebSocket conectado, confirmado pelo evento `plow_websocket_connected`.
- Imagem local `omni-action-hub:0.1.0` construída e executada em Apple Silicon
  com emulação `linux/amd64`. Ainda não publicada em registry externo.

## Teste com serviços reais e entrada simulada

A captura foi criada artificialmente, sem dados pessoais. O evento entrou na
fila com identificador `simulated-e2e-20260912-01`; não foi enviado do telefone.
A inferência, o upload, a criação e a resposta usaram APIs reais.

- Trabalho: `0f118c5c-cd42-4767-8ea8-96c1dc3226d2`.
- Card: [OMN-5 — TESTE E2E](https://linear.app/omni-qa-felipe/issue/OMN-5/teste-e2e-erro-500-ao-salvar-tarefa-na-pagina-create-task).
- Gemini leu o erro 500, classificou como bug e extraiu prioridade alta,
  projeto mencionado “Demo UI” e tags “frontend, bug”.
- Consulta posterior ao Linear: HTTP 200, sem erros GraphQL; time e projeto
  correspondem à configuração. Prioridade operacional mantida em 0.
- Metadados e screenshot confirmados na descrição.
- Imagem privada relida: HTTP 200, `image/png`, 50.532 bytes.
- Resposta encontrada no Plow: uma mensagem correspondente, direção `outbound`,
  status **delivered**, em `2026-09-12T03:02:06.490000Z`.
- Fila: `done`, entrega `sent`, uma tentativa. Imagem temporária removida.

## Correções e verificações

- **46 testes passando**, incluindo reconexão, ambiente s6, metadados,
  classificação, deduplicação, retomada e recuperação de respostas.
- Corrigida a falsa falha no diagnóstico: `docker exec` não herdava as variáveis
  publicadas pelo s6 após o boot. O CLI agora lê arquivos protegidos diretamente.
- Corrigido o crash de inicialização: registro explícito de `plow_chat` no
  registry Hermes antes de instanciar o adapter.
- Reconexão separada da fila persistente, com espera de 5 até 300 segundos.
  Tickets WebSocket são renovados pelo transporte oficial. Tokens de agente
  realmente revogados exigem rotação; não há promessa de renovação automática.
- Lint, sintaxe shell, configuração Compose e build Docker verificados.
- Coletor oficial Agent Index testado offline, com checksum, sem dupla contagem.
  `AGENT_ID` está vazio: não houve envio de telemetria ao leaderboard.
- Resolução de anexos citados testada com as funções reais da revisão fixada
  do plugin. Cinco operações GraphQL validadas contra o schema oficial Linear.

## Pendências

1. Enviar captura real do telefone para validar entrada iMessage → Plow → fila.
   A conexão está ativa, mas a injeção local do teste não cobre essa etapa.
2. Fazer três pessoas instalarem sem assistência e medir os tempos reais.
3. Publicar repositório/imagem, configurar `AGENT_ID`, validar o leaderboard
   e obter a verificação da organização do evento.

## Revisões

- Base: `a71f71d6a988ac5fb0cddf866f298b56433a98c7`.
- Digest: `sha256:5a1aa4f068f836461b19aaeddae365485c685894441eb2605222461c889a0f44`.
- Plugin: `baa1261174469744b9d915f062f7bdb2e304f9a5`.
- CLI Plow: `8ce907e220ab67018d6857e8054a41eed4ecd279`.
- Agent Index: `f900ff144076f0a766584b6ec4d0993600779b16`.

## Buffer e replies — 12/09/2026

- Suíte offline: **61 testes aprovados**, incluindo prova com `asyncio.sleep(2)`
  real entre foto e comando. APIs Gemini/Linear/Plow simuladas nessa prova;
  Workflow, normalização da imagem, deduplicação e SQLite são os de produção.
- Script reproduzível: `scripts/test-image-buffer.sh` (seleção de testes de
  buffer, adaptador e clientes). Prova observada: aproximadamente 2,01 segundos,
  um ticket e uma resposta contendo o link.
- Testados: janela expirada, remetente diferente, múltiplas fotos, referência
  inexistente, reply nativo, GUID após reinício, replay de eventos, consumo
  pela próxima mensagem, limpeza após 24 horas e foto/reply compartilhando
  o mesmo arquivo de cache no lote do transporte.
- Linear: falhas ConnectError/ConnectTimeout/PoolTimeout recuperam na terceira
  tentativa mantendo UUID; esgotamento é informado; ReadTimeout permanece sem
  repetir a mutação e usa a recuperação por reconciliação já testada.
- Lint: `ruff check src tests` aprovado.
- O recebimento real de foto e comando separados por um telefone ainda precisa
  de validação de campo; esta prova não equivale a esse teste externo.
- Versão reconstruída e aplicada ao Docker. Após reinício, container `healthy`;
  `docker exec -i omni-action-hub-agent-1 /bin/sh -c 'omni doctor'` retornou
  `gemini: ok`, `linear: ok`, `plow: ok`.

## Incidente real de anexos — 13/09/2026

Causa confirmada no container: `/var/lib/hermes/image_cache` era root:root 0700,
enquanto o gateway executava como `hermes` (UID 10000). O download do anexo real
retornou HTTP 200 (1.118.755 bytes), mas o resolvedor oficial executado como UID
10000 retornou zero arquivos e um marcador de indisponibilidade. Nenhuma imagem
estava no buffer SQLite. A imagem chegou às 03:01:36 UTC, o texto às 03:01:41 UTC,
com o mesmo UID de remetente. As hipóteses de chave divergente e texto chegando
primeiro não explicam esse episódio. Os logs antigos só registravam conexão,
portanto o diagnóstico exigiu metadados autenticados e reprodução sob o UID real.

A nova versão usa cache privado do Omni, verifica escrita antes de iniciar,
resolve anexos por streaming com limites e suporta comando aguardando imagem.
A prova `verify-live-media.py`, com o anexo real do Plow, confirmou UID 10000,
download e escrita corretos, imagem normalizada de 788.189 bytes, silêncio da
foto isolada e associação com comando dois segundos depois.

Foi recuperado apenas o último pedido originalmente rejeitado, preservando a
mensagem de origem e o UUID do job. Conferidos estado final de falha e ausência
de ticket, relatório e upload antes da recuperação. O Gemini apresentou falha
transitória (HTTP 503 observado na análise com schema), e depois concluiu com
HTTP 200. O relatório foi persistido antes de continuar ao Linear.

Resultado real: **OMN-6**, no time configurado, com screenshot na descrição.
Readback GraphQL HTTP 200 sem erros; um único retorno correspondente no Plow,
com status **delivered**. O arquivo temporário do job foi removido. Link:
https://linear.app/omni-qa-felipe/issue/OMN-6/excecao-zerodivisionerror-ao-executar-comando-python3-no-terminal

Essa recuperação usou eventos e imagem reais já recebidos; não representa um
novo envio pelo iPhone após o deploy. Uma chamada diagnóstica curta ao Gemini
fora do pipeline respondeu HTTP 200 e não foi incluída no ledger do agente;
a análise final de produção foi contabilizada normalmente.

Validação final da versão de 13/09: **84 testes aprovados**, lint de código,
testes e diagnóstico real aprovado. Container reconstruído e reiniciado;
`omni doctor` retornou `storage`, `linear`, `gemini` e `plow` em `ok`.
As proteções e limites de escopo estão em `docs/hardening/hardening.md`.

## Evolução de produto — UX, fallback e produção

- **96 testes aprovados**; lint limpo. Cobertura nova: ACK enquanto outro job está
  em inferência, deduplicação de avisos após reinício, três falhas Gemini → fallback,
  erros permanentes sem fallback, nomes de labels fora do catálogo rejeitados,
  preparação de label sem repetir mutação incerta e compatibilidade com relatórios
  antigos.
- Compressão local medida: PNG de **6.230.659 bytes → JPEG de 864.468 bytes**,
  1280×720, **249 ms**. Entrada sintética com muitos detalhes aleatórios, limite
  de visão inferior a 1 MB. A medição não demonstra OCR perfeito em qualquer imagem;
  o anexo Linear mantém a representação original normalizada.
- `docker-compose.prod.yml` validado pelo Docker Compose com variáveis de teste;
  também confirmou rejeição quando uma variável obrigatória está ausente. Não há
  build nessa definição. Isso não equivale a publicar imagem ou implantar em nuvem.
- O diagnóstico profundo encontrou HTTP503 real do Gemini; a demonstração normal
  posterior conseguiu recuperar e concluir visão/schema. O diagnóstico básico não
  promete capacidade de inferência futura: `--deep` distingue esse escopo.

### Demonstração normal real

Job `ee52f7bd-696c-484e-bc47-4c9419d2a1c3`, fixture sintética identificada como
`DEMO PRODUTO` enfileirada diretamente; não foi um novo envio físico pelo iPhone.
Gemini, Linear e Plow reais. **OMN-7** criado após retry, com anexo e time correto;
GraphQL HTTP200 sem erros, prioridade Linear permaneceu 0. Plow confirmou:

| Mensagem | Tempo desde o registro do job | Entrega |
| --- | ---: | --- |
| ACK | 1,371 s | delivered |
| Aviso único de retry | 25,375 s | delivered |
| Resumo e link | 49,577 s | delivered |

URL: https://linear.app/omni-qa-felipe/issue/OMN-7/erro-500-ao-salvar-tarefa-na-tela-create-task

O teste automatizado de despacho local atende menos de 500 ms; a medição real
acima inclui o serviço externo. Não foi demonstrada entrega física subsegundo.

### Demonstração de fallback

Falha do Gemini injetada deliberadamente em um workflow de validação isolado;
Linear, upload e Plow reais. **OMN-8** criado com título cru, relatório `pending`,
label **ai-pending** confirmada por GraphQL e screenshot presente. O time foi
preservado e a prioridade permaneceu 0. ACK, aviso único e mensagem final foram
confirmados como `delivered`; a mensagem final chegou em 6,651 s.

URL: https://linear.app/omni-qa-felipe/issue/OMN-8/demo-fallback-falha-ao-salvar-tarefa

Durante a preparação desse teste isolado, importar a configuração Hermes antes
de abandonar root alterou o modo do diretório legado. O teste parou antes de
criar issue. A inicialização oficial restaurou as permissões e o teste foi
corrigido para importar após a troca de UID. O diagnóstico agora também verifica
travessia dos diretórios ancestrais; `--deep` exercita escrita sob UID10000.

A fila de validação de fallback permanece separada em `fallback-validation`,
para preservar a deduplicação do teste. Ela não é lida pelo worker de produção.
A publicação da imagem e um deploy AWS/GCP/VPS aguardam um registro/namespace
informado pelo proprietário; nenhuma imagem pública ou implantação em nuvem foi
inventada como resultado.
