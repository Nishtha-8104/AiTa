import { useMemo } from 'react'
import CodeMirror from '@uiw/react-codemirror'
import { EditorView } from '@codemirror/view'
import { EditorState } from '@codemirror/state'
import { HighlightStyle, indentUnit, syntaxHighlighting } from '@codemirror/language'
import { tags as t } from '@lezer/highlight'
import { cpp } from '@codemirror/lang-cpp'
import { python } from '@codemirror/lang-python'
import { palette } from '../../styles/palette'

const { code, ink, pop } = palette

const theme = EditorView.theme({
  '&': {
    color: code.text,
    backgroundColor: code.bg,
    fontSize: '13.5px',
  },
  '&.cm-focused': { outline: 'none' },
  '.cm-scroller': { fontFamily: '"IBM Plex Mono", ui-monospace, monospace', lineHeight: '1.65', fontVariantLigatures: 'none' },
  '.cm-content': { caretColor: ink.DEFAULT, padding: '14px 0' },
  '.cm-line': { padding: '0 16px 0 10px' },
  '.cm-cursor, .cm-dropCursor': { borderLeftColor: ink.DEFAULT, borderLeftWidth: '2px' },
  '&.cm-focused > .cm-scroller > .cm-selectionLayer .cm-selectionBackground, .cm-selectionBackground, .cm-content ::selection': {
    backgroundColor: 'rgba(95,201,192,0.24)',
  },
  '.cm-activeLine': { backgroundColor: 'rgba(255,255,255,0.03)' },
  '.cm-gutters': { backgroundColor: code.bg, color: code.gutter, border: 'none', paddingLeft: '6px' },
  '.cm-activeLineGutter': { backgroundColor: 'transparent', color: ink.muted },
  '.cm-lineNumbers .cm-gutterElement': { padding: '0 8px 0 6px', minWidth: '28px' },
  '.cm-matchingBracket, .cm-nonmatchingBracket': { backgroundColor: 'rgba(124,199,154,0.16)', outline: 'none' },
  '.cm-placeholder': { color: ink.faint },
}, { dark: true })

const highlight = HighlightStyle.define([
  { tag: [t.keyword, t.controlKeyword, t.modifier, t.operatorKeyword], color: pop.pink },
  { tag: [t.processingInstruction, t.meta], color: pop.pink },
  { tag: [t.string, t.special(t.string), t.character], color: pop.mint },
  { tag: [t.number, t.bool, t.null, t.atom], color: pop.sun },
  { tag: [t.comment, t.lineComment, t.blockComment], color: code.comment, fontStyle: 'italic' },
  { tag: [t.function(t.variableName), t.function(t.propertyName), t.macroName], color: pop.aqua },
  { tag: [t.typeName, t.className, t.standard(t.typeName)], color: pop.aqua },
  { tag: [t.definition(t.variableName)], color: ink.DEFAULT },
  { tag: [t.operator, t.punctuation, t.bracket], color: ink.muted },
  { tag: t.escape, color: pop.sun },
])

const LANG = { c: cpp, cpp, python }

export default function CodeMirrorEditor({
  value, onChange, language = 'c', readOnly = false, height, minHeight = '240px', maxHeight, label, maxLength, placeholder,
}) {
  const extensions = useMemo(() => [
    (LANG[language] || cpp)(),
    theme,
    syntaxHighlighting(highlight),
    indentUnit.of('    '),
    EditorState.tabSize.of(4),
    EditorView.contentAttributes.of({ 'aria-label': label || 'Code editor' }),
  ], [language, label])

  const handleChange = next => {
    if (!onChange) return
    onChange(maxLength && next.length > maxLength ? next.slice(0, maxLength) : next)
  }

  return (
    <CodeMirror
      value={value}
      onChange={handleChange}
      extensions={extensions}
      theme="none"
      editable={!readOnly}
      readOnly={readOnly}
      height={height}
      minHeight={minHeight}
      maxHeight={maxHeight}
      placeholder={placeholder}
      indentWithTab
      basicSetup={{
        lineNumbers: true,
        foldGutter: false,
        highlightActiveLine: !readOnly,
        highlightActiveLineGutter: !readOnly,
        autocompletion: false,
        closeBrackets: true,
        bracketMatching: true,
        indentOnInput: true,
        searchKeymap: false,
        tabSize: 4,
      }}
    />
  )
}
