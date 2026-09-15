# Dados e privacidade

A execução local usa Docker e SQLite. Mensagens e imagens passam pelo Plow;
a representação da imagem e o comando são enviados ao Gemini; imagem e relato
são enviados ao Linear. Local não significa processamento inteiramente offline.

O agente atende a conversa autorizada e usa o destino configurado. Segredos ficam
fora da imagem e do Git. O modelo não recebe ferramentas de shell ou escolha de
credenciais. O fluxo guarda estados e IDs para recuperação; imagens temporárias
são excluídas após sucesso ou limpas após o prazo de falha configurado (24 horas).
Os provedores externos possuem suas próprias políticas de armazenamento.

A landing page não possui analytics, formulário ou upload de screenshots.
O provedor de hospedagem pode manter logs de acesso. Nunca envie segredos em
screenshots. Avaliações com dados reais exigem consentimento e sanitização.
Esta descrição técnica não é certificação de segurança ou conformidade legal.
