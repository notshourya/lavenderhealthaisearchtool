/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,jsx}"],
  theme: {
    extend: {
      colors: {
        primary: "#4d65ff",
        accent: "#ff4d8b",
        surface: "#ffffff",
        ink: "#1a1a2e",
        muted: "#6b7280",
        subtle: "#f4f5ff",
      },
      fontFamily: {
        sans: ["Open Sans", "system-ui", "sans-serif"],
      },
      borderRadius: {
        card: "12px",
        btn: "8px",
      },
      boxShadow: {
        card: "0 2px 12px rgba(77,101,255,0.08)",
        "card-hover": "0 4px 24px rgba(77,101,255,0.16)",
      },
    },
  },
  plugins: [],
}
