"use client";
import { useRef, useState } from "react";
import {
  motion,
  useMotionValueEvent,
  useScroll,
  useReducedMotion,
} from "framer-motion";
import {
  ArrowUpRight,
  Check,
  ImageIcon,
  ScanLine,
  Layers3,
} from "lucide-react";
const steps = [
  {
    title: "Você vê. Você envia.",
    text: "Um print e “Registra esse bug”. Na conversa que você já usa, sem trocar de contexto.",
    icon: ImageIcon,
  },
  {
    title: "O contexto se encontra.",
    text: "Imagem e comando se juntam, mesmo chegando separados. A IA estrutura o que está visível.",
    icon: ScanLine,
  },
  {
    title: "A evidência vira ação.",
    text: "Um ticket com imagem e contexto no Linear. Se a IA estiver indisponível, a evidência segue com ai-pending.",
    icon: Layers3,
  },
];
export function Pipeline() {
  const ref = useRef<HTMLElement>(null);
  const [active, setActive] = useState(0);
  const reduced = useReducedMotion();
  const { scrollYProgress } = useScroll({
    target: ref,
    offset: ["start center", "end center"],
  });
  useMotionValueEvent(scrollYProgress, "change", (value) =>
    setActive(Math.min(2, Math.floor(value * 3))),
  );
  return (
    <section id="fluxo" className="pipeline section-wrap" ref={ref}>
      <div className="pipeline-copy">
        <span className="eyebrow">02 / DO SINAL À AÇÃO</span>
        <h2>
          Três momentos.
          <br />
          <span className="muted">Um fluxo.</span>
        </h2>
        <div className="steps">
          {steps.map((step, i) => (
            <div
              key={step.title}
              className={`step ${active === i ? "active" : ""}`}
            >
              <span className="step-number">0{i + 1}</span>
              <div>
                <h3>{step.title}</h3>
                <p>{step.text}</p>
              </div>
            </div>
          ))}
        </div>
      </div>
      <div className="pipeline-visual">
        <div className="terminal-top">
          <span className="status-dot" /> OMNI / FLUXO ILUSTRATIVO{" "}
          <span>0{active + 1}—03</span>
        </div>
        <div className="stages">
          {steps.map((step, i) => (
            <motion.div
              key={step.title}
              className={`stage stage-${i}`}
              animate={{
                opacity: active === i ? 1 : 0.38,
                scale: reduced ? 1 : active === i ? 1 : 0.97,
              }}
              transition={{ duration: 0.4 }}
            >
              <step.icon size={20} />
              <span>
                {
                  [
                    "Evidência recebida",
                    "Contexto estruturado",
                    "Tarefa criada",
                  ][i]
                }
              </span>
              {active > i ? (
                <Check size={16} />
              ) : (
                <span className="stage-index">0{i + 1}</span>
              )}
            </motion.div>
          ))}
        </div>
        <div className="ticket-preview">
          <span className="eyebrow">EXEMPLO DE RESULTADO</span>
          <div className="ticket-id">
            <span className="linear-mark">◩</span> OMN-DEMO{" "}
            <ArrowUpRight size={16} />
          </div>
          <h3>Falha ao salvar tarefa</h3>
          <p>
            A tela exibe um erro ao confirmar a criação. Evidência anexada para
            investigação.
          </p>
          <div className="tags">
            <span>bug</span>
            <span>triagem sugerida</span>
          </div>
          <div className="attachment">
            <ImageIcon size={16} /> screenshot.png <Check size={14} />
          </div>
        </div>
        <div className="pipeline-foot">
          Destino configurado por você. <span>Execução rastreável.</span>
        </div>
      </div>
    </section>
  );
}
