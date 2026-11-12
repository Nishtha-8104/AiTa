import LogoMark, { Wordmark } from './LogoMark'

export default function FocusLayout({ width = 'max-w-2xl', aside, children }) {
  return (
    <div className="min-h-[100dvh] px-4 pb-16 pt-6 sm:px-6">
      <header className="mx-auto flex max-w-6xl items-center justify-between gap-4">
        <div className="flex items-center gap-2.5">
          <LogoMark />
          <Wordmark />
        </div>
        {aside}
      </header>
      <main id="main" className={`mx-auto mt-8 sm:mt-12 ${width}`}>{children}</main>
    </div>
  )
}
