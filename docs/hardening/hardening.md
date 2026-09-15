# Security Hardening Review: Omni-Action Hub

## Evidence Basis

Nós partimos do incidente reproduzido em [VALIDATION.md](../../VALIDATION.md) e
inspecionamos os caminhos de entrada, download, persistência e execução. A
reprodução mostrou falha de disponibilidade por propriedade do cache, sem
evidência de ataque. Também identificamos oportunidades locais para limitar o
consumo de anexos e tornar as decisões de recuperação observáveis. Esta análise
não equivale a uma auditoria integral de dependências ou serviços externos.

## Constraints

Nós preservamos o plugin oficial para autenticação, WebSocket, cursor e envio;
a instalação continua em Docker e a criação de tickets continua restrita ao
time configurado. Não introduzimos ferramentas de shell no modelo, serviços
novos, compra de capacidade ou mudanças de credenciais. Os dados visuais ainda
são enviados a Gemini e Linear como previsto pelo produto.

## Opportunity Portfolio

Nenhuma proposta de reestruturação ampla foi necessária para corrigir este
incidente. Classificamos a análise como `local_remediation_preferred`: cache
privado, verificação sob o UID efetivo e um resolvedor restrito são mudanças
proporcionais ao mecanismo observado. Não há propostas ou diagramas de opções
arquiteturais fictícias nesta coleção.

## Recommendation Summary

Recomendo manter as correções locais já autorizadas e implementadas. Nós agora
limitamos anexos a 10 MB por download, dois downloads concorrentes e 60 segundos
por resolução; rejeitamos redirecionamentos e destinos fora da origem Plow.
O buffer de imagens tem teto de 100 MB e expira conteúdo após 24 horas. Diretórios
privados usam 0700, arquivos de download 0600, e caminhos de cache ou banco que
sejam links simbólicos são rejeitados. O SQLite usa `secure_delete`; isso não
é promessa de apagamento forense de volumes, WAL ou backups do host.

Nós mantemos autorização independente de OCR e do texto citado. A identidade do
remetente precisa existir no transporte autenticado. Conteúdo da imagem pode
alterar a descrição sugerida, mas não o destino, credenciais ou as ferramentas
disponíveis. O schema limita os campos extraídos; sugestões continuam sujeitas à
triagem. As exceções e logs não imprimem conteúdo ou credenciais.

A nova espera aumenta em até 60 segundos o tempo para responder a um comando
sem anexo; esse custo evita rejeitar anexos que ainda estão chegando. O download
por streaming reduz alocação sem limite, mas normalização por Pillow e inferência
ainda consomem recursos e dependem de código de terceiros. A migração SQLite é
aditiva; uma reversão exige preservar o banco e tratar jobs `waiting`, pois a
versão antiga não sabe encerrá-los.

## Next Decisions

Nós ainda precisamos observar novos envios pelo telefone após o deploy e
avaliar carga sustentada antes de ampliar a distribuição. Plow, Gemini e Linear
continuam sendo dependências externas; disponibilidade, limites e falhas desses
serviços não são eliminados pelos retries. O teste real já encontrou HTTP503 no
Gemini e confirmou recuperação posterior.

Separar inferência e credenciais em processos diferentes passa a valer a pena
se forem adicionadas ferramentas arbitrárias, múltiplos usuários por instalação
ou um modelo de plugins não confiáveis. Essa não é a arquitetura atual. Uma
revisão completa da imagem base e de suas dependências permanece fora da
verificação realizada; não afirmamos proteção absoluta de todo o sistema.
