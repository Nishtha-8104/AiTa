import { palette } from '../../styles/palette'

export const TOPIC_LABELS = {
  basics_io: 'Basics & I/O',
  conditionals: 'Conditionals',
  loops: 'Loops',
  functions: 'Functions',
  arrays: 'Arrays',
  strings: 'Strings',
  hashing_sets: 'Hashing & Sets',
  recursion: 'Recursion',
  sorting: 'Sorting',
  searching: 'Searching',
  stacks_queues: 'Stacks & Queues',
  dynamic_programming: 'Dynamic Programming',
}

export const MISCONCEPTION_LABELS = {
  off_by_one: 'Off by one',
  empty_input_unhandled: 'Empty input not handled',
  wrong_initial_value: 'Wrong starting value',
  wrong_comparison_operator: 'Wrong comparison (< vs <=)',
  integer_division: 'Integer vs true division',
  missing_base_case: 'Missing base case',
  mutate_while_iterating: 'Changing a list while looping over it',
  uninitialised_variable: 'Variable not reset / initialised',
  wrong_loop_bound: 'Wrong loop bound',
  return_vs_print: 'Return vs print',
  index_out_of_range: 'Index out of range',
  infinite_loop: 'Loop never ends',
}

export const BAND_STYLE = {
  unseen:     { label: 'Not yet practised', bar: 'bg-white/10',  text: 'text-ink-subtle', soft: 'bg-white/[0.05] border-white/10',      hex: 'rgba(255,255,255,0.12)' },
  weak:       { label: 'Needs work',        bar: 'bg-pop-coral', text: 'text-pop-coral',  soft: 'bg-pop-coral/10 border-pop-coral/25', hex: palette.pop.coral },
  developing: { label: 'Developing',        bar: 'bg-pop-sun',   text: 'text-pop-sun',    soft: 'bg-pop-sun/10 border-pop-sun/25',     hex: palette.pop.sun },
  mastered:   { label: 'Mastered',          bar: 'bg-pop-mint',  text: 'text-pop-mint',   soft: 'bg-pop-mint/10 border-pop-mint/25',   hex: palette.pop.mint },
}

export const LANGUAGE_LABELS = { c: 'C', cpp: 'C++', python: 'Python' }
export const languageLabel = l => LANGUAGE_LABELS[l] || 'C'

export const ITEM_TYPE_LABELS = {
  diagnostic: 'Diagnostic',
  mcq: 'Multiple choice',
  coding: 'Coding problem',
  debug: 'Debug challenge',
  theory: 'Theory',
}

export const EVENT_KIND_LABELS = {
  code: 'Coding',
  mcq: 'MCQ',
  diagnostic: 'Diagnostic',
  debug: 'Debug',
  diagnostic_seed: 'Starting check',
  diagnostic_theory: 'Starting check (theory)',
}

export const topicLabel = t => TOPIC_LABELS[t] || t || 'Unclassified'
export const misconceptionLabel = m => MISCONCEPTION_LABELS[m] || m
