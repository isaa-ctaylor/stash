/** @type {import('tailwindcss').Config} */
const defaultTheme = require('tailwindcss/defaultTheme');
module.exports = {
  content: ["./stash/src/**/*.{html,js}", "./stash/templates/**/*.{html,js}"],
  theme: {
    extend: {
      fontFamily: {
        "roboto-mono": ['"Roboto Mono"', ...defaultTheme.fontFamily.sans]
      }
    }
  },
  plugins: [],
}

