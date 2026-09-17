# Omni / landing

Next.js App Router + Tailwind CSS + Framer Motion + Lenis + lucide-react.
Dark mode, tipografia grande, ilustração própria em CSS, apresentação do pipeline
por scroll, navegação por âncoras e cópia do comando. Não tem formulários, analytics,
chaves, chat funcional, chamadas ao backend ou promessas de tempo de ticket.

## Executar o projeto entregue

Node.js 22+, npm. Na raiz de `omni-action-hub`:

```sh
cd website
npm ci
npm run dev
# http://localhost:3000
npm run typecheck
npm run build
```

O build exporta `out/` para hospedagem estática. Para conferir o build:

```sh
python3 -m http.server 3000 --directory out --bind 127.0.0.1
```

`next start` não se aplica ao modo `output: export`; use um servidor estático.
A fonte usa a pilha local sans-serif, evitando download externo para renderizar
ou compilar. Ícones são vetoriais; não há dependências de imagens remotas.

## Comandos equivalentes para um projeto novo

Estes são para outra pasta, **não sobre o projeto entregue**:

```sh
npx create-next-app@16.3.5 omni-website --typescript --tailwind --app --eslint --use-npm
cd omni-website
npm install --save-exact framer-motion@13.3.0 lenis@1.3.26 lucide-react@1.46.0
```

Use os componentes desta pasta: `app/page.tsx`, `app/layout.tsx`,
`components/motion-provider.tsx`, `reveal.tsx`, `pipeline.tsx` e `install.tsx`.
O provider cria/destrói Lenis no cliente e desativa o smooth scroll quando o
sistema solicita movimento reduzido. Motion respeita a mesma preferência.
Sem JS o conteúdo e as âncoras continuam disponíveis; copiar requer JS.

## Conteúdo e revisão

Métricas são um retrato da rodada de 14/09/2026, com contexto explícito:
100 casos; ACK 1,37 s em um teste real; 86% de redução de bytes em benchmark
sintético (aproximadamente 7,2×, **não 86×**). O histórico não é atualizado
automaticamente pela suíte. Não há promessa de ticket em 2 segundos.

`public/evaluation.md`, `installation.md` e `privacy.md` são downloads públicos
sanitizados, sem paths locais, credenciais ou screenshots de pessoas.
Atualize-os quando a distribuição real mudar. O botão de instalação entrega o
guia e informa que a imagem pública está disponível no GHCR.

A referência [United Carriers](https://unitedcarriers.com) orientou a hierarquia
editorial e o ritmo das seções; marca, composição e arte do Omni são próprias.
Fontes técnicas: [Next.js](https://nextjs.org/docs/app/getting-started/installation),
[Motion](https://motion.dev/docs/react-installation) e
[Lenis](https://github.com/darkroomengineering/lenis).
