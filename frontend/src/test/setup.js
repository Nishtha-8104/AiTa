import { afterEach } from 'vitest'
import { cleanup } from '@testing-library/react'

afterEach(cleanup)

window.scrollTo = () => {}
Element.prototype.scrollIntoView = () => {}
