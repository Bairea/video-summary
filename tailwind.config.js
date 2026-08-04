/** @type {import('tailwindcss').Config} */

export default {
  darkMode: "class",
  content: ["./index.html", "./src/**/*.{js,ts,jsx,tsx}"],
  theme: {
    container: {
      center: true,
    },
    extend: {
      fontFamily: {
        display: ['"Chakra Petch"', '"Noto Sans SC"', "ui-sans-serif", "system-ui"],
        sans: ['"Noto Sans SC"', "ui-sans-serif", "system-ui"],
        mono: ['"IBM Plex Mono"', "ui-monospace", "SFMono-Regular", "Menlo", "monospace"],
      },
      colors: {
        ink: {
          950: "#070A10",
          900: "#0A1020",
          800: "#111B2F",
        },
        neon: {
          400: "#3CF6FF",
          500: "#19D3FF",
          600: "#00A9FF",
        },
      },
    },
  },
  plugins: [],
};
