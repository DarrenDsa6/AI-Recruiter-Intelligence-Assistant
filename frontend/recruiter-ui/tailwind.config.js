/** @type {import('tailwindcss').Config} */
module.exports = {
  content: ["./src/**/*.{js,jsx}"],
  theme: {
    extend: {
      colors: {
        primary: {
          50: "#FDF9EF",
          100: "#FAF0D8",
          200: "#F5DFAA",
          300: "#EECA7A",
          400: "#E8B054",
          500: "#DF9636",
          600: "#C67A26",
          700: "#A05D1F",
          800: "#7C471E",
          900: "#5C361B",
          950: "#33200F",
          DEFAULT: "#E8B054",
        },
        neutral: {
          50: "#F5F6F8",
          100: "#E2E6EB",
          200: "#C2CBD4",
          300: "#9BA6B3",
          400: "#75818F",
          500: "#55616F",
          600: "#3D4856",
          700: "#2C3542",
          750: "#232B37",
          800: "#1B212B",
          850: "#161B23",
          900: "#11141A",
          950: "#0B0D10",
          DEFAULT: "#0B0D10",
        },
        success: {
          300: "#6EE7B7",
          400: "#34D399",
          500: "#10B981",
          600: "#059669",
        },
        danger: {
          300: "#FCA5A5",
          400: "#F87171",
          500: "#EF4444",
          600: "#DC2626",
          700: "#B91C1C",
        },
        warning: {
          300: "#FCD34D",
          400: "#FBBF24",
          500: "#F59E0B",
        },
      },
      fontFamily: {
        sans: ['"Inter"', "system-ui", "-apple-system", '"Segoe UI"', "sans-serif"],
        display: ['"Fraunces"', "Georgia", "serif"],
      },
      borderRadius: {
        shell: "16px",
      },
      boxShadow: {
        card: "0 1px 2px rgba(0,0,0,0.35), 0 12px 32px -16px rgba(0,0,0,0.6)",
        elevated: "0 2px 4px rgba(0,0,0,0.35), 0 24px 48px -20px rgba(0,0,0,0.65)",
        glow: "0 0 0 1px rgba(232,176,84,0.22), 0 0 24px -6px rgba(232,176,84,0.3)",
        "btn-primary": "0 4px 16px -6px rgba(232,176,84,0.45)",
        "btn-primary-hover": "0 8px 24px -8px rgba(232,176,84,0.55)",
      },
      backgroundImage: {
        "radial-glow": "radial-gradient(1000px 520px at 50% -8%, rgba(232,176,84,0.07), transparent 60%)",
      },
    },
  },
  plugins: [require("@tailwindcss/typography")],
};
