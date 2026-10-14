/**
 * The thumbs on a recommendation card: they say whether the rating was saved, and a second click on the
 * same thumb (or one while a request is out) does not send another.
 */
import { describe, it, expect, vi } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { BrowserRouter } from 'react-router'
import { ToastProvider } from '../../contexts/ToastContext'
import { RecommendationCard } from '../../pages/Recommendations'

const recommendation = {
  id: 7,
  title: 'Go concurrency patterns',
  url: 'https://example.com/go',
  reason: 'Covers goroutines',
  match_score: 80,
  analysis: {},
}

const renderCard = (onFeedback) =>
  render(
    <BrowserRouter>
      <ToastProvider>
        <RecommendationCard recommendation={recommendation} onFeedback={onFeedback} selectedContext={null} />
      </ToastProvider>
    </BrowserRouter>
  )

describe('Recommendation card rating', () => {
  it('marks the thumb as chosen and says it was saved', async () => {
    const onFeedback = vi.fn().mockResolvedValue(true)
    renderCard(onFeedback)

    fireEvent.click(screen.getByTestId('thumb-up'))

    await waitFor(() => expect(screen.getByTestId('thumb-up')).toHaveAttribute('aria-pressed', 'true'))
    expect(onFeedback).toHaveBeenCalledWith(7, 'positive')
    expect(await screen.findByText('Marked as helpful')).toBeInTheDocument()
  })

  it('sends nothing more for a thumb that is already chosen', async () => {
    const onFeedback = vi.fn().mockResolvedValue(true)
    renderCard(onFeedback)

    fireEvent.click(screen.getByTestId('thumb-up'))
    await waitFor(() => expect(screen.getByTestId('thumb-up')).toHaveAttribute('aria-pressed', 'true'))
    fireEvent.click(screen.getByTestId('thumb-up'))
    fireEvent.click(screen.getByTestId('thumb-up'))

    expect(onFeedback).toHaveBeenCalledTimes(1)
  })

  it('ignores clicks while the first one is still being sent', async () => {
    let finish
    const onFeedback = vi.fn(() => new Promise((resolve) => { finish = resolve }))
    renderCard(onFeedback)

    fireEvent.click(screen.getByTestId('thumb-up'))
    fireEvent.click(screen.getByTestId('thumb-up'))
    fireEvent.click(screen.getByTestId('thumb-down'))
    expect(onFeedback).toHaveBeenCalledTimes(1)

    finish(true)
    await waitFor(() => expect(screen.getByTestId('thumb-up')).toHaveAttribute('aria-pressed', 'true'))
  })

  it('says so when the rating could not be saved, and leaves the thumb unchosen', async () => {
    const onFeedback = vi.fn().mockResolvedValue(false)
    renderCard(onFeedback)

    fireEvent.click(screen.getByTestId('thumb-down'))

    expect(await screen.findByText("Couldn't save your rating. Try again.")).toBeInTheDocument()
    expect(screen.getByTestId('thumb-down')).toHaveAttribute('aria-pressed', 'false')
  })

  it('lets the user change their mind', async () => {
    const onFeedback = vi.fn().mockResolvedValue(true)
    renderCard(onFeedback)

    fireEvent.click(screen.getByTestId('thumb-up'))
    await waitFor(() => expect(screen.getByTestId('thumb-up')).toHaveAttribute('aria-pressed', 'true'))
    fireEvent.click(screen.getByTestId('thumb-down'))

    await waitFor(() => expect(screen.getByTestId('thumb-down')).toHaveAttribute('aria-pressed', 'true'))
    expect(screen.getByTestId('thumb-up')).toHaveAttribute('aria-pressed', 'false')
    expect(onFeedback).toHaveBeenLastCalledWith(7, 'negative')
  })
})
