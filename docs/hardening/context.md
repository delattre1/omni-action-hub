# Contexto da revisão de segurança

Escopo: implementação local Omni, bordas de download, autorização de entrada,
SQLite, retries e confirmação. Fontes: incidente real documentado em
`VALIDATION.md`, código `src/omni`, `compose.yml` e permissões dos dois arquivos
locais de credenciais (0600, conteúdo não reproduzido). Não é um scan de toda a
base Hermes, do macOS ou dos serviços externos. Não há revisão Git identificada;
`sourceDrift` fica unknown. Hashes da coleção estão em `hardening.json`.

Observado: HTTP200 no anexo, cache legado root:root0700 inacessível ao UID10000,
mesmo remetente nos dois eventos, arquivo ausente no SQLite. O código anterior
usava o cache oficial e transformava a falha em mensagem genérica de ajuda.
Observado após correção: download e buffer reais sob UID10000, recuperação OMN-6
e retorno entregue pelo Plow. A inferência de que permissões causaram a falha
é apoiada pela reprodução do resolvedor oficial sob o mesmo usuário.
