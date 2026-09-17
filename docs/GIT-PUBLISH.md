# Publicação no GitHub

O repositório já existe em https://github.com/fecabrall/omni-action-hub, com origin e
main configurados. **Não rode git init nem remote add novamente nesta pasta.**
As alterações desta entrega são enviadas ao repositório existente.

Para próximas alterações:

```sh
git status --short
# Revise os paths; nunca use git add -f em segredos.
git add README.md .env.example .env.prod.example .gitignore LICENSE LICENSES NOTICE docs scripts tests Dockerfile .dockerignore pyproject.toml
git diff --cached --check
git diff --cached --stat
git commit -m "Improve launch onboarding and submission kit"
git push origin main
```

Para uma cópia nova sem histórico, somente se precisar criar OUTRO repositório:

```sh
git init -b main
git add .gitignore .dockerignore .env.example .env.prod.example .github LICENSE LICENSES NOTICE README.md DESIGN.md Dockerfile compose.yml docker-compose.prod.yml pyproject.toml omni.env.example src runtime vendor scripts tests docs evals website
git diff --cached --check
git diff --cached --stat
git commit -m "Initial Omni-Action Hub release"
# Use a URL de um repositório novo e vazio. Não reenvie histórico sobre o existente.
git remote add origin https://github.com/SEU_USUARIO/SEU_REPOSITORIO.git
git push -u origin main
```

Visibilidade não muda com git push. Antes de tornar público, revise todo o histórico,
vídeos e artefatos, além do commit atual. No GitHub: Settings → General → Danger Zone
→ Change repository visibility. O pacote GHCR tem visibilidade própria; confira
Package settings. Um repositório público com imagem privada continua bloqueando
instalações anônimas. Repositório e pacote foram tornados públicos nesta entrega após autorização explícita.

.gitignore evita inclusão acidental; não remove segredos já rastreados e não
impede `git add -f`. Se houver vazamento, revogue a chave e trate o histórico.
