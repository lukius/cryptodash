/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{vue,ts,tsx}'],
  theme: {
    extend: {
      colors: {
        'dash-bg': '#060b14',
        'dash-card': 'rgba(255,255,255,0.025)',
        'dash-border': 'rgba(255,255,255,0.06)',
        'dash-border-accent': 'rgba(73,234,203,0.2)',
        'dash-text': 'rgba(255,255,255,0.87)',
        'dash-text-secondary': 'rgba(255,255,255,0.6)',
        'dash-text-muted': 'rgba(255,255,255,0.38)',
        'dash-accent': '#49eacb',
        'dash-accent-dim': 'rgba(73,234,203,0.1)',
        'dash-green': '#00e676',
        'dash-red': '#ff4444',
        'dash-btc': '#f7931a',
        'dash-kas': '#49eacb',
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', 'sans-serif'],
      },
      borderRadius: {
        card: '16px',
        'card-sm': '10px',
      },
    },
  },
  plugins: [],
}
