// Single source of truth for colours. Tailwind tokens and JS-only uses (toaster,
// CodeMirror, SVG charts) both read from here.
export const palette = {
  canvas: '#15191F',
  tile:   { DEFAULT: '#1B2129', 2: '#20262E', 3: '#232A33' },
  line:   { DEFAULT: '#2A323C', strong: '#3A4450' },
  ink:    { DEFAULT: '#ECE8DE', muted: '#C4C0B5', subtle: '#9C998F', faint: '#68665F' }, // warm, same family as `paper`
  pop: {
    mint:  '#7CC79A', // mastered, correct
    sun:   '#E8B05A', // developing, hints
    coral: '#E88F7A', // needs work, wrong
    aqua:  '#5FC9C0', // info
    pink:  '#D79AB0', // decoration only
  },
  brand: { 200: '#B5E9E4', 300: '#8FDCD5', 400: '#5FC9C0', 500: '#3FB0A6', 600: '#2E8E86' },
  code:  { bg: '#12161B', text: '#CDD4DD', gutter: '#4A5562', comment: '#6B7684' },
  shadow: '#0B0E12', // the dark "key" shadow under buttons and tiles
  // darker "key" shadow under a pop-coloured key
  key:   { mint: '#4E8F68', aqua: '#3B8F88', sun: '#A87A33', coral: '#A8604F', pink: '#9A6A7D', ink: '#A9A598' },
  chalk: '#FFFFFF',
}

// The light set used inside `.theme-paper` (the chat panel). Same token names,
// so components need no light-specific classes.
export const paper = {
  canvas: '#E7E3D8',
  tile:   { DEFAULT: '#EFECE4', 2: '#E7E3D8', 3: '#DEDACD' },
  line:   { DEFAULT: '#D8D2C2', strong: '#C2BBA8' },
  ink:    { DEFAULT: '#1E2630', muted: '#374151', subtle: '#565F6B', faint: '#8A8F94' },
  pop:    { mint: '#2A7148', sun: '#7C5408', coral: '#A23D27', aqua: '#0D6962', pink: '#984062' },
  brand:  { 200: '#0A524D', 300: '#0D6962', 400: '#0D6962', 500: '#0D6962', 600: '#0A524D' },
  chalk: '#1E2630', // `white/[…]` overlays become slate tints on the paper
}
