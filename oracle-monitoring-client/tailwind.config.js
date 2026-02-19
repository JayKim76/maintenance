/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  darkMode: 'class',
  theme: {
    extend: {
      colors: {
        background: '#0f172a', // Deep Dive Dark
        surface: '#1e293b',
        primary: '#06b6d4', // Cyan
        secondary: '#84cc16', // Lime
        accent: '#8b5cf6', // Purple
        danger: '#ef4444', // Red
        warning: '#f59e0b', // Amber
      },
      fontFamily: {
        sans: ['Inter', 'ui-sans-serif', 'system-ui', 'sans-serif'],
      },
    },
  },
  plugins: [],
}
