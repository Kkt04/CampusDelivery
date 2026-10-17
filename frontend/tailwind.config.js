/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      fontFamily: {
        sans: ['"Public Sans"', "system-ui", "-apple-system", "Segoe UI", "Roboto", "sans-serif"],
      },
      colors: {
        paper: "#F5F7F5",
        ink: "#16201A",
        muted: "#58655D",
        line: "#DCE3DE",
        brand: { DEFAULT: "#2D6A4F", strong: "#1F4D39", soft: "#E5F0E9" },
        warn: { DEFAULT: "#8A5300", soft: "#FBF0DC" },
        danger: { DEFAULT: "#A3352B", soft: "#F8E6E3" },
        done: { DEFAULT: "#3F5566", soft: "#E8EDF1" },
      },
      borderRadius: { card: "10px" },
    },
  },
  plugins: [],
};
