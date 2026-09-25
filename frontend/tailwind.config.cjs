/** @type {import('tailwindcss').Config} */
module.exports = {
  darkMode: "class",
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        // Civic identity: teal-blue primary; red reserved for emergencies;
        // green for resolved; amber for warnings/pending.
        primary: {
          50: "#eff8fa",
          100: "#d7eef2",
          200: "#b0dde6",
          300: "#7ac4d6",
          400: "#43a5c1",
          500: "#258aa8",
          600: "#1b6f8b",
          700: "#195a72",
          800: "#1a4b5f",
          900: "#1a3f50",
          950: "#0c2836",
          DEFAULT: "#1b6f8b",
          foreground: "#ffffff",
        },
        secondary: {
          50: "#f4f7f8",
          100: "#e6ecef",
          200: "#cfdce2",
          300: "#adc4cf",
          400: "#84a5b5",
          500: "#64899c",
          600: "#507084",
          700: "#445c6c",
          800: "#3a4e5b",
          900: "#34434d",
          DEFAULT: "#445c6c",
          foreground: "#ffffff",
        },
        success: { DEFAULT: "#16a34a", foreground: "#ffffff" },
        warning: { DEFAULT: "#d97706", foreground: "#ffffff" },
        danger: { DEFAULT: "#dc2626", foreground: "#ffffff" },
        border: "hsl(var(--border))",
        input: "hsl(var(--input))",
        ring: "hsl(var(--ring))",
        background: "hsl(var(--background))",
        foreground: "hsl(var(--foreground))",
        muted: {
          DEFAULT: "hsl(var(--muted))",
          foreground: "hsl(var(--muted-foreground))",
        },
        card: {
          DEFAULT: "hsl(var(--card))",
          foreground: "hsl(var(--card-foreground))",
        },
        popover: {
          DEFAULT: "hsl(var(--popover))",
          foreground: "hsl(var(--popover-foreground))",
        },
        accent: {
          DEFAULT: "hsl(var(--accent))",
          foreground: "hsl(var(--accent-foreground))",
        },
      },
      borderRadius: {
        lg: "0.75rem",
        md: "0.5rem",
        sm: "0.25rem",
      },
      keyframes: {
        "fade-in": { from: { opacity: "0" }, to: { opacity: "1" } },
        "slide-up": {
          from: { opacity: "0", transform: "translateY(8px)" },
          to: { opacity: "1", transform: "translateY(0)" },
        },
        "pulse-danger": {
          "0%, 100%": { opacity: "1" },
          "50%": { opacity: "0.6" },
        },
      },
      animation: {
        "fade-in": "fade-in 0.2s ease-out",
        "slide-up": "slide-up 0.25s ease-out",
        "pulse-danger": "pulse-danger 1.2s ease-in-out infinite",
      },
    },
  },
  plugins: [],
};
