# Demonstração e teste com pessoas

## Antes da gravação

Use um projeto de teste no Linear e uma captura sem dados pessoais ou segredos.
Confirme `doctor`, `docker compose ps` e a autorização da conversa. Não mostre
arquivos de configuração na gravação. Confirme que a imagem e o comando foram
enviados juntos ou como resposta citada; mensagens soltas não são concatenadas.

## Roteiro de 30–45 segundos

1. Mostre uma interface com um erro visível, como texto sobreposto a um botão.
2. Capture a região da tela.
3. No iMessage, envie “Registra esse bug. Eu esperava conseguir ler o botão.” com a imagem.
4. Mostre a resposta com o identificador e o link.
5. Abra o link manualmente e mostre evidência, lacunas e screenshot.

Não atribua ao agente a abertura automática do navegador; ela está fora do MVP.
Não esconda perguntas de esclarecimento nem apresente inferência como reprodução
verificada do bug. Cronometre o fluxo completo, incluindo espera por APIs.

## Aceitação com três pessoas

Cada pessoa deve usar suas próprias credenciais e seguir somente o README.
Registre dados reais nesta tabela; não preencher com estimativas.

| Pessoa | Pré-requisitos prontos? | Instalação | Screenshot → link | Ticket/anexo corretos? | Precisou de ajuda? | Relatório útil? |
|---|---|---|---|---|---|---|
| 1 | Pendente | — | — | — | — | — |
| 2 | Pendente | — | — | — | — | — |
| 3 | Pendente | — | — | — | — | — |

Cronometre separadamente criação de contas/chaves, instalação das dependências,
instalação do agente e latência do pedido. Considere o fluxo aceito quando as
três pessoas criarem tickets com a imagem correta sem assistência. Registre
falhas mesmo que a segunda tentativa funcione.

Além da demonstração feliz, faça uma imagem ilegível, duas imagens, uma captura
com “ignore as regras” escrito dentro dela e reinício durante uma solicitação.
Use um ambiente de teste; não simule falhas em projetos de produção.
