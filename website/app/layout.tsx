import type { Metadata } from "next";
import { MotionProvider } from "@/components/motion-provider";
import "lenis/dist/lenis.css";
import "./globals.css";

export const metadata: Metadata = {
  title: "Omni — Menos relato. Mais resolvido.",
  description:
    "Da evidência no iMessage à tarefa no Linear. Um agente focado, com Gemini, recuperação de falhas e controle do destino.",
  openGraph: {
    title: "Omni-Action Hub",
    description: "De um print a uma ação.",
    locale: "pt_BR",
    type: "website",
  },
};
export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="pt-BR">
      <body>
        <a className="skip-link" href="#main">
          Pular para o conteúdo
        </a>
        <MotionProvider>{children}</MotionProvider>
      </body>
    </html>
  );
}
