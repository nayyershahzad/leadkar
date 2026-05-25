import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./app/**/*.{ts,tsx}", "./components/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        brand: { DEFAULT: "#0b5fff", dark: "#0747b8" },
        accent: { DEFAULT: "#7c3aed", pink: "#ec4899" },
        ink: "#0b1020",
      },
      container: {
        center: true,
        padding: "1.25rem",
        screens: { "2xl": "1180px" },
      },
      keyframes: {
        float: {
          "0%,100%": { transform: "translateY(0px)" },
          "50%": { transform: "translateY(-14px)" },
        },
        blob: {
          "0%,100%": { transform: "translate(0,0) scale(1)" },
          "33%": { transform: "translate(20px,-30px) scale(1.1)" },
          "66%": { transform: "translate(-20px,20px) scale(0.95)" },
        },
      },
      animation: {
        float: "float 6s ease-in-out infinite",
        blob: "blob 16s ease-in-out infinite",
      },
    },
  },
  plugins: [],
};

export default config;
