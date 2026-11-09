/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,jsx}"],
  theme: {
    extend: {
      colors: {
        brand: {
          50: "#fef9e7",
          100: "#fdf0c2",
          400: "#f4c430",
          500: "#f0b429",
          600: "#d99e0f",
          700: "#b78209",
        },
        ink: {
          700: "#334155",
          800: "#1e293b",
          900: "#0f172a",
        },
      },
    },
  },
  plugins: [],
};
