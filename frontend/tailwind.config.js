/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,ts,jsx,tsx}"],
  theme: {
    extend: {
      fontFamily: {
        pixel: ['"Courier New"', "ui-monospace", "monospace"],
        // The Command Center's terminal aesthetic (v0.6.1) — a distinct
        // monospace stack from `pixel` above so the two UI languages (warm
        // fantasy-RPG chrome vs. cold trading-terminal chrome) read as
        // deliberately different systems, not the same font reused. Named
        // fonts here are a *preference list*, not a network font load —
        // the browser silently skips to the next entry if one isn't
        // installed, same as `pixel`'s "Courier New" above.
        cmdmono: ['"JetBrains Mono"', '"SFMono-Regular"', "ui-monospace", "Menlo", "Consolas", "monospace"],
      },
      colors: {
        parchment: "#f4e6c9",
        ink: "#241c14",
        panel: "#2b2118",
        panelLight: "#3a2c1f",
        gold: "#d9a441",
        bullish: "#4caf6a",
        bearish: "#d1495b",
        // Command Center palette (v0.6.1) — namespaced "cmd" so it never
        // collides with or gets confused for the fantasy-RPG tokens above;
        // the two are deliberately never mixed on the same element.
        "cmd-bg": "#060a12",
        "cmd-panel": "#0c1420",
        "cmd-panelLight": "#131e2e",
        "cmd-border": "#1f3348",
        "cmd-text": "#d8e6f2",
        "cmd-textDim": "#6c8299",
        "cmd-cyan": "#4fd8ff",
        "cmd-green": "#3ce28a",
        "cmd-amber": "#ffb443",
        "cmd-red": "#ff4d5e",
        "cmd-purple": "#a78bfa",
      },
      boxShadow: {
        pixel: "4px 4px 0 rgba(0,0,0,0.6)",
        "cmd-cyan": "0 0 1px rgba(79,216,255,0.8), 0 0 16px rgba(79,216,255,0.25)",
        "cmd-green": "0 0 1px rgba(60,226,138,0.8), 0 0 16px rgba(60,226,138,0.25)",
        "cmd-amber": "0 0 1px rgba(255,180,67,0.8), 0 0 16px rgba(255,180,67,0.25)",
        "cmd-red": "0 0 1px rgba(255,77,94,0.8), 0 0 16px rgba(255,77,94,0.3)",
      },
      // v0.6.2 Phase 10 trade outcome popup — a win pulses its glow and
      // drops confetti, a loss shakes once on entry, a breakeven gets
      // neither (see TradeOutcomePopup.tsx).
      keyframes: {
        "cmd-shake": {
          "0%, 100%": { transform: "translateX(0)" },
          "20%": { transform: "translateX(-8px)" },
          "40%": { transform: "translateX(7px)" },
          "60%": { transform: "translateX(-5px)" },
          "80%": { transform: "translateX(3px)" },
        },
        "cmd-glow-pulse": {
          "0%, 100%": { boxShadow: "0 0 1px rgba(60,226,138,0.8), 0 0 16px rgba(60,226,138,0.25)" },
          "50%": { boxShadow: "0 0 2px rgba(60,226,138,1), 0 0 36px rgba(60,226,138,0.55)" },
        },
        "cmd-confetti-fall": {
          "0%": { transform: "translateY(-10px) rotate(0deg)", opacity: "1" },
          "100%": { transform: "translateY(160px) rotate(340deg)", opacity: "0" },
        },
        // v0.6.3 Feature 14 — the cyber overlay's own open transition:
        // a slight zoom-out-of-focus + fade, so opening any full-screen
        // panel (Command Center, Executive Voting) reads as a deliberate
        // "entering the bridge" moment rather than an instant cut.
        "cmd-overlay-in": {
          "0%": { opacity: "0", transform: "scale(1.03)", filter: "blur(6px)" },
          "100%": { opacity: "1", transform: "scale(1)", filter: "blur(0)" },
        },
        "cmd-panel-in": {
          "0%": { opacity: "0", transform: "translateY(10px)" },
          "100%": { opacity: "1", transform: "translateY(0)" },
        },
        "cmd-toast-in": {
          "0%": { opacity: "0", transform: "translateX(24px)" },
          "100%": { opacity: "1", transform: "translateX(0)" },
        },
        "cmd-toast-out": {
          "0%": { opacity: "1", transform: "translateX(0)" },
          "100%": { opacity: "0", transform: "translateX(24px)" },
        },
        "cmd-grid-drift": {
          "0%": { backgroundPosition: "0px 0px" },
          "100%": { backgroundPosition: "48px 48px" },
        },
      },
      animation: {
        "cmd-shake": "cmd-shake 0.5s ease-in-out",
        "cmd-glow-pulse": "cmd-glow-pulse 1.6s ease-in-out infinite",
        "cmd-confetti-fall": "cmd-confetti-fall 1.4s ease-in forwards",
        "cmd-overlay-in": "cmd-overlay-in 0.32s cubic-bezier(0.16,1,0.3,1) both",
        "cmd-panel-in": "cmd-panel-in 0.4s cubic-bezier(0.16,1,0.3,1) both",
        "cmd-toast-in": "cmd-toast-in 0.28s cubic-bezier(0.16,1,0.3,1) both",
        "cmd-toast-out": "cmd-toast-out 0.22s ease-in both",
        "cmd-grid-drift": "cmd-grid-drift 12s linear infinite",
      },
    },
  },
  plugins: [],
};
