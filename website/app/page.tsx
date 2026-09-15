import {
  ArrowDown,
  ArrowUpRight,
  AudioLines,
  Check,
  Command,
  Fingerprint,
  Layers3,
  ShieldCheck,
} from "lucide-react";
import { Reveal } from "@/components/reveal";
import { Pipeline } from "@/components/pipeline";
import { Install } from "@/components/install";

export default function Home() {
  return (
    <>
      <header className="nav">
        <a href="#" className="brand" aria-label="Omni, início">
          <span className="brand-icon">
            <AudioLines size={22} />
          </span>
          omni<span className="brand-suffix">/ action hub</span>
        </a>
        <nav aria-label="Navegação principal">
          <a href="#fluxo">O fluxo</a>
          <a href="#evidencias">Engenharia</a>
          <a href="#comece" className="nav-cta">
            Começar <ArrowUpRight size={14} />
          </a>
        </nav>
      </header>
      <main id="main">
        <section className="hero">
          <div className="hero-grid" aria-hidden="true" />
          <div className="hero-glow" aria-hidden="true" />
          <Reveal>
            <div className="hero-kicker">
              <span className="status-dot" /> CONTEXTO EM MOVIMENTO{" "}
              <span className="kicker-version">V0.1 / MACOS + DOCKER</span>
            </div>
            <h1>
              De um print.
              <br />
              <span>A uma ação.</span>
            </h1>
            <p className="hero-description">
              Você encontrou o problema.
              <br className="mobile-break" /> Deixe o relato com o Omni.
              <br />
              Do iMessage ao Linear, com a evidência no lugar certo.
            </p>
            <div className="hero-actions">
              <a className="button light" href="#fluxo">
                Veja o fluxo <ArrowUpRight size={18} />
              </a>
              <a className="text-link" href="#evidencias">
                Explore a engenharia <ArrowDown size={15} />
              </a>
            </div>
          </Reveal>
          <Reveal className="hero-art" delay={0.15}>
            <div className="orbit orbit-one" />
            <div className="orbit orbit-two" />
            <div className="flow-line" />
            <div className="floating-label label-in">01 / CAPTURE</div>
            <div className="floating-label label-out">02 / RESOLVE</div>
            <div className="capture-card">
              <div className="window-bar">
                <i />
                <i />
                <i />
                <span>evidência.png</span>
              </div>
              <div className="mock-app">
                <div className="mock-sidebar">
                  <span />
                  <span />
                  <span />
                </div>
                <div className="mock-content">
                  <div className="mock-title" />
                  <div className="mock-row" />
                  <div className="mock-row short" />
                  <div className="mock-error">
                    <span>!</span> Não foi possível salvar
                  </div>
                </div>
                <div className="crop-corner corner-a" />
                <div className="crop-corner corner-b" />
              </div>
              <div className="message-pill">
                Registra esse bug <ArrowUpRight size={12} />
              </div>
            </div>
            <div className="hub-core">
              <AudioLines size={48} strokeWidth={1.4} />
              <span>OMNI</span>
            </div>
            <div className="result-card">
              <div className="result-top">
                <span className="success-icon">
                  <Check size={14} />
                </span>
                <span>Tarefa criada</span>
                <ArrowUpRight size={14} />
              </div>
              <span className="result-id">EXEMPLO / LINEAR</span>
              <h3>Falha ao salvar tarefa</h3>
              <div className="result-footer">
                <span>Evidência anexada</span>
                <span>◩</span>
              </div>
            </div>
          </Reveal>
          <div className="hero-bottom">
            <span>CAPTURE. CONTEXTUALIZE. CONTINUE.</span>
            <span>
              ROLE PARA EXPLORAR <ArrowDown size={12} />
            </span>
          </div>
        </section>
        <div className="integration-bar">
          <span>UM FLUXO, CONECTADO.</span>
          <div>
            iMessage <span>↗</span> Plow <span>↗</span> Gemini <span>↗</span>{" "}
            Linear
          </div>
          <span>SUAS CONTAS. SEU CONTROLE.</span>
        </div>
        <section id="evidencias" className="evidence section-wrap">
          <Reveal>
            <div className="section-heading">
              <div>
                <span className="eyebrow">01 / EVIDÊNCIAS, NÃO PROMESSAS</span>
                <h2>
                  Simples por fora.
                  <br />
                  <span className="muted">Criterioso por dentro.</span>
                </h2>
              </div>
              <p>
                Cada número tem contexto.
                <br />
                Cada ação deixa um rastro.
              </p>
            </div>
          </Reveal>
          <div className="bento">
            <Reveal className="metric metric-tests">
              <div className="metric-label">
                <ShieldCheck size={20} />
                <span>CONFIABILIDADE</span>
              </div>
              <div className="metric-number">
                100<span>/100</span>
              </div>
              <h3>Testes aprovados.</h3>
              <p>
                Suíte local de 14/09/2026. Testes unitários e de integração com
                falhas simuladas.
              </p>
              <div className="test-grid" aria-hidden="true">
                {Array.from({ length: 100 }, (_, i) => (
                  <i key={i} />
                ))}
              </div>
            </Reveal>
            <Reveal className="metric" delay={0.08}>
              <div className="metric-label">
                <Command size={20} />
                <span>FEEDBACK</span>
              </div>
              <div className="metric-number">
                1,37<span>s</span>
              </div>
              <h3>Você sabe que chegou.</h3>
              <p>
                ACK entregue em uma execução real. Tempo do ticket e latência da
                rede variam.
              </p>
              <div className="ack-bubble">
                <span className="status-dot" /> Evidência recebida.
              </div>
            </Reveal>
            <Reveal className="metric" delay={0.16}>
              <div className="metric-label">
                <Layers3 size={20} />
                <span>VISÃO OTIMIZADA</span>
              </div>
              <div className="metric-number">
                86<span>%</span>
              </div>
              <h3>Menos bytes, neste teste.</h3>
              <p>
                6,23 MB → 865 KB em 236 ms. Benchmark sintético; não é uma
                medição de precisão do OCR.
              </p>
              <div className="compression-bars">
                <span />
                <span />
              </div>
            </Reveal>
          </div>
          <a className="evidence-link" href="/evaluation.md">
            Leia o relatório e os limites da avaliação{" "}
            <ArrowUpRight size={14} />
          </a>
        </section>
        <Pipeline />
        <section className="principles section-wrap">
          <Reveal>
            <span className="eyebrow">03 / AUTONOMIA COM LIMITES</span>
            <h2>
              Ele cuida do relato.
              <br />
              <span className="muted">Você mantém o controle.</span>
            </h2>
          </Reveal>
          <div className="principle-grid">
            <Reveal>
              <Fingerprint size={25} />
              <h3>Um destino definido.</h3>
              <p>
                Conversa autorizada, credenciais próprias e time configurado. O
                texto de um print não pode mudar as regras.
              </p>
            </Reveal>
            <Reveal delay={0.1}>
              <ShieldCheck size={25} />
              <h3>A dúvida não duplica.</h3>
              <p>
                Se a criação perder a resposta, o Omni verifica o ticket antes
                de tentar novamente. Estado persistido em SQLite.
              </p>
            </Reveal>
            <Reveal delay={0.2}>
              <Layers3 size={25} />
              <h3>O trabalho continua.</h3>
              <p>
                Na indisponibilidade temporária da IA, imagem e título seguem
                para triagem, identificados com ai-pending.
              </p>
            </Reveal>
          </div>
        </section>
        <Install />
      </main>
      <footer className="footer">
        <a className="brand" href="#">
          <AudioLines size={24} />
          omni
        </a>
        <span>MENOS RELATO. MAIS RESOLVIDO.</span>
        <a href="/privacy.md">
          Dados e privacidade <ArrowUpRight size={14} />
        </a>
        <span>© 2026 OMNI-ACTION HUB</span>
      </footer>
    </>
  );
}
