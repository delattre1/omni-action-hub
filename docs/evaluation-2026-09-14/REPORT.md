# Avaliação do Omni-Action Hub — 14/09/2026

## Resultado

**Aprovado nos testes técnicos executados, com pendências para distribuição e
validação com pessoas. O roteiro recebido não deve ser apresentado como prova
integral de prontidão enterprise nem como regra oficial do hackathon.**

Executamos a suíte local, um teste adicional de concorrência e um benchmark de
compressão. Consultamos o container e executamos `omni doctor --deep` de verdade.
Não alteramos credenciais nem interrompemos a rede da instalação. Os testes de
falha e de carga usaram dados e clientes isolados, sem criar novos tickets.

As demonstrações OMN-7 e OMN-8 pertencem à rodada anterior, documentada em
[VALIDATION.md](../../VALIDATION.md); não são medições novas de hoje.

## Matriz de avaliação

| Critério recebido | Resultado | Evidência / limite |
| --- | --- | --- |
| Instalar sem build | Parcial | Compose de produção não tem `build`; publicação e download da imagem por terceiros não foram comprovados |
| Imagem imutável do GHCR | Pendente | Container usa `omni-action-hub:0.1.0` local. `OMNI_IMAGE` é obrigatório, mas a sintaxe Compose não obriga uso de digest |
| Instalação em cinco minutos | Não medido | Nenhuma instalação independente cronometrada; a regra do evento permanece não confirmada |
| Foto + descrição livre cria ticket | Divergente por projeto | É necessário comando explícito, como `/bug O botão de checkout sumiu da tela principal` |
| ACK em aproximadamente 1,37 s | Evidência histórica | OMN-7 teve esse tempo de entrega; não é SLA. Teste atual verifica despacho independente de inferência |
| Ticket em 2–5 s | Não comprovado | OMN-7 levou 49,577 s com retry. A latência externa varia |
| Compressão abaixo de 1 MB | Aprovado no benchmark | 6.226.298 → 864.877 bytes; 1280×720; 235,62 ms nesta máquina |
| Legibilidade preservada em toda imagem | Não comprovado | Benchmark usa ruído sintético, não mede OCR. A evidência do Linear mantém a resolução normalizada original |
| Métrica `optimize_for_vision` nos logs | Ausente | Função não emite essa linha; a medição é feita pelo script de benchmark |
| Fallback após Gemini indisponível | Aprovado em testes | Três falhas transitórias; imagem, título cru e `ai-pending`; integração real anterior OMN-8 |
| Fallback após chave inválida | Critério incorreto | Autenticação falha sem retry automático nem ticket de fallback; exige correção |
| Cortar toda a internet e ainda criar ticket | Critério inviável | Plow e Linear também dependem da rede; a falha deve ser isolada ao Gemini |
| Concorrência limitada | Aprovado no escopo local | 24 jobs por configuração, com 1/2/4 workers; 72 jobs simulados concluídos |
| Três pessoas na mesma instalação | Fora do modelo atual | Apenas conversa configurada e proprietário autenticado; use três instalações independentes para avaliação humana |
| Limites 2 GB / 256 processos ativos | Não conforme no container atual | `HostConfig.Memory=0`, `PidsLimit=null`; limites definidos apenas no Compose de produção |
| Healthcheck a cada 30 s | Aprovado | Docker informa intervalo de 30.000.000.000 ns; estado observado `healthy` |
| Diagnóstico profundo | Aprovado nesta execução | Gemini, Linear, Plow, armazenamento e label `ai-pending`: `ok` |
| Disponibilidade contínua do Plow | Não comprovada | Logs recentes mostram desconexões seguidas de reconexões |

## Concorrência medida

Os testes usaram Workflow, workers, notificações e SQLite reais em diretórios
temporários. Gemini, Linear e envio de mensagens foram simulados. A inferência
simulada aguarda 30 ms; os tempos abaixo não são capacidade de produção das APIs.

| Workers configurados | Jobs | Pico de inferências | Tickets simulados únicos | ACKs | Tempo |
| ---: | ---: | ---: | ---: | ---: | ---: |
| 1 | 24 | 1 | 24 | 24 | 2,362 s |
| 2 | 24 | 2 | 24 | 24 | 1,160 s |
| 4 | 24 | 4 | 24 | 24 | 0,559 s |

Os testes também reintroduzem os mesmos identificadores de origem e verificam
que cada job termina uma única vez, a fila esvazia e as cópias temporárias somem.
Isso é uma carga curta e limitada, não um ensaio prolongado com três pessoas,
quotas reais, saturação de memória ou escala multi-tenant.

## Respostas ao questionário técnico

1. **Sim, com correção de terminologia.** A entrada usa WebSocket, não webhook.
   Resolução de mídia e inferência são separadas; workers e tarefa de ACK são
   assíncronos. Trabalho de Pillow é transferido para threads.
2. **Sim para JSON validado e restrição de ações.** Pydantic valida o relatório;
   não existem ferramentas arbitrárias disponíveis ao modelo. O prompt orienta
   contra invenções, mas isso não prova ausência absoluta de alucinações.
3. **Sim.** Sugestões são filtradas pelo catálogo real. `ai-pending` é uma regra
   operacional fixa, não uma label inventada pela IA. As demais sugestões não
   são aplicadas automaticamente.
4. **Sim para os caminhos de recuperação testados, sem garantia absoluta.** UUID
   persistido e reconciliação evitam repetir cegamente uma criação incerta.
   Dúvida persistente suspende a recriação. Perda do volume, retenção de 24 horas
   e falhas de armazenamento não são resolvidas apenas por SQLite. A resposta
   final ainda pode duplicar se o processo cair após enviar e antes do commit.
5. **Sim: a suíte agora contém 100 casos executados**, incluindo quatro novos
   casos desta avaliação. A contagem inclui parametrizações e testes unitários;
   não significa 100 testes completos de ponta a ponta com APIs reais.

## Ações antes da banca

1. Informar o registro/namespace, publicar a imagem, registrar seu digest e
   executar uma instalação limpa a partir dela. Medir preparação de contas
   separadamente da instalação da aplicação.
2. Aplicar os limites do Compose de produção na instalação usada para a demo e
   confirmar os valores com `docker inspect`.
3. Usar o [roteiro corrigido](RUNBOOK.md), com comando explícito e critérios sem
   promessas de latência ou disponibilidade não medidas.
4. Medir novos envios por iPhone e a instalação de três pessoas, cada uma com
   sua conversa e credenciais. Não tratar os testes simulados como substitutos.
5. Se a banca precisar acompanhar compressão nos logs, implementar métricas
   seguras de bytes/dimensões/duração; atualmente o benchmark é externo ao log.

## Artefatos e reprodução

- [JUnit da suíte](tests.xml)
- [Benchmark de compressão](compression.json)
- [Resumo estruturado](results.json)
- `tests/test_assessment.py`: concorrência e descrição livre sem autorização.
- `scripts/benchmark-vision.py`: benchmark offline reproduzível, sem screenshots reais.

Nenhuma alteração funcional foi aplicada à aplicação em execução nesta avaliação.
Foram adicionados testes, benchmark e documentação; as divergências de produção
foram mantidas visíveis no resultado.
