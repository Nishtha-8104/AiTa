import CodeEditor from '../ui/CodeEditor'

export default function CodeArea({ value, onChange, disabled, maxLength, minHeight = '260px', label, language = 'c' }) {
  return (
    <CodeEditor
      value={value}
      onChange={onChange}
      readOnly={disabled}
      maxLength={maxLength}
      minHeight={minHeight}
      maxHeight="560px"
      label={label}
      language={language}
    />
  )
}
