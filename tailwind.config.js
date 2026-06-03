/** @type {import('tailwindcss').Config} */
export default {
  content: [
    './audit-ui/index.html',
    './audit-ui/src/**/*.{ts,tsx}',
    './src/components/**/*.{ts,tsx}',
  ],
  theme: {
    extend: {
      fontFamily: {
        sans: ['Inter', 'ui-sans-serif', 'system-ui', 'sans-serif'],
      },
      colors: {
        audit: {
          canvas: '#f0f2f5',
        },
      },
    },
  },
  plugins: [],
};
