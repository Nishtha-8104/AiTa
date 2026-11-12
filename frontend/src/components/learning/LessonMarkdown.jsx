import Markdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import CodeBlock from '../chat/CodeBlock'

function text(node) {
  if (!node) return ''
  if (node.type === 'text') return node.value
  return (node.children || []).map(text).join('')
}

function Fenced({ node }) {
  const code = node?.children?.find(c => c.tagName === 'code')
  const language = (code?.properties?.className || []).map(String)
    .find(c => c.startsWith('language-'))?.slice('language-'.length) || ''
  return <div className="my-4"><CodeBlock code={text(code || node).replace(/\n$/, '')} language={language} /></div>
}

const COMPONENTS = {
  pre: ({ node }) => <Fenced node={node} />,
  code: ({ children }) => (
    <code className="rounded-md bg-white/[0.07] px-1.5 py-0.5 font-mono text-[0.88em] text-pop-sun">{children}</code>
  ),
  h1: ({ children }) => <h2 className="mb-3 mt-8 text-2xl font-semibold tracking-tight text-ink first:mt-0">{children}</h2>,
  h2: ({ children }) => <h3 className="mb-2 mt-7 text-lg font-semibold tracking-tight text-ink first:mt-0">{children}</h3>,
  h3: ({ children }) => <h4 className="mb-2 mt-5 text-[15px] font-semibold text-ink first:mt-0">{children}</h4>,
  p: ({ children }) => <p className="my-3 leading-relaxed">{children}</p>,
  ul: ({ children }) => <ul className="my-3 list-disc space-y-1.5 pl-6 marker:text-ink-faint">{children}</ul>,
  ol: ({ children }) => <ol className="my-3 list-decimal space-y-1.5 pl-6 marker:text-ink-subtle">{children}</ol>,
  strong: ({ children }) => <strong className="font-semibold text-ink">{children}</strong>,
  blockquote: ({ children }) => (
    <blockquote className="my-4 rounded-r-2xl border-l-2 border-pop-sun/50 bg-pop-sun/[0.05] py-2 pl-4 pr-3 text-ink-muted">{children}</blockquote>
  ),
  table: ({ children }) => (
    <div className="my-4 overflow-x-auto rounded-xl border border-line">
      <table className="w-full border-collapse text-sm">{children}</table>
    </div>
  ),
  th: ({ children }) => <th className="border-b border-line bg-tile-2 px-3 py-2 text-left font-semibold text-ink">{children}</th>,
  td: ({ children }) => <td className="border-t border-white/[0.06] px-3 py-2 align-top">{children}</td>,
  hr: () => <hr className="my-6 border-line" />,
  a: ({ href, children }) => <a href={href} target="_blank" rel="noopener noreferrer" className="underline underline-offset-2">{children}</a>,
}

export default function LessonMarkdown({ markdown }) {
  return (
    <div className="text-[15px] text-ink-muted">
      <Markdown remarkPlugins={[remarkGfm]} components={COMPONENTS} disallowedElements={['img']} unwrapDisallowed>
        {markdown}
      </Markdown>
    </div>
  )
}
