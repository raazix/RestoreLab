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
        canvas: '#08090a',
        surface: {
          1: '#0f1011',
          2: '#16181a',
          3: '#1c1e21',
          4: '#232528',
          hover: '#282a2e',
        },
        border: {
          subtle: 'rgba(255, 255, 255, 0.06)',
          muted: 'rgba(255, 255, 255, 0.1)',
          active: 'rgba(255, 255, 255, 0.18)',
        },
        linear: {
          accent: '#5e6ad2',
          glow: 'rgba(94, 106, 210, 0.15)',
        },
        status: {
          emerald: '#10b981',
          amber: '#f59e0b',
          rose: '#f43f5e',
          cyan: '#06b6d4',
          indigo: '#6366f1',
        }
      },
      fontFamily: {
        sans: ['Inter', '-apple-system', 'BlinkMacSystemFont', 'Segoe UI', 'Roboto', 'sans-serif'],
        mono: ['"JetBrains Mono"', '"Geist Mono"', 'Consolas', 'monospace'],
      },
      boxShadow: {
        subtle: '0 1px 2px 0 rgba(0, 0, 0, 0.4)',
        elevated: '0 4px 20px -2px rgba(0, 0, 0, 0.7)',
        glow: '0 0 20px -4px rgba(94, 106, 210, 0.25)',
      },
      animation: {
        'fade-in': 'fadeIn 0.2s cubic-bezier(0.16, 1, 0.3, 1)',
        'scale-in': 'scaleIn 0.2s cubic-bezier(0.16, 1, 0.3, 1)',
      },
      keyframes: {
        fadeIn: {
          from: { opacity: 0 },
          to: { opacity: 1 },
        },
        scaleIn: {
          from: { opacity: 0, transform: 'scale(0.98)' },
          to: { opacity: 1, transform: 'scale(1)' },
        },
      },
    },
  },
  plugins: [],
}
