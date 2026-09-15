# Omni — evidências de 14/09/2026

100 testes locais passaram em 9,405 segundos. A suíte inclui parametrizações,
clientes simulados e casos de integração locais; não são 100 testes físicos.

Concorrência: 24 jobs com 1, 2 e 4 workers, total de 72 jobs simulados concluídos
sem tickets duplicados. Não mede capacidade das APIs ou uso multi-tenant.

ACK: 1,371 segundo em uma demonstração anterior com APIs reais. O ticket dessa
execução levou 49,577 segundos, incluindo retry. Não existe SLA de 2 segundos.

Compressão: imagem sintética de 6.226.298 bytes para 864.877 bytes em 235,62 ms.
Redução de 86,1%, razão aproximada de 7,2×. Não é teste de fidelidade do OCR,
e bytes reduzidos não equivalem diretamente a tokens reduzidos.

Diagnóstico profundo: armazenamento, Gemini, Linear, Plow e label de fallback ok
na execução observada. Logs apresentaram desconexões/reconexões do Plow; um healthcheck
pontual não comprova disponibilidade contínua.

Pendências dessa rodada: publicação imutável, instalação limpa cronometrada,
limites de recursos no container local e três instalações humanas independentes.
Avaliação de precisão da IA depende de dataset real anotado; não há F1 publicado.
