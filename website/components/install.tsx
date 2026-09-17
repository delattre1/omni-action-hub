"use client";
import { useState } from "react";
import { Check, Copy, ArrowUpRight } from "lucide-react";
const command =
  "docker compose --env-file .env -f docker-compose.prod.yml up -d --wait";
export function Install() {
  const [status, setStatus] = useState("");
  async function copy() {
    try {
      await navigator.clipboard.writeText(command);
      setStatus("Comando copiado.");
    } catch {
      setStatus("Selecione e copie o comando abaixo.");
    }
  }
  return (
    <section id="comece" className="install section-wrap">
      <div>
        <span className="eyebrow">04 / ASSUMA O CONTROLE</span>
        <h2>
          Sua evidência.
          <br />
          Seu próximo passo.
        </h2>
        <p>Uma instalação. Suas credenciais. O seu time no Linear.</p>
        <a className="button light" href="/installation.md" download>
          Guia de instalação <ArrowUpRight size={18} />
        </a>
      </div>
      <div className="install-panel">
        <div className="terminal-top">
          DEPLOY / DOCKER COMPOSE <span>AMD64</span>
        </div>
        <ol>
          <li>Configure suas contas Plow, Gemini e Linear.</li>
          <li>Preencha o .env e informe a imagem publicada por digest.</li>
          <li>Inicie o agente e rode o diagnóstico.</li>
        </ol>
        <div className="command">
          <code>{command}</code>
          <button aria-label="Copiar comando Docker Compose" onClick={copy}>
            {status === "Comando copiado." ? (
              <Check size={18} />
            ) : (
              <Copy size={18} />
            )}
          </button>
        </div>
        <p role="status" className="copy-status">
          {status ||
            "Pré-requisitos e publicação da imagem são etapas separadas."}
        </p>
        <div className="release-note">
          <span className="status-dot amber" /> Imagem pública no GHCR
        </div>
      </div>
    </section>
  );
}
