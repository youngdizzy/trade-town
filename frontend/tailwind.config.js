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
    },
  },
  plugins: [],
};
