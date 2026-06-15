/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        primary: '#8b640d',
        'primary-light': '#a67e2e',
        'primary-dark': '#6b4c0a',
        secondary: '#092C4C',
        'secondary-light': '#1a4a7c',
        accent: '#F39C12',
        'accent-light': '#f5b833',
        'accent-dark': '#d68910',
        success: '#27ae60',
        warning: '#e67e22',
        error: '#e74c3c',
        neutral: '#F5F5F5',
        'neutral-dark': '#333333',
      },
      fontFamily: {
        sans: ['Nunito', 'sans-serif'],
        display: ['Poppins', 'sans-serif'],
      },
      spacing: {
        '128': '32rem',
      },
      borderRadius: {
        'lg': '0.5rem',
        'xl': '1rem',
      },
    },
  },
  plugins: [],
}
