/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,jsx}"],
  theme: {
    extend: {
      colors: {
        background: "#121212",
        surface: "#1e1e1e",
        surfaceHover: "#2a2a2a",
        border: "#333333",
        textPrimary: "#f5f5f5",
        textSecondary: "#a3a3a3",
        primary: "#ffffff",
        primaryHover: "#e5e5e5",
        danger: "#ef4444",
        dangerHover: "#dc2626",
      },
      fontFamily: {
        sans: ["Inter", "system-ui", "sans-serif"],
      },
      borderRadius: {
        card: "8px",
        btn: "6px",
      },
      boxShadow: {
        card: "0 1px 3px rgba(0,0,0,0.5)",
        "card-hover": "0 4px 12px rgba(0,0,0,0.5)",
      },
    },
  },
  plugins: [],
}