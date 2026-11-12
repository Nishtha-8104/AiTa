import { describe, expect, it, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'
import PracticePage from './PracticePage'

const session = { id: 7, graded_count: 0 }

vi.mock('../hooks/useAuth', () => ({
  useAuth: () => ({ user: { full_name: 'Demo Student', preferred_language: 'c' } }),
}))

vi.mock('../utils/api', () => ({
  getErrorMessage: (_err, fallback) => fallback,
  feedbackAPI: { unreadCount: () => Promise.resolve({ data: { unread: 0 } }) },
  modelAPI: { get: () => new Promise(() => {}) },
  profileAPI: { getMastery: () => Promise.resolve({ data: { topics: [] } }) },
  practiceSessionAPI: {
    current: () => Promise.resolve({ data: { ...session } }),
    finish: () => Promise.resolve({ data: {} }),
  },
  assessmentAPI: {
    next: () => Promise.resolve({
      data: {
        item_type: 'mcq', topic: 'loops', difficulty: 'easy', reason: 'Loops is your weakest topic.',
        item: { id: 1, stem: 'What does `1 + 1` print?', options: ['1', '2', '3', '4'] },
      },
    }),
    answerMcq: () => {
      session.graded_count = 1
      return Promise.resolve({
        data: { correct: true, answer_index: 1, chosen_index: 1, mastery_after: 0.4, explanation: 'One plus one.' },
      })
    },
  },
}))

describe('PracticePage', () => {
  it('grades an answer and counts it in the session', async () => {
    const user = userEvent.setup()
    render(<MemoryRouter><PracticePage /></MemoryRouter>)

    expect(await screen.findByText('What does', { exact: false })).toBeTruthy()
    await user.click(screen.getByRole('radio', { name: /2/ }))
    await user.click(screen.getByRole('button', { name: 'Check answer' }))

    expect(await screen.findByText('Correct')).toBeTruthy()
    expect(await screen.findByText('1 answered this session')).toBeTruthy()
    expect(screen.getByRole('button', { name: /Finish session/ })).toBeTruthy()
  })
})
