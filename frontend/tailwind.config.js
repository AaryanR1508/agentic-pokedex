/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        pokedex: {
          red: '#ee1515',
          redDark: '#b01010',
          redLight: '#ff3333',
        },
        glass: {
          border: 'rgba(255, 255, 255, 0.15)',
          bg: 'rgba(255, 255, 255, 0.05)',
          text: 'rgba(255, 255, 255, 0.9)',
        }
      },
      fontFamily: {
        sans: ['Inter', 'sans-serif'],
      },
    },
  },
  plugins: [],
}