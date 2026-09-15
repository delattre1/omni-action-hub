# Omni-Action Hub — design da conversa

A interface do produto é o iMessage. O Omni respeita seus balões, tipografia,
acessibilidade e comportamento de links nativos. O diferencial está em dar
clareza e continuidade ao relato, sem criar uma tela extra para uma tarefa curta.
As referências enviadas (Apple Design Skill, Awesome DESIGN.md e UI UX Pro Max)
orientam a organização e a revisão; não são dependências executadas ou instaladas.

## Princípios

- **Controle:** somente o comando autenticado autoriza a criação no destino configurado.
- **Clareza:** diferenciar prioridade sugerida de prioridade aplicada; desconhecido é um resultado válido.
- **Continuidade:** a evidência permanece utilizável quando a IA cai, com marcação explícita `ai-pending`.
- **Discrição:** foto isolada é silenciosa; no máximo um ACK e um aviso de retry por pedido.
- **Acessibilidade:** cada emoji acompanha texto completo. Nenhum significado depende só de cor, símbolo ou animação.

## Sequência da experiência

| Momento | Mensagem / comportamento |
| --- | --- |
| Foto ainda sem comando | Nenhuma resposta; buffer de 60 segundos |
| Comando ainda sem foto | Aguarda por até 60 segundos |
| Evidência e comando associados | `⏳ Evidência recebida! Analisando a tela e estruturando a tarefa...` |
| Primeira retentativa da IA | `🔄 A IA está pensando mais um pouco... Tentando novamente.` |
| Sucesso | `✅ OMN-7 criado: Falha ao salvar` + prioridade **sugerida** + URL |
| IA indisponível | Confirma criação, informa ausência de análise, mostra `ai-pending` e URL |
| Resultado incerto no Linear | Explica a dúvida e a suspensão da recriação |

O ACK é disparado por uma tarefa independente da inferência. A meta de despacho
local é inferior a 500 ms após a associação; a entrega física depende de Plow,
rede e iMessage. Não exibimos porcentagens de progresso inventadas. O aviso de
retry descreve uma operação real, sem repetir balões a cada tentativa.

## Conteúdo e triagem

A confirmação usa título curto e legível, seguido de uma linha para prioridade
e uma para o link. Evitamos detalhes internos, logs, IDs de credenciais e jargão
na conversa. Labels sugeridas usam nomes exatos do catálogo, mas continuam sendo
sugestões. Apenas a label operacional `ai-pending` é aplicada automaticamente no
fallback, com uma regra fixa fora do modelo.

No fallback, não inventamos causa, plataforma, componente ou severidade. O texto
original e o screenshot constituem o relato. A evidência do Linear mantém sua
resolução; apenas a representação enviada à visão é reduzida.

## Referências

- [Apple HIG — Generative AI](https://developer.apple.com/design/human-interface-guidelines/generative-ai)
- [Apple HIG — Feedback](https://developer.apple.com/design/human-interface-guidelines/feedback)
- [Apple HIG — Writing](https://developer.apple.com/design/human-interface-guidelines/writing)

Estas referências ajudam a revisar a interação; não representam certificação
Apple nem exigem instalar pacotes externos de design.


## Identidade da landing

A landing é uma superfície de apresentação independente, em `website/`.
Fundo quase preto (#090a0b), texto marfim (#f2f1ec), verde discreto (#d5edaf),
grid de baixa intensidade e ilustração vetorial/CSS própria. A tipografia usa
sans-serif local, tamanhos fluidos e espaçamento editorial. As métricas trazem
data, denominador e limites; não são badges de certificação.

Animações curtas de revelação e acompanhamento de scroll, sem esconder conteúdo
quando JavaScript está desativado. Respeitar `prefers-reduced-motion`, foco visível,
link para pular navegação, alvos confortáveis e layout sem scroll horizontal.
As miniaturas são exemplos, não screenshots reais nem integrações ao vivo.
