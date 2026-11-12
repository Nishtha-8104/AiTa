export const STEPS = [
  { key: 'welcome',    label: 'Welcome' },
  { key: 'language',   label: 'Language' },
  { key: 'about',      label: 'About you' },
  { key: 'learning',   label: 'How you learn' },
  { key: 'diagnostic', label: 'Check' },
  { key: 'card',       label: 'Your profile' },
]

// Mirrors backend walk.TIERS.
export const TIERS = [
  ['basics_io', 'conditionals'],
  ['loops', 'functions'],
  ['arrays', 'strings'],
  ['recursion', 'sorting', 'searching'],
  ['hashing_sets', 'stacks_queues', 'dynamic_programming'],
]

export const LANGUAGES = [
  { value: 'c',      label: 'C',      blurb: 'Pointers, memory and how programs really run.' },
  { value: 'cpp',    label: 'C++',    blurb: 'C plus classes, the STL and modern features.' },
  { value: 'python', label: 'Python', blurb: 'Short, readable code with batteries included.' },
]

export const YEARS = [1, 2, 3, 4, 5, 6].map(n => ({ value: n, label: `Year ${n}` }))

export const EXPERIENCE = [
  { value: 'none',   label: 'None yet' },
  { value: 'lt6m',   label: 'Under 6 months' },
  { value: '6to12m', label: '6–12 months' },
  { value: '1to2y',  label: '1–2 years' },
  { value: '2yplus', label: '2+ years' },
]

export const GOALS = [
  { value: 'course',      label: 'Course and exams' },
  { value: 'placements',  label: 'Placements and interviews' },
  { value: 'competitive', label: 'Competitive programming' },
  { value: 'hobby',       label: 'Hobby' },
]

export const EXPLANATION_STYLES = [
  { value: 'step_by_step', label: 'Step by step' },
  { value: 'short',        label: 'Short and direct' },
]

export const EXAMPLE_ORDERS = [
  { value: 'examples_first', label: 'Examples first' },
  { value: 'concept_first',  label: 'Concept first' },
]

export const CHAT_LANGUAGES = [
  { value: 'english',  label: 'English' },
  { value: 'hinglish', label: 'Hinglish' },
]

export const HOURS_PER_WEEK = [
  { value: 'lt2',    label: 'Under 2 hours' },
  { value: '2to5',   label: '2–5 hours' },
  { value: '5to10',  label: '5–10 hours' },
  { value: '10plus', label: '10+ hours' },
]

export const SELF_RATINGS = [
  { value: 1, label: '1 · Just starting' },
  { value: 2, label: '2' },
  { value: 3, label: '3' },
  { value: 4, label: '4' },
  { value: 5, label: '5 · Very confident' },
]
