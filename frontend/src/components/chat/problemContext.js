const PREFIX = 'Problem: '
const MARKER = '\n\nMy question: '

export function problemPrefix(context) {
  return context ? `${PREFIX}${context}${MARKER}` : ''
}

export function splitProblem(content) {
  if (!content.startsWith(PREFIX)) return { problem: null, question: content }
  const at = content.indexOf(MARKER)
  if (at === -1) return { problem: null, question: content }
  return { problem: content.slice(PREFIX.length, at), question: content.slice(at + MARKER.length) }
}
