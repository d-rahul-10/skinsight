/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './*.{ts,tsx}', './types/**/*.ts'],
  theme: {
    extend: {
      colors: {
        ink: '#172033',
        muted: '#69758b',
        line: '#e6eaf2',
        violet: { 50: '#f5f3ff', 100: '#ede9fe', 500: '#7666e8', 600: '#6354d9', 700: '#5143bd' },
        sky: { 50: '#eff8ff', 100: '#dff1ff', 500: '#48a9e8', 600: '#288ccc' },
      },
      boxShadow: {
        soft: '0 18px 55px rgba(28, 44, 79, 0.08)',
        card: '0 8px 26px rgba(35, 48, 78, 0.06)',
      },
      fontFamily: {
        sans: ['Inter', 'ui-sans-serif', 'system-ui', 'sans-serif'],
        display: ['Manrope', 'Inter', 'ui-sans-serif', 'sans-serif'],
      },
    },
  },
  plugins: [],
};
