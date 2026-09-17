# Kit de submissão — Omni-Action Hub

## Texto pronto para colar

**Nome:** Omni-Action Hub

**Tagline:** Encontrou o bug? Mande o print. Receba o ticket.

**Descrição:**
Transforme evidências no iMessage em tickets estruturados no Linear. Envie um
screenshot com “Registra esse bug”: o Omni reúne imagem e comando, usa a visão
do Gemini para descrever o que aparece na tela e devolve o link da issue com a
imagem anexada. Menos troca de abas, menos copiar e colar, mais contexto para quem
vai investigar.

Você recebe confirmação durante o processamento. O destino é o time configurado
por você, e sugestões de severidade continuam sujeitas à triagem. Quando a IA fica
temporariamente indisponível, a evidência pode seguir com a marca `ai-pending`.
Cada instalação usa suas próprias credenciais de Plow, Gemini e Linear.

**Experimente:**
Escolha um bug real com evidência visual útil — um formulário com erro, uma tela
densa ou uma falha de dashboard. Envie uma imagem legível e o comportamento que
você esperava. Confira o ticket e conte se o relato ajudou a investigar. Recorte
a área relevante e remova dados sensíveis; complexidade deve servir ao diagnóstico,
não ao gasto artificial de tokens.

**Repositório:** https://github.com/fecabrall/omni-action-hub

**Instalação:** siga o README. macOS/Docker, linha Plow e contas Gemini/Linear
necessários. A base amd64 usa emulação no Apple Silicon. Gemini e demais serviços
externos podem ter custos/quotas. Não há prazo de instalação ou latência garantido.

**Licença:** MIT para código próprio; dependências preservam suas licenças.

## Antes de enviar (não colar como marketing)

- Repositório e pacote tornados públicos com autorização do proprietário; valide instalação em uma máquina independente.
- Preencha o campo de vídeo somente quando existir uma gravação real revisada.
- Registre o agente pelo cliente oficial, obtenha/confirme `AGENT_ID` e coloque-o
  na configuração distribuída. Sem ele, a telemetria da competição está pendente.
- Confira que chamadas Gemini reais aparecem no Agent Index sem duplicação;
  os testes locais de contabilidade não comprovam recebimento no servidor.
- Solicite “Get my agent verified”. Cadastro não significa verificação aprovada.
- Deploy de um clique no Index é coordenado com a equipe Plow; não é obtido apenas
  publicando este Compose. A página indica contato com danedelattre no Discord.

## Regras verificadas em 16/09/2026

A página oficial exige MIT, verificação e reporting pelo cliente AI Worth Using
para ranquear. Exibe usuários e sucesso de instalação. A fórmula “instalações ×
tokens”, prazo final/hora, teto e desclassificação por tempo não foram confirmados
nessa página. Não os apresente como requisitos oficiais comprovados.

Fonte: https://aiworthusing.com/agent-index

“Hermes” aqui é a base/runtime do agente. O catálogo de submissão é o Agent Index;
Docker executa o agente e GHCR distribui sua imagem. Vercel, Heroku e a landing page
não substituem registro, reporting e verificação no Index.
