// Frames are split on blank lines with plain string search: replies can carry a raw
// U+2028, which multiline regex anchors would treat as a line break.
export function createSSEParser(onEvent) {
  let buffer = ''
  let carry = ''

  return function push(chunk) {
    let text = carry + chunk
    carry = ''
    if (text.endsWith('\r')) {
      carry = '\r'
      text = text.slice(0, -1)
    }
    buffer += text.replace(/\r\n?/g, '\n')
    let cut = buffer.indexOf('\n\n')
    while (cut !== -1) {
      const frame = buffer.slice(0, cut)
      buffer = buffer.slice(cut + 2)
      dispatch(frame, onEvent)
      cut = buffer.indexOf('\n\n')
    }
  }
}

function dispatch(frame, onEvent) {
  let event = 'message'
  const data = []
  for (const line of frame.split('\n')) {
    if (!line || line.startsWith(':')) continue
    const colon = line.indexOf(':')
    const field = colon === -1 ? line : line.slice(0, colon)
    let value = colon === -1 ? '' : line.slice(colon + 1)
    if (value.startsWith(' ')) value = value.slice(1)
    if (field === 'event') event = value
    else if (field === 'data') data.push(value)
  }
  if (!data.length) return
  let payload
  try {
    payload = JSON.parse(data.join('\n'))
  } catch {
    return
  }
  onEvent(event, payload)
}
