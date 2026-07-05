export default {
  content: ['./index.html', './src/**/*.{js,ts,jsx,tsx}'],
  theme: {
    extend: {
      colors: {
        cinema: {
          black: '#0a0a0a', dark: '#111111', card: '#161616',
          border: '#222222', muted: '#333333', gold: '#d4a843',
          amber: '#f59e0b', blue: '#3b82f6', green: '#22c55e',
          red: '#ef4444', text: '#e8e8e8', 'text-dim': '#888888',
        }
      },
    },
  },
  plugins: [],
}