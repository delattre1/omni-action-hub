"use client";
import { useEffect } from "react";
import Lenis from "lenis";
import { MotionConfig } from "framer-motion";

export function MotionProvider({ children }: { children: React.ReactNode }) {
  useEffect(() => {
    const preference = window.matchMedia("(prefers-reduced-motion: reduce)");
    let lenis: Lenis | undefined;
    const sync = () => {
      lenis?.destroy();
      lenis = preference.matches
        ? undefined
        : new Lenis({ autoRaf: true, anchors: true, duration: 0.9 });
    };
    sync();
    preference.addEventListener("change", sync);
    return () => {
      lenis?.destroy();
      preference.removeEventListener("change", sync);
    };
  }, []);
  return <MotionConfig reducedMotion="user">{children}</MotionConfig>;
}
