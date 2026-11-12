import plugin from 'tailwindcss/plugin'
import { palette, paper } from './src/styles/palette.js'

// Tokens that switch between the dark page and the white `.theme-paper` panel go
// through CSS variables; the rest stay plain colours.
const THEMED = ['canvas', 'tile', 'line', 'ink', 'pop', 'brand', 'chalk']

const rgb = hex => [1, 3, 5].map(i => parseInt(hex.slice(i, i + 2), 16)).join(' ')

function entries(set) {
  return THEMED.flatMap(name => {
    const value = set[name]
    if (typeof value === 'string') return [[name, value]]
    return Object.entries(value).map(([k, v]) => [k === 'DEFAULT' ? name : `${name}-${k}`, v])
  })
}

const cssVars = set => Object.fromEntries(entries(set).map(([name, hex]) => [`--c-${name}`, rgb(hex)]))

const tokens = Object.fromEntries(THEMED.map(name => {
  const value = palette[name]
  if (typeof value === 'string') return [name, `rgb(var(--c-${name}) / <alpha-value>)`]
  return [name, Object.fromEntries(Object.keys(value).map(k => [
    k, `rgb(var(--c-${k === 'DEFAULT' ? name : `${name}-${k}`}) / <alpha-value>)`,
  ]))]
}))

/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,jsx}'],
  theme: {
    extend: {
      fontFamily: {
        display: ['"Space Grotesk"', 'system-ui', 'sans-serif'],
        body: ['"Space Grotesk"', 'system-ui', 'sans-serif'],
        mono: ['"IBM Plex Mono"', 'ui-monospace', 'monospace'],
      },
      colors: {
        ...tokens,
        white: tokens.chalk,
        code: palette.code,
        shadow: palette.shadow,
        key: palette.key,
      },
      borderRadius: {
        tile: '8px',
      },
      animation: {
        'fade-in': 'fadeIn 0.5s ease forwards',
        rise: 'rise 0.6s cubic-bezier(0.16, 1, 0.3, 1) both',
        'spin-slow': 'spin 40s linear infinite',
        breathe: 'breathe 2.4s ease-in-out infinite',
        'drawer-in': 'drawerIn 0.35s cubic-bezier(0.16, 1, 0.3, 1) both',
        blink: 'blink 1.2s steps(1, end) infinite',
        shimmer: 'shimmer 1.8s ease-in-out infinite',
      },
      keyframes: {
        fadeIn: { from: { opacity: 0 }, to: { opacity: 1 } },
        rise: { from: { opacity: 0, transform: 'translateY(14px)' }, to: { opacity: 1, transform: 'translateY(0)' } },
        breathe: { '0%, 100%': { opacity: 1, transform: 'scale(1)' }, '50%': { opacity: 0.45, transform: 'scale(0.8)' } },
        drawerIn: { from: { transform: 'translateX(-100%)' }, to: { transform: 'translateX(0)' } },
        blink: { '0%, 55%': { opacity: 1 }, '56%, 100%': { opacity: 0 } },
        shimmer: { '0%': { transform: 'translateX(-100%)' }, '100%': { transform: 'translateX(300%)' } },
      },
    },
  },
  plugins: [
    plugin(({ addBase }) => addBase({ ':root': cssVars(palette), '.theme-paper': cssVars(paper) })),
  ],
}
