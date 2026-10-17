/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      fontFamily: {
        sans: ['"Public Sans"', "system-ui", "-apple-system", "Segoe UI", "Roboto", "sans-serif"],
      },
      colors: {
        paper: "#FFF7F1",
        ink: "#241512",
        muted: "#6E544B",
        line: "#EFD8CA",
        brand: { DEFAULT: "#C2410C", strong: "#9A3412", soft: "#FCE7D8" },
        warn: { DEFAULT: "#A16207", soft: "#FBF0D6" },
        danger: { DEFAULT: "#B91C1C", soft: "#FBE2E1" },
        done: { DEFAULT: "#8A4B36", soft: "#F3E5DE" },
      },
      borderRadius: { card: "10px" },
    },
  },
  plugins: [],
};
