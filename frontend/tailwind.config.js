/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      fontFamily: {
        sans: ['"Public Sans"', '"Noto Serif Devanagari"', "system-ui", "-apple-system", "sans-serif"],
        serif: ['"DM Serif Display"', '"Noto Serif Devanagari"', "Georgia", "serif"],
        display: ['"DM Serif Display"', '"Noto Serif Devanagari"', "Georgia", "serif"],
      },
      colors: {
        paper: "#FFFFFF",
        surface: { DEFAULT: "#FFFFFF", alt: "#FFF1F1" },
        ink: "#222222",
        muted: "#666666",
        line: "#F5DADA",
        brand: {
          DEFAULT: "#C62828",
          secondary: "#E53935",
          deep: "#8E1B1B",
          strong: "#8E1B1B",
          soft: "#FFF1F1",
          subtle: "#FFE5E5",
        },
        warn: { DEFAULT: "#B45309", soft: "#FFFBEB" },
        danger: { DEFAULT: "#B91C1C", soft: "#FFE5E5" },
        done: { DEFAULT: "#2E7D32", soft: "#F0FDF4" },
      },
      borderRadius: { card: "10px" },
    },
  },
  plugins: [],
};
