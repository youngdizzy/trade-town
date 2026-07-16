/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,ts,jsx,tsx}"],
  theme: {
    extend: {
      fontFamily: {
        pixel: ['"Courier New"', "ui-monospace", "monospace"],
      },
      colors: {
        parchment: "#f4e6c9",
        ink: "#241c14",
        panel: "#2b2118",
        panelLight: "#3a2c1f",
        gold: "#d9a441",
        bullish: "#4caf6a",
        bearish: "#d1495b",
      },
      boxShadow: {
        pixel: "4px 4px 0 rgba(0,0,0,0.6)",
      },
    },
  },
  plugins: [],
};
