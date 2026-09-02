import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import App from "./App";
import "./index.css";

const rootEl = document.getElementById("root");
if (!rootEl) {
  throw new Error("Root element #root not found");
}

// CEO directive "TradeTown — Memecoin Sniper + Professional Trading
// Terminal, UI Correction / Visualization Rebuild" — the previous
// implementation wired the Sniper in as just another Command Center
// tab, which the directive explicitly calls out as wrong. This app has
// no client-side router at all (confirmed by this pass's own forensic
// recon — no react-router-dom or equivalent dependency anywhere), so
// the minimal, lowest-risk way to give the Sniper its own dedicated
// surface — without touching the existing Phaser canvas / gameStore /
// EventBus tree at all — is a plain pathname branch here, mounting a
// completely independent React root. Production nginx already falls
// back any unknown path to index.html (`frontend/deploy/nginx.conf`'s
// `try_files $uri $uri/ /index.html`), and Vite's dev server does the
// same by default, so `/sniper` resolves correctly in both.
const isSniperSurface = window.location.pathname.startsWith("/sniper");

if (isSniperSurface) {
  // CEO directive "UI / Governance / Travel Mode Hardening" — index.css's
  // global `html, body, #root { height: 100%; overflow: hidden; }` is
  // intentional for the main app (a fixed-viewport Phaser canvas with its
  // own internal scroll containers never wants a document-level
  // scrollbar), but the Sniper surface is an ordinary, taller-than-one-
  // screen document page mounted into that same #root — the global rule
  // silently clipped its lower sections with no way to reach them (the
  // reported "page cannot be scrolled downward" bug). This class scopes
  // a real-scroll override (see index.css's `html.sniper-surface` rules)
  // to exactly this surface, leaving the main app's own overflow:hidden
  // behavior completely untouched.
  document.documentElement.classList.add("sniper-surface");
  void import("./sniper/SniperApp").then(({ SniperApp }) => {
    createRoot(rootEl).render(
      <StrictMode>
        <SniperApp />
      </StrictMode>,
    );
  });
} else {
  createRoot(rootEl).render(
    <StrictMode>
      <App />
    </StrictMode>,
  );
}
