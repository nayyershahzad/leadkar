import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./app/**/*.{ts,tsx}",
    "./components/**/*.{ts,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        brand: {
          DEFAULT: "#0b5fff",
          dark: "#0747b8",
        },
      },
      container: {
        center: true,
        padding: "1rem",
        screens: { "2xl": "1120px" },
      },
    },
  },
  plugins: [],
};

export default config;
