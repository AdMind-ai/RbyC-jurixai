/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    './index.html',
    './src/**/*.{js,ts,jsx,tsx}',
  ],
  theme: {
    extend: {
      colors: {
        'brand-primary': '#F5F5F5',
        'brand-secondary': '#FFFFFF',
        'brand-accent': '#203991',
        'brand-accent-hover': '#0C338C',
        'brand-subtle': '#707070',
        'brand-text': '#292929',
      },
    },
  },
  plugins: [],
};
